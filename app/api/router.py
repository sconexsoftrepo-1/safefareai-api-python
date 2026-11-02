from fastapi import APIRouter

from app.api.endpoints import alarms, commands, dashboard, health, reports, tracking, video, voices

api_router = APIRouter()
for module in (dashboard, tracking, video, alarms, reports, voices, commands):
    api_router.include_router(module.router)

public_router = APIRouter()
public_router.include_router(health.router)
