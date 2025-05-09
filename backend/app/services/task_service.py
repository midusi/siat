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
from app.crud.district import *
from app.schemas.task import TaskCreateRequest
from app.models import Task, Video, TaskStatus, TaskStatusHistory


class TaskService(Base):
    def __init__(self, db: sessionmaker):
        self.db = db
        self.locality_service = LocalityService(db)
        self.video_service = VideoService(db)
        self.task_status_service = TaskStatusService(db)
        
    def create(
        self, 
        task_request: TaskCreateRequest,
        file: UploadFile
    ) -> bool:
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
            return True
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        # finally:
            # # Close the file after processing
            # file.file.close()
        # return TaskResponse.model_validate(task)
    
    def get_data_video(self, video: UploadFile) -> list:
        data_video = {
            "name": video.filename,
            "size": video.size,
            "format": video.content_type
        }
        return data_video
        
