from fastapi import APIRouter, Depends, Request, Response
from app.auth.decorators import require_role
from app.auth.jwt import create_token
from app.schemas.user import UserLoginRequest
from app.services.auth_service import AuthService
from app.services.dependencies import get_auth_service
router = APIRouter()

# Ruta pública
@router.post("/login")
async def login(
    user_request: UserLoginRequest,
    service: AuthService = Depends(get_auth_service),
    response: Response = Response()
):
    token = service.login(user_request.username, user_request.password)
    # Seteamos cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # poner True en producción
        samesite="Lax",
        max_age=3600
    )
    return {"access_token": token}

@router.get("/dashboard")
@require_role(["ROLE_ADMIN"])
async def dashboard(request: Request):
    user = request.state.user
    return {"msg": f"Hola {user['username']}, accediste al dashboard"}