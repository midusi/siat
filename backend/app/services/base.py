from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db_session

class Base:
    def commit_and_refresh(self, obj):
        self.db.commit()
        self.db.refresh(obj)
        return obj