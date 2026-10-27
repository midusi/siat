from fastapi import Response

from app.config import (
    COOKIE_DOMAIN,
    COOKIE_NAME,
    COOKIE_PATH,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    REFRESH_COOKIE_DOMAIN,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    REFRESH_COOKIE_SAMESITE,
    REFRESH_COOKIE_SECURE,
)

ACCESS_COOKIE_MAX_AGE = 60 * 60
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7


def set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_COOKIE_MAX_AGE,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        max_age=REFRESH_COOKIE_MAX_AGE,
        domain=REFRESH_COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, domain=COOKIE_DOMAIN, path=COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE_NAME, domain=REFRESH_COOKIE_DOMAIN, path=REFRESH_COOKIE_PATH)
