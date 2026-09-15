from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.adapters.wiring import build_object_storage, build_uow
from app.ports.uow import UnitOfWork
from app.ports.storage import ObjectStorage


def get_uow(db: Session = Depends(get_db_session)) -> UnitOfWork:
    return build_uow(db)


def get_object_storage() -> ObjectStorage:
    return build_object_storage()


def get_auth_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.auth_service import AuthService
    return AuthService(uow)


def get_user_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.user_service import UserService
    return UserService(uow)


def get_locality_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.locality_service import LocalityService
    return LocalityService(uow)


def get_district_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.district_service import DistrictService
    return DistrictService(uow)


def get_province_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.province_service import ProvinceService
    return ProvinceService(uow)


def get_task_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.task_service import TaskService
    return TaskService(uow, get_object_storage())


def get_video_service():
    from app.services.video_service import VideoService
    return VideoService(get_object_storage())


def get_bucket_service():
    return get_object_storage()


def get_password_reset_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.password_reset_service import PasswordResetService
    return PasswordResetService(uow)


def get_inference_service(uow: UnitOfWork = Depends(get_uow)):
    from app.services.inference_service import InferenceService
    return InferenceService(uow)


def get_email_service():
    from app.services.email_service import EmailService
    return EmailService()
