from fastapi import APIRouter, Depends, Request
from app.auth.decorators import require_role
from app.services.user_service import UserService
from app.services.dependencies import get_user_service
from app.schemas.user import UserCreateRequest

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/user-register")
async def user_register(user_request: UserCreateRequest, service: UserService = Depends(get_user_service)):
    user = service.create(user_request)
    return {"user": user}

@router.get("/user")
async def get_users(service: UserService = Depends(get_user_service)):
    users = service.get_list()
    return {"users": users}

@router.patch("/user/{user_id}/disable")
async def get_users(user_id: int, service: UserService = Depends(get_user_service)):
    user = service.disable(user_id)
    return {"user": user}

@router.patch("/user/{user_id}/enable")
async def get_users(user_id: int, service: UserService = Depends(get_user_service)):
    user = service.enable(user_id)
    return {"user": user}