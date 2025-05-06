from fastapi import APIRouter, Request
from app.auth.decorators import require_role
from app.auth.jwt import create_token

router = APIRouter()

# Ruta pública
@router.post("/login-ad")
async def login():
    fake_user = {"id": 1, "username": "nacho", "role": "Admin"}
    token = create_token(fake_user)
    return {"access_token": token}

@router.post("/login-op")
async def login2():
    fake_user = {"id": 1, "username": "nacho", "role": "Operador"}
    token = create_token(fake_user)
    return {"access_token": token}

# Ruta protegida (Admin y Operador)
@router.get("/dashboard")
@require_role(["Admin", "Operador"])
async def dashboard(request: Request):
    # param = request.query_params.get("asd")
    user = request.state.user
    return {"msg": f"Hola {user['username']}, accediste al dashboard"}

# Ruta solo para Admin
@router.get("/admin")
@require_role(["Admin"])
async def admin_panel(request: Request):
    user = request.state.user
    return {"msg": f"Hola {user['username']}, accedió al panel de administración"}


# @require_role(["Admin", "Operador"])