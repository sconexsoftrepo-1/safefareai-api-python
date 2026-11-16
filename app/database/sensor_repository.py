import logging
from typing import List, Dict, Any

from app.database.sensor_connection import get_db_connection

logger = logging.getLogger(__name__)


def insert_sensor_readings(readings: List[Dict[str, Any]]) -> int:
    """
    Insert sensor readings into dbo.sensor_readings.

    Each reading must contain:
        tenant_id
        vehicle_number
        iot_kit
        timestamp
        sensor_sub_id
        sensor_data
        is_alert

    Returns the number of inserted rows.
    """

    if not readings:
        logger.info("No sensor readings available for insertion.")
        return 0

    insert_query = """
        INSERT INTO dbo.sensor_readings
        (
            tenant_id,
            vehicle_number,
            iot_kit,
            [timestamp],
            sensor_sub_id,
            sensor_data,
            is_alert
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    required_columns = [
        "tenant_id",
        "vehicle_number",
        "iot_kit",
        "timestamp",
        "sensor_sub_id",
        "sensor_data",
        "is_alert"
    ]

    for index, reading in enumerate(readings):
        missing = [
            column for column in required_columns
            if column not in reading
        ]

        if missing:
            raise ValueError(
                f"Reading at index {index} is missing: {missing}"
            )

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.fast_executemany = True

        values = [
            (
                reading["tenant_id"],
                reading["vehicle_number"],
                reading["iot_kit"],
                reading["timestamp"],
                reading["sensor_sub_id"],
                reading["sensor_data"],
                bool(reading["is_alert"])
            )
            for reading in readings
        ]

        cursor.executemany(insert_query, values)

        connection.commit()

        inserted_count = len(values)

        logger.info(
            "Successfully inserted %s sensor readings. Alert readings: %s",
            inserted_count,
            sum(1 for reading in readings if reading["is_alert"])
        )

        return inserted_count

    except Exception:
        if connection:
            connection.rollback()

        logger.exception("Failed to insert sensor readings.")
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()