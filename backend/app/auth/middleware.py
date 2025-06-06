from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.auth.jwt import decode_token

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = None
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
        elif request.cookies.get("access_token"):
            token = request.cookies.get("access_token")
        if token:
            user_data = decode_token(token)
            print(user_data)
            if user_data:
                request.state.user = user_data
        return await call_next(request)