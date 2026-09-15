from fastapi.responses import JSONResponse

from app.domain.exceptions import AppError


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
