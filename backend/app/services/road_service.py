# services/road_service.py
from sqlalchemy.orm import sessionmaker

from app.crud import road as road_crud
from app.models import Road
from app.enums.road_direction import RoadDirection

class RoadService:
    def __init__(self, db: sessionmaker):
        self.db = db
        
    def get_by_id(self, road_id: str) -> Road:
        return road_crud.find_one_by_fields(self.db, id=road_id)
        
    def find_by_fields(self, **filters) -> list[Road] | None:
        return road_crud.find_by_fields(self.db, **filters)
        
    def create(self, number: int, direction: RoadDirection, polygon, video_id: int, name: str | None = None) -> Road:
        import json
        return Road(
            name=name if name is not None and len(name) > 0 else f"Vía {number}",
            direction=direction,
            polygon=polygon,
            video_id=video_id,
        )