from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.db import get_db_session
from app.models import User
from app.config import COOKIE_NAME


def get_current_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    # Extract token from Authorization header or cookie
    token: Optional[str] = None
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:]
    if token is None:
        token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o no encontrado")

    token_ver = int(payload.get("ver", -1))
    current_ver = int(user.refresh_token_version or 0)
    if token_ver != current_ver:
        # Access emitido antes del logout/rotación -> inválido
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido (versión)")

    return user


def require_role(*allowed_roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if allowed_roles and user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
        return user
    return dependency
