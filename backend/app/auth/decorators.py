from functools import wraps
from fastapi import Request, HTTPException, status
from typing import Union, List

# Deprecated: use app.auth.dependencies.require_role as a dependency

def require_role(roles: Union[str, List[str]] = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = getattr(request.state, "user", None)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
            if roles and user.get("role") not in roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator