"""Background worker: copies alarm images / videos from the GPS TrackTech server to our S3 bucket.

Runs every ALARM_MEDIA_INTERVAL_SECONDS (default 5) in its own thread, started from app/main.py next to the other
workers, and stopped with a threading.Event when the backend shuts down. No API call or frontend trigger is needed.
"""
import logging
import threading
import time
from typing import Optional

BACKLOG_POLL_SECONDS = 0.5      # while records are waiting / being copied, look again after this short pause

from app.config.alarm_media_config import AlarmMediaConfig, load_alarm_media_config

logger = logging.getLogger(__name__)


def start_alarm_media_worker(
    stop_event: Optional[threading.Event] = None,
    cfg: Optional[AlarmMediaConfig] = None,
    service=None,
):
    cfg = cfg or load_alarm_media_config()

    if not cfg.enabled:
        logger.info("Alarm media migration worker is disabled (ALARM_MEDIA_MIGRATION_ENABLED=false).")
        return

    stop_event = stop_event or threading.Event()

    if service is None:
        try:
            from app.database.alarm_media_repository import AlarmMediaRepository
            from app.services.alarm_media_service import (
                AlarmMediaMigrationService, S3MediaStorage, UrllibDownloader,
            )
            service = AlarmMediaMigrationService(
                AlarmMediaRepository(cfg.table), S3MediaStorage(), UrllibDownloader(cfg.download_timeout_seconds),
                cfg, stop_event=stop_event,
            )
        except Exception:
            logger.exception("Alarm media migration worker could not start (check the S3 settings in .env).")
            return

    logger.info("Alarm media migration worker started. Interval: %ss | vendor %s | S3 folder %s/ | %s parallel",
                cfg.interval_seconds, cfg.vendor_base_url, cfg.s3_prefix.strip("/"), cfg.max_parallel)

    while not stop_event.is_set():
        started = time.monotonic()
        busy = False
        try:
            busy = bool(service.run_cycle()) or service.in_flight_count() > 0
        except Exception:                       # SQL down etc.: log, keep the worker alive, retry next cycle
            logger.exception("Alarm media migration cycle failed.")
        # Nothing to do: check again every ALARM_MEDIA_INTERVAL_SECONDS (5 s). With a backlog (records just started or
        # still being copied) come back quickly, so a free slot is refilled at once instead of waiting a full interval.
        wait = BACKLOG_POLL_SECONDS if busy else cfg.interval_seconds
        stop_event.wait(max(0.0, wait - (time.monotonic() - started)))

    try:
        service.shutdown()
    except Exception:
        logger.exception("Alarm media migration shutdown failed.")
    logger.info("Alarm media migration worker stopped.")