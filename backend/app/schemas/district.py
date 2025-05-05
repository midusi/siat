from pydantic import BaseModel, ConfigDict

class DistrictResponse(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)