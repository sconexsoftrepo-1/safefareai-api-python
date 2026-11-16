import logging
import time

from app.config.settings import settings
from app.services.s3_service import s3_service
from app.services.sensor_ingestion import process_sensor_csv
from app.services.prs_ingestion import process_prs_csv
from app.services.csv_parser import is_prs_file

from app.services.iot_kit_monitoring_service import (
    record_successful_csv,
    check_missing_iot_kits,
)

logger = logging.getLogger(__name__)


def process_prs_s3_file(file_info: dict):
    """
    Download, process and delete one PRS_... S3 CSV file.

    The rows go to dbo.prs_sensor_readings (with lat/long from device_positions).
    The file is deleted only after a successful insert; on any error it stays in S3.
    """

    s3_key = file_info["key"]
    filename = file_info["filename"]

    logger.info("Processing PRS S3 file: %s", filename)

    try:
        file_content = s3_service.download_csv_file(s3_key)

        result = process_prs_csv(file_content, filename)

        if not result or not result.get("success"):
            raise RuntimeError(
                f"PRS database processing failed: {filename}"
            )

        s3_service.delete_csv_file(s3_key)

        logger.info(
            "Successfully processed and deleted PRS file: %s | "
            "Inserted: %s | With position: %s",
            filename,
            result.get("inserted_count", 0),
            result.get("positions_matched", 0),
        )

        return result

    except Exception:
        logger.exception(
            "Failed to process PRS S3 file: %s. File retained in S3.",
            filename
        )
        return None


def process_s3_file(file_info: dict):
    """
    Download, process and delete one S3 CSV file.

    PRS_... files go to prs_sensor_readings (see process_prs_s3_file);
    every other file goes to sensor_readings.

    All sensor readings and alert flags are stored in SQL Server.
    Sensor alert emails are disabled.

    IoT kit missing-data and recovery emails remain enabled.
    """

    if is_prs_file(file_info["filename"]):
        return process_prs_s3_file(file_info)

    s3_key = file_info["key"]
    filename = file_info["filename"]

    logger.info("Processing S3 file: %s", filename)

    try:
        # 1. Download CSV from S3
        file_content = s3_service.download_csv_file(s3_key)

        # 2. Parse, identify alerts and insert all readings into SQL Server
        result = process_sensor_csv(file_content, filename)

        if not result or not result.get("success"):
            raise RuntimeError(
                f"Database processing failed: {filename}"
            )

        # 3. Update IoT kit monitoring after successful DB insertion
        if result.get("iot_kit"):
            record_successful_csv(
                tenant_id=result["tenant_id"],
                vehicle_number=result["vehicle_number"],
                iot_kit=result["iot_kit"],
            )

        # 4. Delete CSV only after successful processing
        s3_service.delete_csv_file(s3_key)

        logger.info(
            "Successfully processed and deleted: %s | "
            "Inserted: %s | Alerts stored: %s",
            filename,
            result.get("inserted_count", 0),
            result.get("alert_count", 0),
        )

        return result

    except Exception:
        logger.exception(
            "Failed to process S3 file: %s. File retained in S3.",
            filename
        )
        return None


def start_s3_polling_worker():
    """
    Continuously poll S3 (every S3_POLL_INTERVAL seconds, default 5) for the
    normal sensor files and monitor all registered IoT kits.
    PRS_... files are NOT handled here - see start_prs_polling_worker().
    """

    logger.info("S3 polling worker started.")

    while True:
        try:
            # 1. List CSV files
            csv_files = s3_service.list_csv_files(prs=False)

            if not csv_files:
                logger.info("No CSV files found in S3.")

            # 2. Process CSV files sequentially
            for file_info in csv_files:
                process_s3_file(file_info)

            # 3. Check missing IoT kits independently of S3 uploads
            logger.info("Starting IoT kit missing-data check.")

            check_missing_iot_kits()

            logger.info("IoT kit monitoring check completed.")

        except Exception:
            logger.exception(
                "S3 polling or IoT monitoring failed."
            )

        # 4. Wait for the next polling cycle
        time.sleep(settings.S3_POLL_INTERVAL)


# A PRS file that failed (bad data, unknown kit, ...) stays in S3. It is not retried
# immediately; it waits this long so the log is not flooded every 10 seconds.
PRS_RETRY_AFTER_SECONDS = 300


def start_prs_polling_worker():
    """
    Continuously poll S3 for PRS_... seat files every PRS_POLL_INTERVAL
    seconds (default 10) and store them in dbo.prs_sensor_readings.
    """

    logger.info("PRS polling worker started.")

    retry_at = {}

    while True:
        try:
            now = time.time()

            for file_info in s3_service.list_csv_files(prs=True):
                key = file_info["key"]

                if retry_at.get(key, 0) > now:
                    continue

                if process_prs_s3_file(file_info) is None:
                    retry_at[key] = now + PRS_RETRY_AFTER_SECONDS
                else:
                    retry_at.pop(key, None)

            # forget entries whose retry time has passed
            for key in [k for k, t in retry_at.items() if t <= now]:
                del retry_at[key]

        except Exception:
            logger.exception("PRS S3 polling failed.")

        time.sleep(settings.PRS_POLL_INTERVAL)