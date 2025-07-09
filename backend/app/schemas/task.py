from pydantic import BaseModel, field_validator, condecimal
from pydantic.config import ConfigDict
from app.schemas.locality import LocalityWDistrictResponse
from app.schemas.task_status import TaskStatusResponse
from app.schemas.road import RoadRequest
from datetime import datetime
    
class TaskCreateRequest(BaseModel):
    name: str
    locality_id: int
    uploaded_at: datetime
    
class TaskResponse(BaseModel):
    id: int
    name: str
    locality: LocalityWDistrictResponse
    name_video: str
    duration: int
    status: TaskStatusResponse
    uploaded_at: datetime
        
    model_config = ConfigDict(from_attributes=True)
    
class TaskConfigRequest(BaseModel):
    roads_in: list[RoadRequest]
    roads_out: list[RoadRequest]
    
    model_config = ConfigDict(from_attributes=True)