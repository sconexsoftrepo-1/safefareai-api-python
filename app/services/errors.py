from __future__ import annotations


class MaintenanceError(Exception):
    """Business error carrying the HTTP status to return."""

    def __init__(self, status_code: int, message: str, data=None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.data = data
