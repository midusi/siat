from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.services.user_service import UserService
from app.services.dependencies import get_user_service
from app.schemas.user import ChangePasswordRequest, UserProfileUpdateRequest, UserResponse

router = APIRouter(prefix="/user", tags=["user"]) 

@router.get("/me", response_model=UserResponse)
async def me(user = Depends(get_current_user)):
    return UserResponse.model_validate(user)

@router.post("/me/change-password", status_code=204)
async def change_password(req: ChangePasswordRequest, user = Depends(get_current_user), service: UserService = Depends(get_user_service)):
    service.change_password(user.id, req)
    return {}

@router.patch("/me", response_model=UserResponse)
async def update_profile(req: UserProfileUpdateRequest, user = Depends(get_current_user), service: UserService = Depends(get_user_service)):
    updated = service.update_profile(user.id, req)
    return updated
