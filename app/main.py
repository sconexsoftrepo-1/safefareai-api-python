import os
import logging
import threading
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

# --- Vehicle Maintenance dev login (must be installed BEFORE its router is imported) ---
from app.integration.dev_auth import install_dev_auth

install_dev_auth()

# Iris AI (chat) routes
from app.api.chat import router as chat_router

# IoT Sensor routes + background S3 worker
from app.routes.sensor_routes import router as sensor_router
from app.workers.s3_polling_worker import (
    start_s3_polling_worker,
    start_prs_polling_worker,
)

# BMS vs Sensor comparison routes + 10-second background worker
from app.api.bms_comparison import bms_router, bms_sensor_router
from app.workers.bms_comparison_worker import start_bms_comparison_worker

# Alarm media migration (GPS TrackTech server -> AWS S3), background worker
from app.workers.alarm_media_worker import start_alarm_media_worker
from app.api.alarm_media import alarm_media_router

# Tyre Maintenance routes + background scheduler
from app.api.v1.endpoints.tyre_maintenance import router as tyre_maintenance_router
from app.jobs.tyre_maintenance_scheduler import (
    start_tyre_maintenance_scheduler,
    stop_tyre_maintenance_scheduler,
)

# Vehicle Maintenance routes + daily scheduler
from app.api.vehicle_maintenance import router as vehicle_maintenance_router
from app.vehicle_maintenance_module import (
    setup_vehicle_maintenance,
    shutdown_vehicle_maintenance,
)


# Logging configuration (from the Sensor backend)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting SafeFare Backend...")

    # --- Sensor: S3 polling in a background thread ---
    worker_thread = threading.Thread(
        target=start_s3_polling_worker,
        name="S3-Polling-Worker",
        daemon=True
    )
    worker_thread.start()
    logger.info("S3 polling worker launched.")

    # --- Sensor: PRS (seat) files -> prs_sensor_readings, own thread / own interval ---
    prs_worker_thread = threading.Thread(
        target=start_prs_polling_worker,
        name="PRS-Polling-Worker",
        daemon=True
    )
    prs_worker_thread.start()
    logger.info("PRS polling worker launched.")

    # --- BMS vs Sensor comparison: reads prs_sensor_readings every BMS_WORKER_INTERVAL_SECONDS ---
    bms_worker_thread = threading.Thread(
        target=start_bms_comparison_worker,
        name="BMS-Comparison-Worker",
        daemon=True
    )
    bms_worker_thread.start()
    logger.info("BMS comparison worker launched.")

    # --- Alarm media: copies alarm images / videos (alarm_media.s3_key IS NULL) to S3 every 5 seconds ---
    alarm_media_stop = threading.Event()
    alarm_media_thread = threading.Thread(
        target=start_alarm_media_worker,
        args=(alarm_media_stop,),
        name="Alarm-Media-Worker",
        daemon=True
    )
    alarm_media_thread.start()
    logger.info("Alarm media migration worker launched.")

    # --- Tyre maintenance: asyncio background task ---
    start_tyre_maintenance_scheduler()

    # --- Vehicle maintenance: services + daily scheduler thread ---
    # (the router itself is registered below, so include_router=False)
    setup_vehicle_maintenance(app, include_router=False)

    try:
        yield
    finally:
        alarm_media_stop.set()                    # graceful stop: running copies are aborted, their records stay NULL
        alarm_media_thread.join(timeout=15)
        shutdown_vehicle_maintenance(app)
        await stop_tyre_maintenance_scheduler()
        logger.info("SafeFare Backend shutting down.")



app = FastAPI(
    title="SafeFare Backend",
    description=(
        "Combined API: Iris AI (SafeFare AI Assistant) + "
        "IoT Sensor Data Ingestion (AWS S3 to SQL Server) + "
        "Tyre Maintenance + Vehicle Maintenance + BMS vs Sensor comparison + Alarm media migration"
    ),
    version="1.0.0",
    lifespan=lifespan,
    root_path=os.getenv("ROOT_PATH", "/safe-fare-python"),
    docs_url="/docs",
    openapi_url="/openapi.json",
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",                 # local development only; remove when not needed
    "https://safefareai.sconexsoft.com",
    "https://safefareai-ui-sconex.vercel.app",
    "https://safefareai-ui.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization", "X-Tenant-ID"],
    max_age=600,
)




@app.get("/")
def root():
    return {
        "success": True,
        "message": "SafeFare Backend is running (Iris AI, IoT Sensors, Tyre Maintenance, Vehicle Maintenance, BMS vs Sensor)"
    }


# Iris AI health check
@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# Register API routes
app.include_router(chat_router)                  # /api/chat/...
app.include_router(sensor_router)                # /api/sensors/...
app.include_router(tyre_maintenance_router)      # /api/v1/tyre-maintenance/...
app.include_router(vehicle_maintenance_router)   # /api/vehicle-maintenance/...
app.include_router(bms_router)                   # /api/bms/...
app.include_router(bms_sensor_router)            # /api/bms-sensor/...
app.include_router(alarm_media_router)           # /api/alarm-media/urls (signed viewing links)