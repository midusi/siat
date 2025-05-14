# services/route_service.py
from sqlalchemy.orm import sessionmaker

from app.crud import route as route_crud
from app.models import Route

class RouteService:
    def __init__(self, db: sessionmaker):
        self.db = db
        
    def find_one_by_fields(self, **filters) -> Route:
        return route_crud.find_one_by_fields(self.db, **filters)