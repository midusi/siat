# crud/road.py
from sqlalchemy.orm import Session
from app.models import Road

def list_by_video(db: Session, video_id: int) -> list[Road]:
    return db.query(Road).filter(Road.video_id == video_id).all()
