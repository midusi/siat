from pydantic import BaseModel, field_validator, condecimal
from pydantic.config import ConfigDict
from app.schemas.locality import LocalityWDistrictResponse
from app.schemas.task_status import TaskStatusResponse
from app.schemas.road import RoadRequest
from datetime import datetime
    
class TaskCreateRequest(BaseModel):
    name: str
    locality_id: int
    date: datetime
    
class TaskResponse(BaseModel):
    id: int
    name: str
    locality: LocalityWDistrictResponse
    name_video: str
    duration: int
    status: TaskStatusResponse
    date: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
    
class RoadPolygon(BaseModel):
    name: str
    # 4 puntos, cada punto [x, y]
    polygon: list[list[int]]

class TaskConfigRequest(BaseModel):
    roads_in: list[RoadPolygon]
    roads_out: list[RoadPolygon]
    excluded_zones: list[list[list[int]]] | None = None
    
    model_config = ConfigDict(from_attributes=True)

class TaskUpdateData(BaseModel):
    rutas: dict
    indeterminados: dict
    determinados: dict | None = None
    data_obj_history: dict | None = None
