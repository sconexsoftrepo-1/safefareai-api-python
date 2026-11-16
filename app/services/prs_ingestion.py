import bisect
import logging
from datetime import timedelta
from typing import Any, Dict, List

from app.config.settings import settings
from app.database.prs_repository import (
    get_vehicle_device_by_iot_kit,
    get_device_positions,
    insert_prs_readings,
)
from app.services.csv_parser import parse_csv_file
from app.services.vendor_location_service import get_vehicle_location

logger = logging.getLogger(__name__)


def attach_positions(
    readings: List[Dict[str, Any]],
    positions: List[Dict[str, Any]],
    max_gap_seconds: int,
) -> int:
    """
    Give every reading the lat/long of the device_positions row whose
    received_at is closest to the reading timestamp (an exact match wins).
    Rows further than max_gap_seconds away are ignored -> lat/long stay None.

    `positions` must be sorted by received_at. Returns how many readings got a position.
    """

    times = [position["received_at"] for position in positions]
    matched = 0

    for reading in readings:
        reading["lat"] = None
        reading["long"] = None

        if not times:
            continue

        timestamp = reading["timestamp"]
        index = bisect.bisect_left(times, timestamp)

        candidates = [
            i for i in (index - 1, index) if 0 <= i < len(times)
        ]

        best = min(
            candidates,
            key=lambda i: abs((times[i] - timestamp).total_seconds()),
        )

        gap = abs((times[best] - timestamp).total_seconds())

        if gap <= max_gap_seconds:
            reading["lat"] = positions[best]["lat"]
            reading["long"] = positions[best]["lon"]
            matched += 1

    return matched


def process_prs_csv(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Process one PRS_... CSV file into dbo.prs_sensor_readings.

    1. Parse + validate rows (kit = the name after "PRS_")
    2. Find the vehicle / device of that kit
    3. Get lat/long: from the GPS vendor API (default), or from dbo.device_positions
       by nearest received_at (PRS_LOCATION_SOURCE=device_positions)
    4. Insert into dbo.prs_sensor_readings
    """

    logger.info("Starting PRS CSV processing: %s", filename)

    readings = parse_csv_file(file_content, filename)

    if not readings:
        logger.warning("PRS CSV contains no readings: %s", filename)

        return {
            "success": True,
            "filename": filename,
            "iot_kit": None,
            "inserted_count": 0,
            "positions_matched": 0,
            "message": "CSV contains no PRS readings",
        }

    iot_kit = readings[0]["iot_kit"]

    vehicle = get_vehicle_device_by_iot_kit(iot_kit)

    if vehicle is None:
        raise ValueError(
            f"No vehicle mapping found for IoT kit: {iot_kit}"
        )

    for reading in readings:
        reading["tenant_id"] = vehicle["tenant_id"]
        reading["vehicle_number"] = vehicle["vehicle_number"]
        reading["iot_kit"] = vehicle["iot_kit"]

    matched = 0

    # A file that carries its own lat/long columns (sample / simulator files) keeps them.
    file_has_position = all(
        reading.get("lat") is not None and reading.get("long") is not None
        for reading in readings
    )

    if file_has_position:
        matched = len(readings)

    elif settings.PRS_LOCATION_SOURCE != "device_positions":
        # One vendor call per file; every row of the file gets the same position.
        location = get_vehicle_location(vehicle["vehicle_number"], vehicle["device_id"])

        for reading in readings:
            reading["lat"] = location[0] if location else None
            reading["long"] = location[1] if location else None

        matched = len(readings) if location else 0

        if not location:
            logger.warning(
                "PRS %s: no position from the vendor API; lat/long left empty.",
                filename,
            )

    elif vehicle["device_id"] is None:
        logger.warning(
            "Vehicle %s has no device_id; PRS lat/long left empty.",
            vehicle["vehicle_number"],
        )
        attach_positions(readings, [], 0)
    else:
        gap = max(1, settings.PRS_POSITION_MAX_GAP_SECONDS)
        window = timedelta(seconds=gap)

        positions = get_device_positions(
            vehicle["tenant_id"],
            vehicle["device_id"],
            min(r["timestamp"] for r in readings) - window,
            max(r["timestamp"] for r in readings) + window,
        )

        matched = attach_positions(readings, positions, gap)

        if matched < len(readings):
            logger.warning(
                "PRS %s: %s of %s readings have no device_positions row "
                "within %s seconds; lat/long left empty.",
                filename,
                len(readings) - matched,
                len(readings),
                gap,
            )

    inserted_count = insert_prs_readings(readings)

    logger.info(
        "PRS CSV processing completed: %s | Inserted: %s | With position: %s",
        filename,
        inserted_count,
        matched,
    )

    return {
        "success": True,
        "filename": filename,
        "iot_kit": iot_kit,
        "vehicle_number": vehicle["vehicle_number"],
        "tenant_id": vehicle["tenant_id"],
        "inserted_count": inserted_count,
        "positions_matched": matched,
        "message": "PRS readings inserted successfully",
    }