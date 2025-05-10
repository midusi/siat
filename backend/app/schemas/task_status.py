from pydantic import BaseModel, ConfigDict
    
class TaskStatusResponse(BaseModel):
    id: str
    name: str
    
    model_config = ConfigDict(from_attributes=True)