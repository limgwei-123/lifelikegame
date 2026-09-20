from typing import Any


class AppError(Exception):
    code = "APP_ERROR"
    default_message = "Application error"
    status_code = 400

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    default_message = "Resource not found"
    status_code = 404


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    default_message = "Permission denied"
    status_code = 403


class ConflictError(AppError):
    code = "CONFLICT"
    default_message = "Conflict"
    status_code = 409


class RequestValidationError(AppError):
    code = "VALIDATION_ERROR"
    default_message = "Request validation failed"
    status_code = 422

    def __init__(self, issues: list[dict[str, str]]):
        super().__init__(details={"issues": issues})
