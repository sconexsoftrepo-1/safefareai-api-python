import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.database.sensor_connection import get_db_connection

logger = logging.getLogger(__name__)


def get_vehicle_device_by_iot_kit(iot_kit: str) -> Optional[Dict[str, Any]]:
    """
    Find the vehicle (and its device) for an IoT kit.

    dbo.vehicles : iot_kit -> tenant_id, vehicle_number, device_id

    The kit name written in a PRS file name can differ from vehicles.iot_kit only in
    punctuation / case (the device sends IOT_KIT001, the table has IOT-KIT-001), so an
    exact match is tried first and then a match that ignores "-", "_", spaces and case.
    Returns None if there is no such vehicle, or if the loose match is ambiguous.
    """

    simplified = re.sub(r"[^A-Za-z0-9]", "", iot_kit).upper()

    query = """
        SELECT
            tenant_id,
            vehicle_number,
            iot_kit,
            device_id
        FROM dbo.vehicles
        WHERE iot_kit = ?
           OR UPPER(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(iot_kit)), '-', ''), '_', ''), ' ', '')) = ?
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query, (iot_kit, simplified))
        rows = cursor.fetchall()

        if not rows:
            logger.warning("No vehicle found for IoT kit: %s", iot_kit)
            return None

        matches = [r for r in rows if r[2] == iot_kit] or rows

        if len(matches) > 1:
            logger.warning(
                "IoT kit %s matches %s vehicles; not guessing.",
                iot_kit,
                len(matches),
            )
            return None

        row = matches[0]

        return {
            "tenant_id": row[0],
            "vehicle_number": row[1],
            "iot_kit": row[2],
            "device_id": row[3],
        }

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_device_positions(
    tenant_id: int,
    device_id: int,
    start: datetime,
    end: datetime,
) -> List[Dict[str, Any]]:
    """
    Positions of one device with received_at between start and end
    (dbo.device_positions), oldest first.
    """

    query = """
        SELECT
            received_at,
            lat,
            lon
        FROM dbo.device_positions
        WHERE tenant_id = ?
          AND device_id = ?
          AND received_at BETWEEN ? AND ?
        ORDER BY received_at
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query, (tenant_id, device_id, start, end))

        return [
            {"received_at": row[0], "lat": row[1], "lon": row[2]}
            for row in cursor.fetchall()
        ]

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def insert_prs_readings(readings: List[Dict[str, Any]]) -> int:
    """
    Insert rows into dbo.prs_sensor_readings.

    Each reading needs: tenant_id, vehicle_number, iot_kit, timestamp,
    sensor_sub_id, sensor_data, lat, long   (lat/long may be None)

    Returns the number of inserted rows.
    """

    if not readings:
        logger.info("No PRS readings available for insertion.")
        return 0

    insert_query = """
        INSERT INTO dbo.prs_sensor_readings
        (
            tenant_id,
            vehicle_number,
            iot_kit,
            [timestamp],
            sensor_sub_id,
            sensor_data,
            lat,
            [long]
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    insert_query_with_snapshot = """
        INSERT INTO dbo.prs_sensor_readings
        (
            tenant_id,
            vehicle_number,
            iot_kit,
            [timestamp],
            sensor_sub_id,
            sensor_data,
            lat,
            [long],
            snapshot_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = [
        (
            reading["tenant_id"],
            reading["vehicle_number"],
            reading["iot_kit"],
            reading["timestamp"],
            reading["sensor_sub_id"],
            reading["sensor_data"],
            reading["lat"],
            reading["long"],
        )
        for reading in readings
    ]

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Migration 003 adds dbo.prs_sensor_readings.snapshot_id. When it exists, every row of this call
        # (= one PRS file = one 60-seat sensor response) gets the SAME id so the BMS comparison can group
        # the 60 seats reliably. Without the column the insert behaves exactly as before.
        cursor.execute("SELECT COL_LENGTH('dbo.prs_sensor_readings', 'snapshot_id')")
        if cursor.fetchone()[0] is not None:
            snapshot_id = str(uuid.uuid4())
            insert_query = insert_query_with_snapshot
            values = [value + (snapshot_id,) for value in values]

        # fast_executemany is not used: it can fail on NULL lat/long values.
        cursor.executemany(insert_query, values)
        connection.commit()

        logger.info(
            "Inserted %s PRS readings. With position: %s",
            len(values),
            sum(1 for reading in readings if reading["lat"] is not None),
        )

        return len(values)

    except Exception:
        if connection:
            connection.rollback()

        logger.exception("Failed to insert PRS readings.")
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()