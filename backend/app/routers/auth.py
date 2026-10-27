from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from app.api.cookies import clear_session_cookies, set_session_cookies
from app.api.dependencies import require_csrf_header
from app.schemas.user import UserLoginRequest, UserResponse
from app.services.auth_service import AuthService
from app.services.dependencies import get_auth_service
from app.auth.dependencies import get_current_user
from app.config import COOKIE_NAME, REFRESH_COOKIE_NAME
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

    set_session_cookies(response, access_token, refresh_token)
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

    set_session_cookies(response, access_token, refresh_token)
    return {"access_token": access_token}


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf_header)])
async def logout(request: Request, response: Response, service: AuthService = Depends(get_auth_service)):
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

    # Contrato actual: el borrado se aplica a `response` pero se devuelve un Response nuevo,
    # por lo que el cliente no recibe Set-Cookie (ver test_contract_auth).
    clear_session_cookies(response)
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
async def me(user = Depends(get_current_user)):
    return UserResponse.model_validate(user)