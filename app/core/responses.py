"""Standard response envelope shared by every Python endpoint."""
from typing import Any

from pydantic import BaseModel

NO_DATA_MESSAGE = "No Data from Vendor"


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Any = None
    meta: dict[str, Any] | None = None


class ApiError(BaseModel):
    code: str
    details: Any = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    message: str
    data: None = None
    error: ApiError


def ok(data: Any, message: str = "Success", meta: dict[str, Any] | None = None) -> dict:
    body: dict[str, Any] = {"success": True, "message": message, "data": data}
    if meta:
        body["meta"] = meta
    return body


def no_data() -> dict:
    """The agreed response when the vendor answered successfully but returned no usable records."""
    return {"success": True, "message": NO_DATA_MESSAGE, "data": None}


# Documented error responses, attached to routers for Swagger.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorResponse, "description": "Invalid request"},
    401: {"model": ApiErrorResponse, "description": "Missing or invalid bearer token"},
    403: {"model": ApiErrorResponse, "description": "Missing permission"},
    404: {"model": ApiErrorResponse, "description": "Resource not found in the caller's tenant"},
    422: {"model": ApiErrorResponse, "description": "Request validation failed"},
    500: {"model": ApiErrorResponse, "description": "Database or server error"},
    502: {"model": ApiErrorResponse, "description": "Vendor error (auth, permission, rejected or invalid response)"},
    503: {"model": ApiErrorResponse, "description": "Vendor rate limited/unavailable or database unavailable"},
    504: {"model": ApiErrorResponse, "description": "Vendor timeout"},
}


# Route keyword arguments: document the envelope and omit fields the service did not set (e.g. `meta`), so the
# "No Data from Vendor" body is exactly {success, message, data}.
ENVELOPE: dict[str, Any] = {"response_model": ApiResponse, "response_model_exclude_unset": True}
