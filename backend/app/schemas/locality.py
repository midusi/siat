from pydantic import BaseModel, ConfigDict

class LocalityResponse(BaseModel):
    id: int
    name: str
    district_id: int
    
    model_config = ConfigDict(from_attributes=True)