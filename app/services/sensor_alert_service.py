import logging
from typing import List, Dict, Any

from app.services.sensor_types import sensor_type_from_sub_id

logger = logging.getLogger(__name__)


def is_alert_reading(reading: Dict[str, Any]) -> bool:
    """
    Identify alert readings based on sensor type and reading status.

    The sensor type comes from sensor_sub_id: 1=IR, 2=ULT, 3=SMK, 4=ALC, 5=PRS.
    PRS (seat occupied / not_occupied) never raises an alert.

    ALC: alert
    SMK: alert
    ULT: danger, warning, no_echo
    IR: no alerts
    """

    sensor_type = sensor_type_from_sub_id(
        reading.get("sensor_sub_id")
    ) or ""

    sensor_data = str(
        reading.get("sensor_data", "")
    ).strip()

    if not sensor_data:
        return False

    values = {}

    for item in sensor_data.split(","):
        if ":" not in item:
            continue

        key, value = item.split(":", 1)
        values[key.strip().lower()] = value.strip().lower()

    status = values.get("reading", "")

    if sensor_type in ("ALC", "SMK"):
        return status == "alert"

    if sensor_type == "ULT":
        return status in ("danger", "warning", "no_echo")

    return False


def extract_alerts(
    readings: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extract alert readings without modifying original readings.
    """

    alerts = [
        reading
        for reading in readings
        if is_alert_reading(reading)
    ]

    logger.info(
        "Found %s alert readings out of %s total readings.",
        len(alerts),
        len(readings)
    )

    return alerts