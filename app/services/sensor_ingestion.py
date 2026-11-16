
import logging
from typing import Dict, Any

from app.services.csv_parser import parse_csv_file
from app.services.vehicle_mapping import get_vehicle_by_iot_kit
from app.services.sensor_alert_service import is_alert_reading
from app.database.sensor_repository import insert_sensor_readings

logger = logging.getLogger(__name__)


def process_sensor_csv(
    file_content: bytes,
    filename: str
) -> Dict[str, Any]:
    """
    Process one sensor CSV file.

    All readings are inserted into SQL Server.
    Alert readings are identified using the is_alert column.
    No email notifications are sent.
    """

    logger.info("Starting CSV processing: %s", filename)

    # 1. Parse CSV
    readings = parse_csv_file(file_content, filename)

    if not readings:
        logger.warning("CSV contains no readings: %s", filename)

        return {
            "success": True,
            "filename": filename,
            "iot_kit": None,
            "inserted_count": 0,
            "alert_count": 0,
            "message": "CSV contains no sensor readings"
        }

    iot_kit = readings[0]["iot_kit"]

    # 2. Find associated vehicle
    vehicle = get_vehicle_by_iot_kit(iot_kit)

    if vehicle is None:
        raise ValueError(
            f"No vehicle mapping found for IoT kit: {iot_kit}"
        )

    # 3. Add vehicle information and calculate alert status
    alert_count = 0

    for reading in readings:
        reading["tenant_id"] = vehicle["tenant_id"]
        reading["vehicle_number"] = vehicle["vehicle_number"]
        reading["iot_kit"] = vehicle["iot_kit"]

        reading["is_alert"] = is_alert_reading(reading)

        if reading["is_alert"]:
            alert_count += 1

    # 4. Insert all readings into SQL Server
    inserted_count = insert_sensor_readings(readings)

    logger.info(
        "CSV processing completed: %s | Inserted: %s | Alerts: %s",
        filename,
        inserted_count,
        alert_count
    )

    return {
        "success": True,
        "filename": filename,
        "iot_kit": iot_kit,
        "vehicle_number": vehicle["vehicle_number"],
        "tenant_id": vehicle["tenant_id"],
        "inserted_count": inserted_count,
        "alert_count": alert_count,
        "message": "Sensor readings inserted successfully"
    }
