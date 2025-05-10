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
from app.crud import task as task_crud
# from app.crud.district import *
from app.schemas.task import TaskCreateRequest, TaskResponse
from app.schemas.task_status import TaskStatusResponse
from app.schemas.locality import LocalityWDistrictResponse
from app.schemas.district import DistrictResponse
from app.models import Task, Video, TaskStatus, TaskStatusHistory

class TaskService:
    def __init__(self, db: sessionmaker):
        self.db = db
        self.locality_service = LocalityService(db)
        self.video_service = VideoService(db)
        self.task_status_service = TaskStatusService(db)
        
    def get_list(self) -> list[TaskResponse]:
        tasks = task_crud.get_list(self.db)
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
        task = task_crud.get_by_id(self.db, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
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
        
