from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from app.schemas.user import UserLoginRequest, UserResponse
from app.services.auth_service import AuthService
from app.services.dependencies import get_auth_service
from app.auth.dependencies import get_current_user
from app.config import (
    COOKIE_NAME, COOKIE_SECURE, COOKIE_SAMESITE, COOKIE_DOMAIN, COOKIE_PATH,
    REFRESH_COOKIE_NAME, REFRESH_COOKIE_SECURE, REFRESH_COOKIE_SAMESITE, REFRESH_COOKIE_DOMAIN, REFRESH_COOKIE_PATH,
    CSRF_HEADER_NAME
)
from app.auth.jwt import decode_token
from app.security.rate_limit import rate_limit_login
import logging

router = APIRouter(prefix="/auth", tags=["auth"]) 
log = logging.getLogger("audit")


@router.post("/login", response_model=dict)
async def login(
    user_request: UserLoginRequest,
    service: AuthService = Depends(get_auth_service),
    response: Response = Response(),
    _: None = Depends(rate_limit_login),
):
    result = service.login(user_request.username, user_request.password)
    if not result:
        log.info(f"login failed username={user_request.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token, refresh_token, user = result
    log.info(f"login success user_id={user.id} username={user.username}")

    # Set cookies
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=60 * 60,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 7,
        domain=REFRESH_COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )
    return {"access_token": access_token}


@router.post("/refresh", response_model=dict)
async def refresh(request: Request, response: Response, service: AuthService = Depends(get_auth_service)):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No hay refresh token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    user_id = int(payload.get("sub"))
    token_version = int(payload.get("ver", 0))

    result = service.refresh(user_id, token_version)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh inválido o expirado")

    access_token, refresh_token, _ = result

    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=60 * 60,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 7,
        domain=REFRESH_COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )
    return {"access_token": access_token}


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, service: AuthService = Depends(get_auth_service)):
    if not request.headers.get(CSRF_HEADER_NAME):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSRF token faltante")

    access = request.cookies.get(COOKIE_NAME)
    user_id = None
    if access:
        payload = decode_token(access)
        if payload and payload.get("type") == "access":
            user_id = int(payload.get("sub"))

    # If no access token, try refresh
    if user_id is None:
        refresh = request.cookies.get(REFRESH_COOKIE_NAME)
        if refresh:
            payload = decode_token(refresh)
            if payload and payload.get("type") == "refresh":
                user_id = int(payload.get("sub"))

    if user_id is not None:
        service.logout(user_id)
        log.info(f"logout user_id={user_id}")

    response.delete_cookie(COOKIE_NAME, domain=COOKIE_DOMAIN, path=COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE_NAME, domain=REFRESH_COOKIE_DOMAIN, path=REFRESH_COOKIE_PATH)
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
async def me(user = Depends(get_current_user)):
    return UserResponse.model_validate(user)