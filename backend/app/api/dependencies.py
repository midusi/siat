from fastapi import Request

from app.config import CSRF_HEADER_NAME
from app.domain.exceptions import ValidationError

def require_csrf_header(request: Request) -> None:
    if not request.headers.get(CSRF_HEADER_NAME):
        raise ValidationError("CSRF token faltante")
