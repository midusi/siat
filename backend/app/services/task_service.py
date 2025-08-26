# services/task_service.py
import os
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import sessionmaker
import hashlib
import time
import datetime
import json

from app.services.base import *
from app.services.locality_service import LocalityService
from app.services.video_service import VideoService
from app.services.task_status_service import TaskStatusService
from app.services.task_status_history_service import TaskStatusHistoryService
from app.services.road_service import RoadService
from app.crud import task as task_crud
from app.schemas.task import TaskCreateRequest, TaskResponse, TaskConfigRequest
from app.schemas.task import TaskUpdateData  # newly added import
from app.schemas.task_status import TaskStatusResponse
from app.schemas.locality import LocalityWDistrictResponse
from app.schemas.district import DistrictResponse
from app.models import Task, Video, TaskStatusHistory, Road, Inference
from app.enums.road_direction import RoadDirection
from app.services.bucket_service import BucketService

ARCHIVED_STATUS_ID = "ARCHIVED"

class TaskService:
    def __init__(self, db: sessionmaker):
        self.db = db
        self.locality_service = LocalityService(db)
        self.bucket_service = BucketService()
        self.video_service = VideoService(db, self.bucket_service)
        self.task_status_service = TaskStatusService(db)
        self.task_status_history_service = TaskStatusHistoryService(db)
        self.road_service = RoadService(db)
        
    def _to_response(self, task: Task) -> TaskResponse:
        history = task.status_history[0]
        return TaskResponse.model_validate({
            "id": task.id,
            "name": task.name,
            "locality": {
                "id": task.locality.id,
                "name": task.locality.name,
                "district": {
                    "id": task.locality.district.id,
                    "name": task.locality.district.name
                }
            },
            "name_video": task.video.name,
            "duration": int(task.video.duration),
            "status": {
                "id": history.task_status.id,
                "name": history.task_status.name
            },
            "date": task.date, 
            "created_at": task.created_at.isoformat()
        })
        
    def get_list(self) -> list[TaskResponse]:
        # Exclude archived tasks by default
        tasks = task_crud.find_all_active(self.db)
        return [self._to_response(t) for t in tasks]

    def get_archived_list(self) -> list[TaskResponse]:
        tasks = task_crud.find_all_archived(self.db)
        return [self._to_response(t) for t in tasks]
    
    def get_task(self, task_id: int) -> dict:
        """Devuelve la información real desde la BD y MinIO para el frontend.
        Incluye el path público del video, sus dimensiones y fps.
        También el json de rutas (transition_counts) e indeterminados (transition_undetermined)
        y la url del historial (url_data_obj_history).
        """
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        if not task.video:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La tarea no tiene video asociado")

        # Base pública para acceder a MinIO directamente
        public_base = f"http://localhost:9000/{BucketService.BUCKET_NAME}"

        # Elegir siempre el video original para reproducir
        video_key = task.video.url

        payload: dict = {
            "id": task.id,
            "name": task.name,
            # Front espera una URL reproducible por el tag <video>
            "videoPath": f"{public_base}/{video_key}",
            "videoWidth": task.video.width,
            "videoHeight": task.video.height,
            "videoFps": task.video.fps,
        }

        # Incluir polígonos de vías configuradas (Entrada/Salida) para overlay en el front
        try:
            roads = self.get_roads_by_task(task) or []
            roads_in = []
            roads_out = []
            for r in roads:
                item = {
                    "id": r.id,
                    "name": r.name,
                    "direction": r.direction,
                    "polygon": r.polygon,  # lista de pares [x, y] en coords del video original
                }
                # Road.direction almacena texto de RoadDirection ("Entrada"/"Salida")
                if str(r.direction) == str(RoadDirection.IN.value) or r.direction == RoadDirection.IN:
                    roads_in.append(item)
                elif str(r.direction) == str(RoadDirection.OUT.value) or r.direction == RoadDirection.OUT:
                    roads_out.append(item)
                else:
                    # Si viniera otro valor inesperado, ignorar silenciosamente
                    pass
            payload["roadsIn"] = roads_in
            payload["roadsOut"] = roads_out
        except Exception:
            # No bloquear si falla por compat; simplemente no incluir
            pass

        # Si existe inferencia, agregar URLs públicas a los JSON
        if task.inference:
            if task.inference.transition_counts:
                payload["rutas"] = json.loads(task.inference.transition_counts)
            if task.inference.transition_undetermined:
                try:
                    undet = json.loads(task.inference.transition_undetermined)
                except Exception:
                    undet = task.inference.transition_undetermined
                # Compat: if labels are arrays, convert to { in, out }
                if isinstance(undet, dict):
                    for k, it in list(undet.items()):
                        if isinstance(it, dict) and isinstance(it.get("labels"), list):
                            arr = it["labels"]
                            undet[k]["labels"] = {"in": (arr[0] if len(arr) > 0 else ""), "out": (arr[1] if len(arr) > 1 else "")}
                payload["indeterminados"] = undet
            # Agregar objetos con rutas determinadas por trackId
            if task.inference.transition_determined:
                det = json.loads(task.inference.transition_determined)
                if isinstance(det, dict):
                    for k, it in list(det.items()):
                        if isinstance(it, dict) and isinstance(it.get("labels"), list):
                            arr = it["labels"]
                            det[k]["labels"] = {"in": (arr[0] if len(arr) > 0 else ""), "out": (arr[1] if len(arr) > 1 else "")}
                payload["determinados"] = det
            if task.inference.url_data_obj_history:
                payload["historyUrl"] = f"{public_base}/{task.inference.url_data_obj_history}"

        return payload
        
    def create(
        self, 
        task_request: TaskCreateRequest,
        file: UploadFile
    ) -> TaskResponse:
        # Validate task data
        name = task_request.name
        locality_id = task_request.locality_id
        date = task_request.date
        locality = self.locality_service.get_by_id(locality_id)
        
        if not locality:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La localidad no existe")
        
        if not file.filename.endswith(('.mp4', '.avi', '.mov')):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de video no soportado")
        
        data_video = self.video_service.get_metadata_video(file)
        
        video_name = os.path.splitext(file.filename)[0]
        video_extension = os.path.splitext(file.filename)[1][1:]
        video = {
            "name": video_name,
            "format": video_extension,
            "url": f"{hashlib.sha256(f'{video_name}{int(time.time())}'.encode()).hexdigest()}.{video_extension}",
            **data_video
        }
        
        # Create objects in database
        try:
            # Create video
            video_obj = Video(
                **video
            )
            self.db.add(video_obj)
            self.db.flush()
            
            # Create task status history
            task_obj = Task(
                name=name,
                locality_id=locality_id,
                video_id=video_obj.id,
                date=date,
                created_at=datetime.datetime.now()
            )
            self.db.add(task_obj)
            self.db.flush()
            
            # Update video url
            video_obj.url = "task/" + str(task_obj.id) + "/" + video["url"]
            
            # Upload video to bucket
            try:
                self.bucket_service.upload(file, video_obj.url)
                
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
            
            # Create task status history
            task_status_pending = self.task_status_service.get_by_id("VIDEO_UPLOADED")
            task_status_history_obj = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task_obj.id,
                status_id=task_status_pending.id,
            )
            self.db.add(task_status_history_obj)
            
            # Commit and refresh the task object to get the ID
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        finally:
            # Close the file after processing
            file.file.close()
        

    
    def config(self, task_config_request: TaskConfigRequest, task_id: int):

        # Buscar la tarea por ID
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")

        # Verificar que la tarea se pueda configurar
        # Solo se puede configurar si el estado actual es VIDEO_UPLOADED o CONFIGURED
        current_task_status_history = self.task_status_history_service.get_current_by_task(task.id)
        if current_task_status_history.status_id not in ["VIDEO_UPLOADED", "CONFIGURED"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La tarea no se puede configurar")

        # Eliminar las vías actuales asociadas al video de la tarea
        currents_road = self.road_service.find_by_fields(video_id=task.video_id)
        for road in currents_road:
            self.db.delete(road)

        # roads_in y roads_out: listas de objetos con name y polygon (lista de pares [x, y])
        roads_in = task_config_request.roads_in
        roads_out = task_config_request.roads_out

        try:
            for i, road_in in enumerate(roads_in):
                road = self.road_service.create(
                    number=i+1,
                    direction=RoadDirection.IN,
                    polygon=road_in.polygon,
                    video_id=task.video.id,
                    name=road_in.name,
                )
                self.db.add(road)

            for i, road_out in enumerate(roads_out):
                road = self.road_service.create(
                    number=i+1,
                    direction=RoadDirection.OUT,
                    polygon=road_out.polygon,
                    video_id=task.video.id,
                    name=road_out.name,
                )
                self.db.add(road)

            # Actualizar el estado de la tarea
            current_task_status_history.to_date = datetime.datetime.now()
            self.db.flush()

            # Create task status history CONFIGURED
            task_status_configured = self.task_status_service.get_by_id("CONFIGURED")
            new_task_status_history = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=task_status_configured.id,
                to_date=datetime.datetime.now(),
            )
            self.db.add(new_task_status_history)

            # Create task status history READY_TO_PROCESS
            task_status_ready_to_process = self.task_status_service.get_by_id("READY_TO_PROCESS")
            new_task_status_history = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=task_status_ready_to_process.id,
            )
            self.db.add(new_task_status_history)

            self.db.commit()
            # self.process_video(task.id)
            return task
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
    def get_first_frame(self, task_id: int):
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        
        video = task.video
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El video de la tarea no existe")
        
        # Ahora video.url es la key del objeto, que es lo que espera get_frame
        # Y el valor de retorno ya es una cadena Base64, lista para ser enviada como JSON.
        first_frame_b64 = self.video_service.get_frame(video.url, 0)
        return first_frame_b64
    
    def get_video_dimensions(self, task_id: int) -> dict:
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        
        video = task.video
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El video de la tarea no existe")
        
        return {
            "width": video.width,
            "height": video.height
        }

    def process_video(self, task_id: int):

        # Verificar que la tarea exista
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")

        # Verificar que el video de la tarea exista
        video = task.video
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El video de la tarea no existe")

        # Verificar que la tarea esté configurada para procesar el video
        current_task_status_history = self.task_status_history_service.get_current_by_task(task.id)
        if current_task_status_history.status_id != "CONFIGURED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La tarea no está configurada para procesar el video")
        
        # -----------------
        # HARCODEADO:
        transition_counts = {
            "rutas": {
                "0": {
                    "0": { "bicycle": 0, "bus": 0, "car": 0, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "1": { "bicycle": 0, "bus": 0, "car": 6, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "2": { "bicycle": 0, "bus": 0, "car": 34, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "3": { "bicycle": 0, "bus": 0, "car": 8, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 }
                },
                "1": {
                    "0": { "bicycle": 0, "bus": 0, "car": 2, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "1": { "bicycle": 0, "bus": 0, "car": 1, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "2": { "bicycle": 0, "bus": 0, "car": 19, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "3": { "bicycle": 0, "bus": 0, "car": 23, "heavy_truck": 0, "light_truck": 1, "motorbike": 1 }
                },
                "2": {
                    "0": { "bicycle": 0, "bus": 0, "car": 77, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "1": { "bicycle": 0, "bus": 0, "car": 11, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "2": { "bicycle": 0, "bus": 0, "car": 4, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "3": { "bicycle": 0, "bus": 0, "car": 17, "heavy_truck": 0, "light_truck": 0, "motorbike": 2 }
                },
                "3": {
                    "0": { "bicycle": 0, "bus": 0, "car": 8, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "1": { "bicycle": 0, "bus": 0, "car": 22, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "2": { "bicycle": 0, "bus": 0, "car": 17, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                    "3": { "bicycle": 0, "bus": 0, "car": 0, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 }
                }
            }
        }
        
        transition_undetermined = {
            "indeterminados": {
                "1": {
                    "frame": "20",
                    "class": "car",
                    "boundingBox": [
                        "100",
                        "100",
                        "500",
                        "500"
                    ],
                    "labels": ["0", ""],
                },
                "2": {
                    "frame": "40",
                    "class": "bus",
                    "boundingBox": [
                        "200",
                        "200",
                        "600",
                        "600"
                    ],
                    "labels": ["1", ""],
                },
                "3": {
                    "frame": "60",
                    "class": "motorbike",
                    "boundingBox": [
                        "300",
                        "300",
                        "700",
                        "700"
                    ],
                    "labels": ["", "2"],
                },
                "4": {
                    "frame": "80",
                    "class": "bicycle",
                    "boundingBox": [
                        "400",
                        "400",
                        "800",
                        "800"
                    ],
                    "labels": ["", "3"],
                },
                "5": {
                    "frame": "100",
                    "class": "heavy_truck",
                    "boundingBox": [
                        "500",
                        "500",
                        "900",
                        "900"
                    ],
                    "labels": ["", ""],
                }
            }
        }

        # Get the folder where the video was saved in the bucket
        video_folder = os.path.dirname(video.url)

        # Prepare file names
        transition_counts_filename = "transition_counts.json"
        transition_undetermined_filename = "transition_undetermined.json"

        # Serialize data to JSON strings
        transition_counts_str = json.dumps(transition_counts, ensure_ascii=False, indent=2)
        transition_undetermined_str = json.dumps(transition_undetermined, ensure_ascii=False, indent=2)

        # Build full paths for the files in the bucket
        transition_counts_path = f"{video_folder}/{transition_counts_filename}"
        transition_undetermined_path = f"{video_folder}/{transition_undetermined_filename}"

        # Upload files to the bucket
        self.bucket_service.upload(transition_counts_str, transition_counts_path)
        self.bucket_service.upload(transition_undetermined_str, transition_undetermined_path)

        # Store URLs in the inference object
        inference = Inference(
            task_id=task.id,
            url_transition_counts=transition_counts_path,
            url_transition_undetermined=transition_undetermined_path,
            url_video_processed=video.url,
            inferred_at=datetime.datetime.now()
        )
        self.db.add(inference)
        # FIN HARCODEADO
        # -----------------

        # Actualizar el estado de la tarea a PROCESSED
        current_task_status_history.to_date = datetime.datetime.now()
        self.db.flush()
        task_status_processed = self.task_status_service.get_by_id("REVIEW")
        new_task_status_history = TaskStatusHistory(
            from_date=datetime.datetime.now(),
            task_id=task.id,
            status_id=task_status_processed.id,
        )
        self.db.add(new_task_status_history)
        self.db.flush()
        self.db.commit()

    # NEW: Persist updated rutas and indeterminados coming from frontend
    def update_data(self, task_id: int, updated_data: TaskUpdateData) -> dict:
        """Actualiza rutas, indeterminados, determinados y (opcional) data_obj_history.
        - transition_counts, transition_undetermined, transition_determined se guardan como JSON en BD.
        - data_obj_history (si viene) se sube a MinIO y se actualiza url_data_obj_history.
        Devuelve las URLs/keys actualizadas.
        """
        # Validaciones básicas
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        video = task.video
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El video de la tarea no existe")

        inference = task.inference
        if not inference:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no tiene inferencia")

        rutas = updated_data.rutas or {}
        indeterminados = updated_data.indeterminados or {}
        determinados = updated_data.determinados or {}
        data_obj_history = updated_data.data_obj_history or None

        try:
            # Serializar los datos como JSON antes de asignarlos
            # Guardar directamente los diccionarios sin envoltorio adicional
            inference.transition_counts = json.dumps(rutas, ensure_ascii=False, indent=2)
            inference.transition_undetermined = json.dumps(indeterminados, ensure_ascii=False, indent=2)
            # NEW: guardar determinados
            inference.transition_determined = json.dumps(determinados, ensure_ascii=False, indent=2)

            # Si vino data_obj_history, subirlo a MinIO y mantener el mismo nombre/clave que tenía antes
            if data_obj_history is not None:
                # Preferir conservar la misma key previamente usada si existe
                if inference.url_data_obj_history:
                    history_key = inference.url_data_obj_history
                else:
                    # Fallback: construir una key consistente con el esquema de proceso inicial
                    # Derivar carpeta (task/{id}) y hash base del nombre del video original
                    video_folder = os.path.dirname(task.video.url)
                    base_name = os.path.basename(task.video.url)  # p.ej. <hash>.mp4
                    hash_value, _ = os.path.splitext(base_name)
                    history_key = f"{video_folder}/{hash_value}_data_obj_history.json"

                history_str = json.dumps(data_obj_history, ensure_ascii=False, separators=(",", ":"))
                # Subir (sobrescribe si existe)
                self.bucket_service.upload(history_str, history_key, content_type="application/json")
                # Guardar/actualizar key en la BD
                inference.url_data_obj_history = history_key

            self.db.flush()
            self.db.commit()

            return {
                "rutasUrl": inference.transition_counts,
                "indeterminadosUrl": inference.transition_undetermined,
                "determinadosUrl": inference.transition_determined,
                "historyUrl": f"http://localhost:9000/{BucketService.BUCKET_NAME}/{inference.url_data_obj_history}" if inference.url_data_obj_history else None,
            }
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No se pudo actualizar los datos: {str(e)}",
            )

    # NEW: Archive and unarchive tasks by changing current TaskStatusHistory
    def archive(self, task_id: int) -> TaskResponse:
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        current = self.task_status_history_service.get_current_by_task(task.id)
        if current.status_id == ARCHIVED_STATUS_ID:
            return self._to_response(task)
        try:
            current.to_date = datetime.datetime.now()
            self.db.flush()
            archived_status = self.task_status_service.get_by_id(ARCHIVED_STATUS_ID)
            if not archived_status:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado ARCHIVED no existe")
            new_hist = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=archived_status.id,
            )
            self.db.add(new_hist)
            self.db.commit()
            # Reload associations for response (optional)
            return self._to_response(task)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    def unarchive(self, task_id: int) -> TaskResponse:
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        current = self.task_status_history_service.get_current_by_task(task.id)
        if current.status_id != ARCHIVED_STATUS_ID:
            return self._to_response(task)
        try:
            # Find last non-archived status in history
            prev_non_archived = (
                self.db.query(TaskStatusHistory)
                .filter(TaskStatusHistory.task_id == task.id, TaskStatusHistory.status_id != ARCHIVED_STATUS_ID)
                .order_by(TaskStatusHistory.id.desc())
                .first()
            )
            target_status_id = prev_non_archived.status_id if prev_non_archived else "REVIEW"
            target_status = self.task_status_service.get_by_id(target_status_id)
            if not target_status:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado de destino inválido")
            current.to_date = datetime.datetime.now()
            self.db.flush()
            new_hist = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=target_status.id,
            )
            self.db.add(new_hist)
            self.db.commit()
            return self._to_response(task)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    def delete(self, task_id: int) -> None:
        """Elimina una tarea y todos sus datos relacionados, además de su carpeta en el bucket.
        Orden de borrado en BD:
        - TaskStatusHistory
        - Inference
        - Roads (por video)
        - Task
        - Video
        Luego borra el prefijo "task/{id}" del bucket para eliminar video y JSONs.
        """
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        video = task.video
        if not video:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La tarea no tiene video asociado")

        # Prefijo en el bucket, p.ej. "task/123"
        prefix = os.path.dirname(video.url)

        try:
            # 1) Eliminar historiales de estado
            self.db.query(TaskStatusHistory).filter(TaskStatusHistory.task_id == task.id).delete(synchronize_session=False)
            # 2) Eliminar inferencia (si existe)
            if task.inference:
                self.db.delete(task.inference)
            # 3) Eliminar vías del video
            self.db.query(Road).filter(Road.video_id == video.id).delete(synchronize_session=False)
            # 4) Eliminar la tarea
            self.db.delete(task)
            # 5) Eliminar el video
            self.db.delete(video)
            self.db.flush()

            # 6) Eliminar objetos del bucket bajo el prefijo
            # Se hace antes del commit; si falla, se hace rollback de la BD para mantener consistencia
            self.bucket_service.delete_prefix(prefix)

            # 7) Confirmar transacción en BD
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No se pudo eliminar la tarea: {str(e)}")

    def get_video_download_info(self, task_id: int) -> tuple[str, str]:
        """Retorna (video_key, filename_sugerido) para descarga.
        Usa el video procesado si existe, si no el original.
        """
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        if not task.video:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La tarea no tiene video asociado")
        if task.inference and task.inference.url_video_processed:
            key = task.inference.url_video_processed
            base_name = f"{task.video.name}_processed.{task.video.format}"
        else:
            key = task.video.url
            base_name = f"{task.video.name}.{task.video.format}"
        return key, base_name

    def get_tasks_by_status(self, status_id: str) -> list[Task]:
        return task_crud.find_by_fields(self.db, status_id=status_id)
    
    def get_roads_by_task(self, task: Task) -> list[Road]:
        return self.road_service.find_by_fields(video_id=task.video_id)
    
    def update_task_status(self, task_id: int, status_id: str, commit: bool = False):
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        try:
            current_task_status_history = self.task_status_history_service.get_current_by_task(task.id)
            current_task_status_history.to_date = datetime.datetime.now()
            self.db.flush()
            task_status = self.task_status_service.get_by_id(status_id)
            new_task_status_history = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=task_status.id,
            )
            self.db.add(new_task_status_history)
            self.db.flush()
            if commit:
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))