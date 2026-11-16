import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.database.sensor_connection import (
    get_db_connection,
    test_db_connection
)
from app.services.alert_grouping import DEFAULT_MAX_GAP_SECONDS, detect_alerts, summarise
from app.services.s3_service import s3_service
from app.services.sensor_types import SENSOR_TYPE_SQL
from app.workers.s3_polling_worker import process_s3_file

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sensors",
    tags=["Sensors"]
)


@router.get("/health")
def sensor_health():
    return {
        "success": True,
        "message": "Sensor backend is running"
    }


@router.get("/database/test")
def database_test():
    result = test_db_connection()

    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result["error"]
        )

    return result


@router.post("/process-s3")
def manually_process_s3_files():
    """
    Manually process CSV files available in S3.
    """

    try:
        files = s3_service.list_csv_files()

        results = []

        for file_info in files:
            result = process_s3_file(file_info)

            results.append({
                "filename": file_info["filename"],
                "success": result is not None,
                "result": result
            })

        return {
            "success": True,
            "files_found": len(files),
            "results": results
        }

    except Exception:
        logger.exception("Manual S3 processing failed.")

        raise HTTPException(
            status_code=500,
            detail="Unable to process S3 files"
        )


@router.get("/alerts")
def get_sensor_alerts(
    tenant_id: Optional[int] = Query(default=None),
    vehicle_number: Optional[str] = Query(default=None),
    sensor_sub_id: Optional[int] = Query(default=None, description="1=IR 2=ULT 3=SMK 4=ALC 5=PRS. Leave empty for all sensors."),
    from_time: Optional[str] = Query(default=None, description="Only readings from this time, e.g. 2026-11-10 00:00:00"),
    to_time: Optional[str] = Query(default=None, description="Only readings up to this time"),
    max_gap_seconds: int = Query(default=DEFAULT_MAX_GAP_SECONDS, ge=0, description="If the next reading comes more than this many seconds after the last 1, the alert ends at that last 1 (0 = off)"),
    raw: bool = Query(default=False, description="true = the old list of every alert reading, ungrouped"),
):
    """
    Sensor alerts = every run of 1s, and how long it lasts.

    For each sensor (per vehicle and IoT kit) the readings are followed in time order. Each run of is_alert = 1 is
    one alert: started_at is the row where the 1 first appears, ended_at is the first row where the value is 0
    again, and lasted_seconds is the time between them. If it has not gone back to 0 yet, ongoing is true and the
    time runs to the latest reading. Changes from 1 to 0 are not alerts.

    max_gap_seconds (default 60): if the sensor sends nothing for longer than this after its last 1 (for example
    the device was off), the alert ends at that last 1 and the silent time is not counted. 0 turns this off.

    - No sensor_sub_id: alerts of all sensors, plus a summary with the count per sensor and the total.
    - sensor_sub_id given: only that sensor's alerts.
    - raw=true: the earlier behaviour, one row per alert reading.
    """

    where = ["1=1"]
    params = []
    if tenant_id is not None:
        where.append("tenant_id = ?")
        params.append(tenant_id)
    if vehicle_number is not None:
        where.append("vehicle_number = ?")
        params.append(vehicle_number)
    if sensor_sub_id is not None:
        where.append("sensor_sub_id = ?")
        params.append(sensor_sub_id)
    if from_time is not None:
        where.append("[timestamp] >= ?")
        params.append(from_time)
    if to_time is not None:
        where.append("[timestamp] <= ?")
        params.append(to_time)

    filters = {
        "tenant_id": tenant_id,
        "vehicle_number": vehicle_number,
        "sensor_sub_id": sensor_sub_id,
        "from_time": from_time,
        "to_time": to_time,
    }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if raw:
            cursor.execute(
                f"""
                SELECT tenant_id, vehicle_number, iot_kit, [timestamp], sensor_sub_id,
                       {SENSOR_TYPE_SQL} AS sensor_type, sensor_data, is_alert
                FROM dbo.sensor_readings
                WHERE is_alert = 1 AND {" AND ".join(where)}
                ORDER BY [timestamp] ASC
                """,
                params,
            )
            columns = [c[0] for c in cursor.description]
            alerts = [
                {c: (v.isoformat() if hasattr(v, "isoformat") else v) for c, v in zip(columns, row)}
                for row in cursor.fetchall()
            ]
            return {"success": True, "filters": filters, "count": len(alerts), "alerts": alerts}

        # Every reading is needed (not only alerts) so that 0 -> 1 and 1 -> 0 changes can be seen.
        cursor.execute(
            f"""
            SELECT tenant_id, vehicle_number, iot_kit, [timestamp], sensor_sub_id, sensor_data, is_alert
            FROM dbo.sensor_readings
            WHERE {" AND ".join(where)}
            ORDER BY tenant_id, vehicle_number, iot_kit, sensor_sub_id, [timestamp]
            """,
            params,
        )

        def stream():
            while True:
                batch = cursor.fetchmany(5000)
                if not batch:
                    return
                for r in batch:
                    yield {
                        "tenant_id": r[0], "vehicle_number": r[1], "iot_kit": r[2], "timestamp": r[3],
                        "sensor_sub_id": r[4], "sensor_data": r[5], "is_alert": r[6],
                    }

        alerts = detect_alerts(stream(), max_gap_seconds)

        return {
            "success": True,
            "filters": {**filters, "max_gap_seconds": max_gap_seconds},
            "summary": summarise(alerts, sensor_sub_id),
            "count": len(alerts),
            "alerts": alerts,
        }

    except Exception:
        logger.exception("Failed to retrieve sensor alerts.")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve sensor alerts"
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()