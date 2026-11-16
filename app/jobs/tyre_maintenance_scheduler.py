import asyncio
import logging
import os

from dotenv import load_dotenv

from app.repositories import tyre_maintenance_repository as repo
from app.services import tyre_maintenance_service as service


load_dotenv()

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = int(
    os.getenv("TYRE_MAINTENANCE_CHECK_INTERVAL", "5")
)

_scheduler_task = None
_scheduler_running = False


async def tyre_maintenance_loop():
    """
    Periodically checks tyre usage for all initialized vehicles.

    Current responsibilities:
    - Read tenant_id and device_id combinations.
    - Calculate current tyre distance.
    - Update maintenance status.
    - Log errors without stopping the scheduler.

    Notification delivery will be integrated in a later step.
    """

    global _scheduler_running

    if _scheduler_running:
        logger.warning(
            "Tyre maintenance scheduler is already running."
        )
        return

    _scheduler_running = True

    logger.info(
        "Tyre maintenance scheduler started. Interval: %s seconds",
        CHECK_INTERVAL_SECONDS,
    )

    try:
        while True:

            try:
                maintenance_keys = await asyncio.to_thread(
                    repo.get_all_maintenance_keys
                )

                for tenant_id, device_id in maintenance_keys:

                    try:
                        result = await asyncio.to_thread(
                            service.get_tyre_maintenance,
                            tenant_id,
                            device_id,
                        )

                        await asyncio.to_thread(
                            service.check_and_create_alert,
                            result,
                        )

                        logger.info(
                            "Tyre check | Tenant: %s | Device: %s | "
                            "Distance: %s km | Usage: %s%% | Status: %s",
                            tenant_id,
                            device_id,
                            result["current_distance_km"],
                            result["usage_percentage"],
                            result["maintenance_status"],
                        )

                    except Exception:
                        logger.exception(
                            "Tyre check failed for tenant %s, device %s",
                            tenant_id,
                            device_id,
                        )

            except Exception:
                logger.exception(
                    "Tyre maintenance scheduler iteration failed."
                )

            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    finally:
        _scheduler_running = False
        logger.info("Tyre maintenance scheduler stopped.")


def start_tyre_maintenance_scheduler():
    """
    Start the background scheduler.
    """

    global _scheduler_task

    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(
            tyre_maintenance_loop()
        )

        logger.info("Tyre maintenance scheduler task created.")


async def stop_tyre_maintenance_scheduler():
    """
    Stop the background scheduler cleanly.
    """

    global _scheduler_task

    if _scheduler_task and not _scheduler_task.done():

        _scheduler_task.cancel()

        try:
            await _scheduler_task

        except asyncio.CancelledError:
            logger.info(
                "Tyre maintenance scheduler cancellation completed."
            )

    _scheduler_task = None