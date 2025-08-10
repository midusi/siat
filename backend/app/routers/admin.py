from fastapi import APIRouter, Depends
from app.services.user_service import UserService
from app.services.dependencies import get_user_service
from app.schemas.user import UserCreateRequest, UserUpdateRequest, AdminResetPasswordRequest
from app.auth.dependencies import require_role

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("ROLE_ADMIN"))])

@router.post("/user-register")
async def user_register(user_request: UserCreateRequest, service: UserService = Depends(get_user_service)):
    user = service.create(user_request)
    return {"user": user}

@router.get("/user")
async def get_users(service: UserService = Depends(get_user_service)):
    users = service.get_list()
    return {"users": users}

@router.patch("/user/{user_id}")
async def update_user(user_id: int, req: UserUpdateRequest, service: UserService = Depends(get_user_service)):
    user = service.update(user_id, req)
    return {"user": user}

@router.patch("/user/{user_id}/disable")
async def disable_user(user_id: int, service: UserService = Depends(get_user_service)):
    user = service.disable(user_id)
    return {"user": user}

@router.patch("/user/{user_id}/enable")
async def enable_user(user_id: int, service: UserService = Depends(get_user_service)):
    user = service.enable(user_id)
    return {"user": user}

@router.post("/user/{user_id}/reset-password", status_code=204)
async def admin_reset_password(user_id: int, req: AdminResetPasswordRequest, service: UserService = Depends(get_user_service)):
    service.admin_reset_password(user_id, req)
    return {}

@router.delete("/user/{user_id}", status_code=204)
async def delete_user(user_id: int, service: UserService = Depends(get_user_service)):
    service.delete(user_id)
    return {}