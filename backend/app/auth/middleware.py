from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.auth.jwt import decode_token
from app.config import COOKIE_NAME

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = None
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
        elif request.cookies.get(COOKIE_NAME):
            token = request.cookies.get(COOKIE_NAME)
        if token:
            user_data = decode_token(token)
            if user_data:
                request.state.user = user_data
        return await call_next(request)