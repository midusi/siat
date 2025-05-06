from fastapi import APIRouter, Depends, Request
from app.auth.decorators import require_role
from app.auth.jwt import create_token
from app.schemas.user import UserLoginRequest
from app.services.auth_service import AuthService
from app.services.dependencies import get_auth_service
router = APIRouter()

# Ruta pública
@router.post("/login")
async def login(user_request: UserLoginRequest, service: AuthService = Depends(get_auth_service)):
    token = service.login(user_request.username, user_request.password)
    return {"access_token": token}

# Ruta protegida (Admin y Operador)
# @router.get("/dashboard")
# @require_role(["Admin", "Operador"])
# async def dashboard(request: Request):
#     # param = request.query_params.get("asd")
#     user = request.state.user
#     return {"msg": f"Hola {user['username']}, accediste al dashboard"}


# @require_role(["Admin", "Operador"])