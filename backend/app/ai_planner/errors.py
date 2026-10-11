from datetime import datetime, timezone

from app.errors.exception import AppError


class AITimeoutError(AppError):
    code = "AI_TIMEOUT"
    default_message = "AI provider request timed out"
    status_code = 504


class AIRateLimitedError(AppError):
    code = "AI_RATE_LIMITED"
    default_message = "AI provider rate limit reached; please try again later"
    status_code = 429


class AIUnavailableError(AppError):
    code = "AI_UNAVAILABLE"
    default_message = "AI provider is temporarily unavailable"
    status_code = 503


class AIConfigurationError(AppError):
    code = "AI_CONFIGURATION_ERROR"
    default_message = "AI provider configuration requires attention"
    status_code = 503


class AIProviderError(AppError):
    code = "AI_PROVIDER_ERROR"
    default_message = "AI provider could not process the request"
    status_code = 502


class AIInvalidOutputError(AppError):
    code = "AI_INVALID_OUTPUT"
    default_message = "AI provider returned an invalid plan"
    status_code = 502


class AIQuotaExceededError(AppError):
    code = "AI_DAILY_LIMIT_EXCEEDED"
    default_message = "Daily AI request limit reached; please try again after the reset"
    status_code = 429

    def __init__(self, reset_at: datetime):
        super().__init__(details={"reset_at": reset_at.astimezone(timezone.utc).isoformat()})


class AIRequestInProgressError(AppError):
    code = "AI_REQUEST_IN_PROGRESS"
    default_message = "An AI request is already in progress; please wait"
    status_code = 429


class AIAdmissionUnavailableError(AppError):
    code = "AI_ADMISSION_UNAVAILABLE"
    default_message = "AI request admission is temporarily unavailable"
    status_code = 503
