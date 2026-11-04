from fastapi.responses import JSONResponse

from app.domain.exceptions import AppError


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request, exc: AppError):
        content = {"detail": exc.detail}
        field = getattr(exc, "field", None)
        if field:
            content["field"] = field
        return JSONResponse(status_code=exc.status_code, content=content)
