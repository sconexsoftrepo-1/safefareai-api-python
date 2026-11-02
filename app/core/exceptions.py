"""Application error types and the FastAPI handlers that turn them into the standard JSON envelope.

Vendor failures, database failures and caller errors are separate types so that a failure is never
reported as "No Data from Vendor".
"""
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    default_message = "Unexpected server error"

    def __init__(self, message: str | None = None, *, code: str | None = None, status_code: int | None = None,
                 details: dict[str, Any] | None = None):
        self.message = message or self.default_message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code, code, default_message = 400, "BAD_REQUEST", "Invalid request"


class UnauthorizedError(AppError):
    status_code, code, default_message = 401, "UNAUTHORIZED", "Authentication required"


class ForbiddenError(AppError):
    status_code, code, default_message = 403, "FORBIDDEN", "You do not have permission to perform this action"


class NotFoundError(AppError):
    status_code, code, default_message = 404, "NOT_FOUND", "Resource not found"


class ConflictError(AppError):
    status_code, code, default_message = 409, "CONFLICT", "Request conflicts with the current state"


class ConfigurationError(AppError):
    status_code, code, default_message = 500, "CONFIGURATION_ERROR", "Server configuration error"


class DatabaseError(AppError):
    status_code, code, default_message = 500, "DATABASE_ERROR", "Database operation failed; no changes were saved"


class DatabaseUnavailableError(DatabaseError):
    status_code, code, default_message = 503, "DATABASE_UNAVAILABLE", "Database is unavailable"


# --- Vendor (GPS TrackTech) errors -------------------------------------------------------------------------
class VendorError(AppError):
    status_code, code, default_message = 502, "VENDOR_ERROR", "The vendor service returned an error"

    def __init__(self, message: str | None = None, *, vendor_code: int | None = None,
                 http_status: int | None = None, **kwargs):
        details = kwargs.pop("details", None) or {}
        if vendor_code is not None:
            details["vendorCode"] = vendor_code
        if http_status is not None:
            details["vendorHttpStatus"] = http_status
        super().__init__(message, details=details or None, **kwargs)
        self.vendor_code = vendor_code
        self.http_status = http_status


class VendorAuthError(VendorError):
    code, default_message = "VENDOR_AUTH_FAILED", "The vendor rejected the configured API key"


class VendorPermissionError(VendorError):
    code, default_message = "VENDOR_PERMISSION_DENIED", "The vendor account has no permission for this operation"


class VendorBadRequestError(VendorError):
    code, default_message = "VENDOR_REJECTED_REQUEST", "The vendor rejected the request parameters"


class VendorRateLimitError(VendorError):
    status_code, code, default_message = 503, "VENDOR_RATE_LIMITED", "The vendor is rate limiting requests"


class VendorUnavailableError(VendorError):
    status_code, code, default_message = 503, "VENDOR_UNAVAILABLE", "The vendor service is unavailable"


class VendorTimeoutError(VendorError):
    status_code, code, default_message = 504, "VENDOR_TIMEOUT", "The vendor service did not respond in time"


class VendorInvalidResponseError(VendorError):
    code, default_message = "VENDOR_INVALID_RESPONSE", "The vendor returned an unexpected response"


def _envelope(message: str, code: str, details: Any = None) -> dict:
    error: dict[str, Any] = {"code": code}
    if details:
        error["details"] = details
    return {"success": False, "message": message, "data": None, "error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        logger.log(level, "%s %s -> %s %s", request.method, request.url.path, exc.status_code, exc.code)
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc.message, exc.code, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return JSONResponse(status_code=422,
                            content=_envelope("Request validation failed", "VALIDATION_ERROR", details))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content=_envelope(str(exc.detail), f"HTTP_{exc.status_code}"),
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(OperationalError)
    async def _db_unavailable(request: Request, exc: OperationalError):
        logger.error("Database unavailable on %s %s: %s", request.method, request.url.path, type(exc.orig).__name__)
        err = DatabaseUnavailableError()
        return JSONResponse(status_code=err.status_code, content=_envelope(err.message, err.code))

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        err = DatabaseError()
        return JSONResponse(status_code=err.status_code, content=_envelope(err.message, err.code))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_envelope(AppError.default_message, AppError.code))
