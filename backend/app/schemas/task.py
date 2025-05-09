from pydantic import BaseModel, ConfigDict
# from app.schemas.locality import LocalityWDistrictResponse
from datetime import datetime
    
class TaskCreateRequest(BaseModel):
    name: str
    locality_id: int
    uploaded_at: datetime
    
# class TaskResponse(BaseModel):
#     name: str
#     locality: LocalityWDistrictResponse
#     name_video: str
#     status: str
#     uploaded_at: str
        
#     model_config = ConfigDict(from_attributes=True)