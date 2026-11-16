import csv
import io
import logging
import re

from datetime import datetime
from typing import List, Dict, Any

from app.services.sensor_types import (
    PRS_FILE_PREFIX,
    PRS_SENSOR_SUB_ID,
    PRS_READING_VALUES,
    PRS_MAX_SEAT_NUMBER,
)

logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = {
    "timestamp",
    "sensor_sub_id",
    "sensor_data"
}

# Seat-pressure (PRS) files only need a timestamp plus the seat data, which can be
# given either as  sensor_data = "unique_number:A1,reading:occupied"
# or as two columns  unique_number , reading.
PRS_REQUIRED_COLUMNS = {"timestamp"}


def extract_iot_kit(filename: str) -> str:
    """
    Extract actual IoT kit ID from filename.

    Example:
    IOT-KIT-001_06-11-2026_18-32-25.CSV

    Returns:
    IOT-KIT-001
    """

    pattern = r"^(.+?)_\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}\.csv$"

    match = re.match(pattern, filename, re.IGNORECASE)

    if not match:
        raise ValueError(
            f"Invalid CSV filename format: {filename}"
        )

    return match.group(1)


def is_prs_file(filename: str) -> bool:
    """True for seat-pressure files, e.g. PRS_IOT-KIT-001_10-11-2026_11-45-00.csv"""
    return filename.strip().upper().startswith(PRS_FILE_PREFIX)


def extract_iot_kit_for_file(filename: str) -> str:
    """
    IoT kit ID the file belongs to.

    Normal file : IOT-KIT-001_06-11-2026_18-32-25.csv      -> IOT-KIT-001
    PRS file    : PRS_IOT-KIT-001_10-11-2026_11-45-00.csv  -> IOT-KIT-001
                  (everything after the "PRS_" prefix)
    """
    kit = extract_iot_kit(filename)

    if is_prs_file(filename):
        kit = kit[len(PRS_FILE_PREFIX):]

        if not kit:
            raise ValueError(
                f"No IoT kit ID after the PRS prefix: {filename}"
            )

    return kit


def build_prs_sensor_data(row: Dict[str, Any]) -> str:
    """
    Validate one PRS row and return it as  "unique_number:A1,reading:occupied".

    unique_number : A1 .. A60   ("seat_number" is accepted as an alias)
    reading       : occupied | not_occupied | no_data   ("not occupied" is accepted too)
    """
    values = {}

    # Data can come from separate columns ...
    for column in ("unique_number", "seat_number", "reading", "seating"):
        if row.get(column) not in (None, ""):
            values[column] = str(row[column]).strip()

    # ... or from the sensor_data text  "unique_number:A1,reading:occupied".
    for item in str(row.get("sensor_data") or "").split(","):
        if ":" in item:
            key, value = item.split(":", 1)
            values.setdefault(key.strip().lower(), value.strip())

    unique_number = (
        values.get("unique_number") or values.get("seat_number") or ""
    ).upper()

    reading = (
        values.get("reading") or values.get("seating") or ""
    ).lower().replace(" ", "_")

    number = unique_number[1:] if unique_number[:1] == "A" else ""

    if not (number.isdigit() and 1 <= int(number) <= PRS_MAX_SEAT_NUMBER):
        raise ValueError(
            f"unique_number must be A1 to A{PRS_MAX_SEAT_NUMBER}, "
            f"got '{unique_number}'"
        )

    if reading not in PRS_READING_VALUES:
        raise ValueError(
            f"reading must be one of {', '.join(PRS_READING_VALUES)}, got '{reading}'"
        )

    return f"unique_number:{unique_number},reading:{reading}"


def parse_optional_position(row: Dict[str, Any]):
    """(lat, long) from optional CSV columns lat/long (or latitude/longitude); (None, None) when absent or empty."""
    raw_lat = row.get("lat") if row.get("lat") not in (None, "") else row.get("latitude")
    raw_lon = row.get("long") if row.get("long") not in (None, "") else (
        row.get("longitude") if row.get("longitude") not in (None, "") else row.get("lon"))

    if raw_lat in (None, "") or raw_lon in (None, ""):
        return None, None

    lat, lon = float(raw_lat), float(raw_lon)          # ValueError -> reported with the row number by the caller

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"lat/long out of range: {lat}, {lon}")

    return lat, lon


def parse_timestamp(timestamp_value: str) -> datetime:
    """
    Parse timestamp from CSV.

    Supported formats:
    YYYY-MM-DD HH:MM:SS
    YYYY-MM-DDTHH:MM:SS
    DD-MM-YYYY HH:MM:SS

    Returns a datetime value.
    """

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                timestamp_value.strip(),
                date_format
            )
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported timestamp format: {timestamp_value}"
    )


def parse_csv_file(
    file_content: bytes,
    filename: str
) -> List[Dict[str, Any]]:
    """
    Parse CSV downloaded from S3.

    Expected CSV columns:
        timestamp
        sensor_sub_id   (1=IR, 2=ULT, 3=SMK, 4=ALC)
        sensor_data

    An old "iot_kit_id" column, if a file still has one, is ignored: the
    sensor type now comes from sensor_sub_id.

    Returns a list of sensor readings.
    """

    iot_kit = extract_iot_kit_for_file(filename)
    prs_file = is_prs_file(filename)

    try:
        decoded_content = file_content.decode("utf-8-sig")

    except UnicodeDecodeError as error:
        raise ValueError(
            f"CSV file is not valid UTF-8: {filename}"
        ) from error

    csv_file = io.StringIO(decoded_content)

    reader = csv.DictReader(csv_file)

    if not reader.fieldnames:
        raise ValueError(
            f"CSV file is empty or has no header: {filename}"
        )

    actual_columns = {
        column.strip() for column in reader.fieldnames
        if column
    }

    missing_columns = (
        PRS_REQUIRED_COLUMNS if prs_file else REQUIRED_COLUMNS
    ) - actual_columns

    if missing_columns:
        raise ValueError(
            f"Missing CSV columns in {filename}: "
            f"{', '.join(sorted(missing_columns))}"
        )

    readings = []

    for row_number, row in enumerate(reader, start=2):

        try:
            if prs_file:
                prs_reading = {
                    "iot_kit": iot_kit,
                    "timestamp": parse_timestamp(row["timestamp"]),
                    "sensor_sub_id": PRS_SENSOR_SUB_ID,
                    "sensor_data": build_prs_sensor_data(row),
                }
                # Optional position carried by the file itself (columns lat,long). Files without these
                # columns behave exactly as before (position comes from the vendor API / device_positions).
                lat, lon = parse_optional_position(row)
                if lat is not None:
                    prs_reading["lat"], prs_reading["long"] = lat, lon
                readings.append(prs_reading)
                continue

            reading = {
                "iot_kit": iot_kit,
                "timestamp": parse_timestamp(
                    row["timestamp"]
                ),
                "sensor_sub_id": int(
                    row["sensor_sub_id"]
                ),
                "sensor_data": (
                    row["sensor_data"].strip()
                    if row["sensor_data"] is not None
                    else None
                )
            }

            readings.append(reading)

        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError(
                f"Invalid data at row {row_number} "
                f"in {filename}: {error}"
            ) from error

    logger.info(
        "Parsed %s sensor readings from %s",
        len(readings),
        filename
    )

    return readings