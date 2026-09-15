import os
from fastapi import UploadFile
import hashlib
import time
import datetime
import json

from app.services.locality_service import LocalityService
from app.services.video_service import VideoService
from app.services.task_status_service import TaskStatusService
from app.services.task_status_history_service import TaskStatusHistoryService
from app.services.road_service import RoadService
from app.schemas.task import TaskCreateRequest, TaskResponse, TaskConfigRequest
from app.schemas.task import TaskUpdateData
from app.domain.entities import Task, Video, TaskStatusHistory, Road, Inference
from app.enums.road_direction import RoadDirection
from app.ports.storage import ObjectStorage
from app.ports.uow import UnitOfWork
from app.adapters.wiring import build_object_storage
from app.services.task_upload import presign_upload as build_presigned_upload
from app.domain.exceptions import NotFoundError, ValidationError, InternalError

ARCHIVED_STATUS_ID = "ARCHIVED"


class TaskService:
    def __init__(self, uow: UnitOfWork, storage: ObjectStorage | None = None):
        self.uow = uow
        self.storage = storage or build_object_storage()
        self.locality_service = LocalityService(uow)
        self.video_service = VideoService(self.storage)
        self.task_status_service = TaskStatusService(uow)
        self.task_status_history_service = TaskStatusHistoryService(uow)
        self.road_service = RoadService(uow)

    def presign_upload(self, filename: str, content_type: str, expiration: int = 3600) -> dict:
        return build_presigned_upload(self.storage, filename, content_type, expiration)

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
                "id": history.status_id,
                "name": history.status_name or task.current_status_name
            },
            "date": task.date,
            "created_at": task.created_at.isoformat()
        })

    def _require_task(self, task_id: int) -> Task:
        task = self.uow.tasks.get(task_id)
        if not task:
            raise NotFoundError("La tarea no existe")
        return task

    def get_list(self) -> list[TaskResponse]:
        tasks = self.uow.tasks.list_active()
        return [self._to_response(t) for t in tasks]

    def get_archived_list(self) -> list[TaskResponse]:
        tasks = self.uow.tasks.list_archived()
        return [self._to_response(t) for t in tasks]

    def get_task(self, task_id: int) -> dict:
        task = self._require_task(task_id)
        if not task.video:
            raise ValidationError("La tarea no tiene video asociado")

        public_base = f"/bucket/{self.storage.bucket_name}"
        video_key = task.video.url

        payload: dict = {
            "id": task.id,
            "name": task.name,
            "videoPath": f"{public_base}/{video_key}",
            "videoWidth": task.video.width,
            "videoHeight": task.video.height,
            "videoFps": task.video.fps,
        }

        try:
            roads = self.get_roads_by_task(task) or []
            roads_in = []
            roads_out = []
            for r in roads:
                item = {
                    "id": r.id,
                    "name": r.name,
                    "direction": r.direction,
                    "polygon": r.polygon,
                }
                if str(r.direction) == str(RoadDirection.IN.value) or r.direction == RoadDirection.IN:
                    roads_in.append(item)
                elif str(r.direction) == str(RoadDirection.OUT.value) or r.direction == RoadDirection.OUT:
                    roads_out.append(item)
            payload["roadsIn"] = roads_in
            payload["roadsOut"] = roads_out
            excluded = [r.polygon for r in roads if (str(r.direction) == str(RoadDirection.EXCLUDED.value) or r.direction == RoadDirection.EXCLUDED)]
            if excluded:
                payload["excludedZones"] = excluded
        except Exception:
            pass

        if task.inference:
            if task.inference.transition_counts:
                payload["rutas"] = json.loads(task.inference.transition_counts)
            if task.inference.transition_undetermined:
                try:
                    undet = json.loads(task.inference.transition_undetermined)
                except Exception:
                    undet = task.inference.transition_undetermined
                if isinstance(undet, dict):
                    for k, it in list(undet.items()):
                        if isinstance(it, dict) and isinstance(it.get("labels"), list):
                            arr = it["labels"]
                            undet[k]["labels"] = {"in": (arr[0] if len(arr) > 0 else ""), "out": (arr[1] if len(arr) > 1 else "")}
                payload["indeterminados"] = undet
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
        name = task_request.name
        locality_id = task_request.locality_id
        date = task_request.date
        locality = self.locality_service.get_by_id(locality_id)

        if not locality:
            raise ValidationError("La localidad no existe")

        if not file.filename.endswith(('.mp4', '.avi', '.mov')):
            raise ValidationError("Formato de video no soportado")

        data_video = self.video_service.get_metadata_video(file)

        video_name = os.path.splitext(file.filename)[0]
        video_extension = os.path.splitext(file.filename)[1][1:]
        video = {
            "name": video_name,
            "format": video_extension,
            "url": f"{hashlib.sha256(f'{video_name}{int(time.time())}'.encode()).hexdigest()}.{video_extension}",
            **data_video
        }

        try:
            video_obj = Video(**video)
            self.uow.videos.add(video_obj)
            self.uow.flush()

            task_obj = Task(
                name=name,
                locality_id=locality_id,
                video_id=video_obj.id,
                date=date,
                created_at=datetime.datetime.now()
            )
            self.uow.tasks.add(task_obj)
            self.uow.flush()

            video_obj.url = "task/" + str(task_obj.id) + "/" + video["url"]

            try:
                self.storage.upload(file, video_obj.url)
            except Exception as e:
                raise InternalError(str(e))

            task_status_pending = self.task_status_service.get_by_id("VIDEO_UPLOADED")
            task_status_history_obj = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task_obj.id,
                status_id=task_status_pending.id,
            )
            self.uow.status_histories.add(task_status_history_obj)
            self.uow.commit()

        except Exception as e:
            self.uow.rollback()
            raise InternalError(str(e))
        finally:
            file.file.close()

    def create_from_object_key(
        self,
        task_request: TaskCreateRequest,
        object_key: str
    ) -> TaskResponse:
        name = task_request.name
        locality_id = task_request.locality_id
        date = task_request.date

        locality = self.locality_service.get_by_id(locality_id)
        if not locality:
            raise ValidationError("La localidad no existe")

        filename = os.path.basename(object_key)
        video_name, file_ext = os.path.splitext(filename)
        video_extension = file_ext[1:] if file_ext else 'mp4'

        if video_extension.lower() not in ('mp4', 'avi', 'mov'):
            raise ValidationError("Formato de video no soportado")

        if not self.storage.exists(object_key):
            raise ValidationError(
                "El archivo no fue encontrado en el almacenamiento. Asegúrese de subirlo primero usando la URL presignada."
            )

        try:
            data_video = self.video_service.get_metadata_from_s3(object_key)
        except Exception as e:
            raise InternalError(f"No se pudo obtener metadata del video: {str(e)}")

        try:
            video_obj = Video(
                name=video_name,
                format=video_extension,
                url=object_key,
                **data_video
            )
            self.uow.videos.add(video_obj)
            self.uow.flush()

            task_obj = Task(
                name=name,
                locality_id=locality_id,
                video_id=video_obj.id,
                date=date,
                created_at=datetime.datetime.now()
            )
            self.uow.tasks.add(task_obj)
            self.uow.flush()

            final_key = f"task/{task_obj.id}/{filename}"
            try:
                self.storage.copy(object_key, final_key)
                self.storage.delete_object(object_key)
                video_obj.url = final_key
            except Exception as e:
                raise InternalError(f"Error al mover archivo en MinIO: {str(e)}")

            task_status_pending = self.task_status_service.get_by_id("VIDEO_UPLOADED")
            task_status_history_obj = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task_obj.id,
                status_id=task_status_pending.id,
            )
            self.uow.status_histories.add(task_status_history_obj)
            self.uow.commit()

            return self._to_response(self.uow.tasks.get(task_obj.id))

        except Exception as e:
            self.uow.rollback()
            try:
                self.storage.delete_object(object_key)
            except:
                pass
            raise InternalError(str(e))

    def config(self, task_config_request: TaskConfigRequest, task_id: int):
        task = self._require_task(task_id)

        current_task_status_history = self.task_status_history_service.get_current_by_task(task.id)
        if current_task_status_history.status_id not in ["VIDEO_UPLOADED", "CONFIGURED"]:
            raise ValidationError("La tarea no se puede configurar")

        currents_road = self.road_service.find_by_fields(video_id=task.video_id)
        for road in currents_road:
            self.uow.roads.delete(road)

        roads_in = task_config_request.roads_in
        roads_out = task_config_request.roads_out
        excluded_zones = task_config_request.excluded_zones or []

        try:
            for i, road_in in enumerate(roads_in):
                road = self.road_service.create(
                    number=i+1,
                    direction=RoadDirection.IN,
                    polygon=road_in.polygon,
                    video_id=task.video.id,
                    name=road_in.name,
                )
                self.uow.roads.add(road)

            for i, road_out in enumerate(roads_out):
                road = self.road_service.create(
                    number=i+1,
                    direction=RoadDirection.OUT,
                    polygon=road_out.polygon,
                    video_id=task.video.id,
                    name=road_out.name,
                )
                self.uow.roads.add(road)

            for i, polygon in enumerate(excluded_zones):
                road = self.road_service.create(
                    number=i+1,
                    direction=RoadDirection.EXCLUDED,
                    polygon=polygon,
                    video_id=task.video.id,
                    name=f"Zona excluida {i+1}",
                )
                self.uow.roads.add(road)

            current_task_status_history.to_date = datetime.datetime.now()
            self.uow.flush()

            task_status_configured = self.task_status_service.get_by_id("CONFIGURED")
            new_task_status_history = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=task_status_configured.id,
                to_date=datetime.datetime.now(),
            )
            self.uow.status_histories.add(new_task_status_history)

            task_status_ready_to_process = self.task_status_service.get_by_id("READY_TO_PROCESS")
            new_task_status_history = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=task_status_ready_to_process.id,
            )
            self.uow.status_histories.add(new_task_status_history)

            self.uow.commit()

            try:
                import httpx
                httpx.post("http://backend-worker:8001/trigger", timeout=1.0)
            except Exception as e:
                print(f"Failed to trigger worker: {e}")

            return task
        except Exception as e:
            self.uow.rollback()
            raise InternalError(str(e))

    def get_first_frame(self, task_id: int):
        task = self._require_task(task_id)

        video = task.video
        if not video:
            raise NotFoundError("El video de la tarea no existe")

        first_frame_b64 = self.video_service.get_frame(video.url, 0)
        return first_frame_b64

    def get_video_dimensions(self, task_id: int) -> dict:
        task = self._require_task(task_id)

        video = task.video
        if not video:
            raise NotFoundError("El video de la tarea no existe")

        return {
            "width": video.width,
            "height": video.height
        }

    def process_video(self, task_id: int):
        task = self._require_task(task_id)

        video = task.video
        if not video:
            raise NotFoundError("El video de la tarea no existe")

        current_task_status_history = self.task_status_history_service.get_current_by_task(task.id)
        if current_task_status_history.status_id != "CONFIGURED":
            raise ValidationError("La tarea no está configurada para procesar el video")

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
                    "boundingBox": ["100", "100", "500", "500"],
                    "labels": ["0", ""],
                },
                "2": {
                    "frame": "40",
                    "class": "bus",
                    "boundingBox": ["200", "200", "600", "600"],
                    "labels": ["1", ""],
                },
                "3": {
                    "frame": "60",
                    "class": "motorbike",
                    "boundingBox": ["300", "300", "700", "700"],
                    "labels": ["", "2"],
                },
                "4": {
                    "frame": "80",
                    "class": "bicycle",
                    "boundingBox": ["400", "400", "800", "800"],
                    "labels": ["", "3"],
                },
                "5": {
                    "frame": "100",
                    "class": "heavy_truck",
                    "boundingBox": ["500", "500", "900", "900"],
                    "labels": ["", ""],
                }
            }
        }

        video_folder = os.path.dirname(video.url)
        transition_counts_filename = "transition_counts.json"
        transition_undetermined_filename = "transition_undetermined.json"
        transition_counts_str = json.dumps(transition_counts, ensure_ascii=False, indent=2)
        transition_undetermined_str = json.dumps(transition_undetermined, ensure_ascii=False, indent=2)
        transition_counts_path = f"{video_folder}/{transition_counts_filename}"
        transition_undetermined_path = f"{video_folder}/{transition_undetermined_filename}"

        self.storage.upload(transition_counts_str, transition_counts_path)
        self.storage.upload(transition_undetermined_str, transition_undetermined_path)

        inference = Inference(
            task_id=task.id,
            transition_counts=transition_counts_str,
            transition_undetermined=transition_undetermined_str,
            transition_determined=None,
            url_data_obj_history="",
            url_video_processed=video.url,
            inferred_at=datetime.datetime.now()
        )
        self.uow.inferences.add(inference)

        current_task_status_history.to_date = datetime.datetime.now()
        self.uow.flush()
        task_status_processed = self.task_status_service.get_by_id("REVIEW")
        new_task_status_history = TaskStatusHistory(
            from_date=datetime.datetime.now(),
            task_id=task.id,
            status_id=task_status_processed.id,
        )
        self.uow.status_histories.add(new_task_status_history)
        self.uow.flush()
        self.uow.commit()

    def update_data(self, task_id: int, updated_data: TaskUpdateData) -> dict:
        task = self._require_task(task_id)
        video = task.video
        if not video:
            raise NotFoundError("El video de la tarea no existe")

        inference = task.inference
        if not inference:
            raise NotFoundError("La tarea no tiene inferencia")

        rutas = updated_data.rutas or {}
        indeterminados = updated_data.indeterminados or {}
        determinados = updated_data.determinados or {}
        data_obj_history = updated_data.data_obj_history or None

        try:
            inference.transition_counts = json.dumps(rutas, ensure_ascii=False, indent=2)
            inference.transition_undetermined = json.dumps(indeterminados, ensure_ascii=False, indent=2)
            inference.transition_determined = json.dumps(determinados, ensure_ascii=False, indent=2)

            if data_obj_history is not None:
                if inference.url_data_obj_history:
                    history_key = inference.url_data_obj_history
                else:
                    video_folder = os.path.dirname(task.video.url)
                    base_name = os.path.basename(task.video.url)
                    hash_value, _ = os.path.splitext(base_name)
                    history_key = f"{video_folder}/{hash_value}_data_obj_history.json"

                history_str = json.dumps(data_obj_history, ensure_ascii=False, separators=(",", ":"))
                self.storage.upload(history_str, history_key, content_type="application/json")
                inference.url_data_obj_history = history_key

            self.uow.flush()
            self.uow.commit()

            return {
                "rutasUrl": inference.transition_counts,
                "indeterminadosUrl": inference.transition_undetermined,
                "determinadosUrl": inference.transition_determined,
                "historyUrl": self.storage.public_url(inference.url_data_obj_history) if inference.url_data_obj_history else None,
            }
        except Exception as e:
            self.uow.rollback()
            raise InternalError(f"No se pudo actualizar los datos: {str(e)}")

    def archive(self, task_id: int) -> TaskResponse:
        task = self._require_task(task_id)
        current = self.task_status_history_service.get_current_by_task(task.id)
        if current.status_id == ARCHIVED_STATUS_ID:
            return self._to_response(task)
        try:
            current.to_date = datetime.datetime.now()
            self.uow.flush()
            archived_status = self.task_status_service.get_by_id(ARCHIVED_STATUS_ID)
            if not archived_status:
                raise ValidationError("Estado ARCHIVED no existe")
            new_hist = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=archived_status.id,
            )
            self.uow.status_histories.add(new_hist)
            self.uow.commit()
            return self._to_response(self.uow.tasks.get(task.id))
        except Exception as e:
            self.uow.rollback()
            raise InternalError(str(e))

    def unarchive(self, task_id: int) -> TaskResponse:
        task = self._require_task(task_id)
        current = self.task_status_history_service.get_current_by_task(task.id)
        if current.status_id != ARCHIVED_STATUS_ID:
            return self._to_response(task)
        try:
            prev_non_archived = self.uow.status_histories.previous_non_archived(task.id, ARCHIVED_STATUS_ID)
            target_status_id = prev_non_archived.status_id if prev_non_archived else "REVIEW"
            target_status = self.task_status_service.get_by_id(target_status_id)
            if not target_status:
                raise ValidationError("Estado de destino inválido")
            current.to_date = datetime.datetime.now()
            self.uow.flush()
            new_hist = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=target_status.id,
            )
            self.uow.status_histories.add(new_hist)
            self.uow.commit()
            return self._to_response(self.uow.tasks.get(task.id))
        except Exception as e:
            self.uow.rollback()
            raise InternalError(str(e))

    def delete(self, task_id: int) -> None:
        task = self._require_task(task_id)
        video = task.video
        if not video:
            raise ValidationError("La tarea no tiene video asociado")

        prefix = os.path.dirname(video.url)

        try:
            self.uow.tasks.delete_cascade(task)
            self.uow.flush()
            self.storage.delete_prefix(prefix)
            self.uow.commit()
        except Exception as e:
            self.uow.rollback()
            raise InternalError(f"No se pudo eliminar la tarea: {str(e)}")

    def get_video_download_info(self, task_id: int) -> tuple[str, str]:
        task = self._require_task(task_id)
        if not task.video:
            raise ValidationError("La tarea no tiene video asociado")
        if task.inference and task.inference.url_video_processed:
            key = task.inference.url_video_processed
            base_name = f"{task.video.name}_processed.{task.video.format}"
        else:
            key = task.video.url
            base_name = f"{task.video.name}.{task.video.format}"
        return key, base_name

    def get_tasks_by_status(self, status_id: str) -> list[Task]:
        return self.uow.tasks.list_by_status(status_id)

    def get_roads_by_task(self, task: Task) -> list[Road]:
        return self.road_service.find_by_fields(video_id=task.video_id)

    def update_task_status(self, task_id: int, status_id: str, commit: bool = False):
        task = self._require_task(task_id)
        try:
            current_task_status_history = self.task_status_history_service.get_current_by_task(task.id)
            current_task_status_history.to_date = datetime.datetime.now()
            self.uow.flush()
            task_status = self.task_status_service.get_by_id(status_id)
            new_task_status_history = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=task_status.id,
            )
            self.uow.status_histories.add(new_task_status_history)
            self.uow.flush()
            if commit:
                self.uow.commit()
        except Exception as e:
            self.uow.rollback()
            raise InternalError(str(e))
