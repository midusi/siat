from pydantic import BaseModel, field_validator
from pydantic.config import ConfigDict
    
class RoadRequest(BaseModel):
    route_id: int
    polygon: tuple[float, float]
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator("polygon")
    @classmethod
    def check_length_four(cls, v):
        if len(v) != 2:
            raise ValueError("Cada polígono debe tener 2 puntos.")
        if any(coord < 0 for coord in v):
            raise ValueError("Las coordenadas del polígono deben ser positivas.")
        return v