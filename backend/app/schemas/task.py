from pydantic import BaseModel, ConfigDict
from app.schemas.locality import LocalityWDistrictResponse
from app.schemas.task_status import TaskStatusResponse
from datetime import datetime
    
class TaskCreateRequest(BaseModel):
    name: str
    locality_id: int
    uploaded_at: datetime
    
class TaskResponse(BaseModel):
    name: str
    locality: LocalityWDistrictResponse
    name_video: str
    duration: int
    status: TaskStatusResponse
    uploaded_at: datetime
        
    model_config = ConfigDict(from_attributes=True)