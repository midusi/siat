class AppError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "No encontrado"):
        super().__init__(404, detail)


class ValidationError(AppError):
    def __init__(self, detail: str):
        super().__init__(400, detail)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(401, detail)


class ConflictError(AppError):
    def __init__(self, detail: str):
        super().__init__(409, detail)


class InternalError(AppError):
    def __init__(self, detail: str):
        super().__init__(500, detail)


class StorageError(AppError):
    def __init__(self, detail: str):
        super().__init__(500, detail)


class StorageNotFound(AppError):
    def __init__(self, detail: str = "Objeto no encontrado"):
        super().__init__(404, detail)
