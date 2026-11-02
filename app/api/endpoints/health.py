import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.session import check_database

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", summary="Liveness probe")
def health():
    return {"success": True, "message": "OK", "data": {"status": "UP"}}


@router.get("/health/ready", summary="Readiness probe (SQL Server connectivity)")
def ready():
    try:
        check_database()
    except Exception as exc:  # never leak connection details
        logger.warning("Readiness check failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"success": False, "message": "Database unavailable",
                                                      "data": {"status": "DOWN"},
                                                      "error": {"code": "DATABASE_UNAVAILABLE"}})
    return {"success": True, "message": "OK", "data": {"status": "UP", "database": "UP"}}
