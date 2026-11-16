"""Background worker for the BMS vs Sensor comparison.

Runs every BMS_WORKER_INTERVAL_SECONDS (default 10) in its own thread, started from app/main.py next to the existing
S3 / PRS workers. It only READS what the PRS worker already stored in dbo.prs_sensor_readings - it does not call S3
or the sensor / GPS vendor API.
"""
import logging
import threading
import time
from typing import Optional

from app.config.bms_config import BmsConfig, load_bms_config

logger = logging.getLogger(__name__)


def start_bms_comparison_worker(
    stop_event: Optional[threading.Event] = None,
    cfg: Optional[BmsConfig] = None,
    service=None,
):
    cfg = cfg or load_bms_config()

    if not cfg.enabled:
        logger.info("BMS comparison worker is disabled (BMS_COMPARISON_ENABLED=false).")
        return

    if service is None:
        from app.database.bms_repository import BmsRepository
        from app.services.bms_comparison_service import BmsComparisonService
        service = BmsComparisonService(BmsRepository(cfg.source_table), cfg)

    stop_event = stop_event or threading.Event()
    logger.info("BMS comparison worker started. Interval: %ss | entry %sm | exit %sm | dwell %ss",
                cfg.interval_seconds, cfg.entry_radius_m, cfg.exit_radius_m, cfg.min_dwell_seconds)

    while not stop_event.is_set():
        started = time.monotonic()
        try:
            service.run_cycle()
        except Exception:                       # SQL down etc.: log, keep the worker alive, retry next cycle
            logger.exception("BMS comparison cycle failed.")
        stop_event.wait(max(0.0, cfg.interval_seconds - (time.monotonic() - started)))

    logger.info("BMS comparison worker stopped.")