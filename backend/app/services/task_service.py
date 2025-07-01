# services/task_service.py
import os
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import sessionmaker
import hashlib
import time
import datetime

from app.services.base import *
from app.services.locality_service import LocalityService
from app.services.video_service import VideoService
from app.services.task_status_service import TaskStatusService
from app.services.task_status_history_service import TaskStatusHistoryService
from app.services.route_service import RouteService
from app.services.road_service import RoadService
from app.crud import task as task_crud
from app.schemas.task import TaskCreateRequest, TaskResponse, TaskConfigRequest
from app.schemas.task_status import TaskStatusResponse
from app.schemas.locality import LocalityWDistrictResponse
from app.schemas.district import DistrictResponse
from app.models import Task, Video, TaskStatusHistory, Road
from app.enums.road_direction import RoadDirection

class TaskService:
    def __init__(self, db: sessionmaker):
        self.db = db
        self.locality_service = LocalityService(db)
        self.video_service = VideoService(db)
        self.task_status_service = TaskStatusService(db)
        self.task_status_history_service = TaskStatusHistoryService(db)
        self.route_service = RouteService(db)
        self.road_service = RoadService(db)
        
    def get_list(self) -> list[TaskResponse]:
        tasks = task_crud.find_all(self.db)
        responses = []
        for task in tasks:
            history = task.status_history[0]
            task_response = TaskResponse.model_validate({
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
                "uploaded_at": task.uploaded_at.isoformat()
            })
            responses.append(task_response)
        return responses
    
    def get_task(self, task_id: int) -> TaskResponse:
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        
        history = task.status_history[0]
        task_response = TaskResponse.model_validate({
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
            "uploaded_at": task.uploaded_at.isoformat()
        })
        return task_response
        
    def create(
        self, 
        task_request: TaskCreateRequest,
        file: UploadFile
    ) -> TaskResponse:
        # Validate task data
        name = task_request.name
        locality_id = task_request.locality_id
        uploaded_at = task_request.uploaded_at
        locality = self.locality_service.get_by_id(locality_id)
        if not locality:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La localidad no existe")
        
        data_video = self.video_service.get_metadata_video(file)
        
        # if video_request.size > 104857600:  # 100 MB
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El video no puede ser mayor a 100 MB")
        if not file.filename.endswith(('.mp4', '.avi', '.mov')):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de video no soportado")
        
        video_name = os.path.splitext(file.filename)[0]
        video_extension = os.path.splitext(file.filename)[1][1:]
        video = {
            "name": video_name,
            "format": video_extension,
            "url": f"{hashlib.sha256(f'{video_name}{int(time.time())}'.encode()).hexdigest()}.{video_extension}",
            **data_video
        }
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
                uploaded_at=uploaded_at
            )
            self.db.add(task_obj)
            self.db.flush()
            
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
            
            # Create schema for task
            task_status_response = TaskStatusResponse.model_validate(task_status_pending)
            district_response = DistrictResponse.model_validate(locality.district)
            locality_response = LocalityWDistrictResponse.model_validate(
                {
                    "id": locality.id, 
                    "name": locality.name, 
                    "district": district_response
                })
            return TaskResponse.model_validate(
                {
                    "id": task_obj.id,
                    "name": task_obj.name,
                    "locality": locality_response,
                    "name_video": video_obj.name,
                    "duration": video_obj.duration,
                    "status": task_status_response,
                    "uploaded_at": task_obj.uploaded_at,
                })
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        # finally:
            # # Close the file after processing
            # file.file.close()
        

    
    def config(self, task_config_request: TaskConfigRequest, task_id: int):
        task = task_crud.find_one_by_fields(self.db, id=task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La tarea no existe")
        
        current_task_status_history = self.task_status_history_service.get_current_by_task(task.id)
        if current_task_status_history.status_id != "VIDEO_UPLOADED" and current_task_status_history.status_id != "CONFIGURED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La tarea no se puede configurar")
        
        currents_road = self.road_service.find_by_fields(video_id=task.video_id)
        for road in currents_road:
            self.db.delete(road)
        
        roads_in = task_config_request.roads_in
        roads_out = task_config_request.roads_out
        
        try:
            for i, road in enumerate(roads_in):
                route = self.route_service.find_one_by_fields(id=road.route_id)
                if not route:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La ruta no existe")
                road = self.road_service.create(
                    number=i+1,
                    direction=RoadDirection.IN,
                    polygon=road.polygon,
                    video_id=task.video.id,
                    route_id=route.id,
                )
                self.db.add(road)

            for i, road in enumerate(roads_out):
                route = self.route_service.find_one_by_fields(id=road.route_id)
                road = Road(
                    number=i+1,
                    direction=RoadDirection.OUT,
                    polygon=road.polygon,
                    video_id=task.video.id,
                    route_id=route.id,
                )
                self.db.add(road)
                
            # Change task status history
            current_task_status_history.to_date = datetime.datetime.now()
            self.db.flush()
            
            # Create task status history CONFIGURED
            task_status_configured = self.task_status_service.get_by_id("CONFIGURED")
            new_task_status_history = TaskStatusHistory(
                from_date=datetime.datetime.now(),
                task_id=task.id,
                status_id=task_status_configured.id,
            )
            self.db.add(new_task_status_history)
                
            self.db.commit()
            return task
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))