from fastapi import APIRouter, Depends, Request, Response
from app.api.cookies import clear_session_cookies, set_session_cookies
from app.api.dependencies import require_csrf_header
from app.schemas.user import UserLoginRequest, UserResponse
from app.services.auth_service import AuthService
from app.services.dependencies import get_auth_service
from app.auth.dependencies import get_current_user
from app.config import COOKIE_NAME, REFRESH_COOKIE_NAME
from app.security.rate_limit import rate_limit_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=dict)
async def login(
    user_request: UserLoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    _: None = Depends(rate_limit_login),
):
    session = service.login(user_request.username, user_request.password)
    set_session_cookies(response, session.access_token, session.refresh_token)
    return {"access_token": session.access_token}


@router.post("/refresh", response_model=dict)
async def refresh(request: Request, response: Response, service: AuthService = Depends(get_auth_service)):
    session = service.refresh_from_token(request.cookies.get(REFRESH_COOKIE_NAME))
    set_session_cookies(response, session.access_token, session.refresh_token)
    return {"access_token": session.access_token}


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf_header)])
async def logout(request: Request, response: Response, service: AuthService = Depends(get_auth_service)):
    service.logout_from_tokens(
        request.cookies.get(COOKIE_NAME),
        request.cookies.get(REFRESH_COOKIE_NAME),
    )

    # Contrato actual: el borrado se aplica a `response` pero se devuelve un Response nuevo,
    # por lo que el cliente no recibe Set-Cookie (ver test_contract_auth).
    clear_session_cookies(response)
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
async def me(user = Depends(get_current_user)):
    return UserResponse.model_validate(user)
