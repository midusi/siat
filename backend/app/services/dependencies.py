from fastapi import Depends
from app.db import get_db_session
from sqlalchemy.orm import sessionmaker

def get_auth_service(db: sessionmaker = Depends(get_db_session)):
    from app.services.auth_service import AuthService
    return AuthService(db)

def get_user_service(db: sessionmaker = Depends(get_db_session)):
    from app.services.user_service import UserService
    return UserService(db)

def get_locality_service(db: sessionmaker = Depends(get_db_session)):
    from app.services.locality_service import LocalityService
    return LocalityService(db)

def get_district_service(db: sessionmaker = Depends(get_db_session)):
    from app.services.district_service import DistrictService
    return DistrictService(db)

def get_task_service(db: sessionmaker = Depends(get_db_session)):
    from app.services.task_service import TaskService
    return TaskService(db)

def get_video_service(db: sessionmaker = Depends(get_db_session)):
    from app.services.video_service import VideoService
    return VideoService(db)