from pydantic import BaseModel, ConfigDict
from app.schemas.district import DistrictResponse

class LocalityResponse(BaseModel):
    id: int
    name: str
    district_id: int
    
    model_config = ConfigDict(from_attributes=True)

class LocalityWDistrictResponse(BaseModel):
    id: int
    name: str
    district: DistrictResponse
    
    model_config = ConfigDict(from_attributes=True)