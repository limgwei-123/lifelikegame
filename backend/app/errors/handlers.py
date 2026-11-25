from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from app.errors.exception import AppError
from app.core.rate_limiting import RequestRateLimitedError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        if request.url.path.rstrip('/') == '/auth/change-password':
            # Pydantic errors can contain the raw request even for SecretStr.
            return JSONResponse(status_code=422, content={'detail': [
                {key: error[key] for key in ('type', 'loc', 'msg')} for error in exc.errors()
            ]})
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(RequestRateLimitedError)
    async def rate_limit_handler(request: Request, exc: RequestRateLimitedError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "details": exc.details},
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )
