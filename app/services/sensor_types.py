"""Sensor type lookup.

The sensor type is no longer stored as text in a column; it is encoded in
dbo.sensor_readings.sensor_sub_id:

    1 = IR   (passenger counter - no alerts)
    2 = ULT  (ultrasonic: danger / warning / no_echo)
    3 = SMK  (smoke: alert)
    4 = ALC  (alcohol: alert)
    5 = PRS  (seat pressure: unique_number:A1..A60, reading:occupied/not_occupied - no alerts)

PRS data arrives in its own files named  PRS_<iot kit>_<dd-mm-yyyy>_<HH-MM-SS>.csv
and is stored in dbo.prs_sensor_readings (not in sensor_readings).
"""
from typing import Optional

SENSOR_TYPE_BY_SUB_ID = {
    1: "IR",
    2: "ULT",
    3: "SMK",
    4: "ALC",
    5: "PRS",
}

# Files whose name starts with this prefix are seat-pressure files.
PRS_FILE_PREFIX = "PRS_"
PRS_SENSOR_SUB_ID = 5
PRS_READING_VALUES = ("occupied", "not_occupied", "no_data")   # "not occupied" is accepted and normalised
PRS_MAX_SEAT_NUMBER = 60   # unique_number A1 .. A60

# Same mapping as a SQL expression, for queries that need the readable name.
SENSOR_TYPE_SQL = (
    "CASE sensor_sub_id "
    + " ".join(f"WHEN {k} THEN '{v}'" for k, v in SENSOR_TYPE_BY_SUB_ID.items())
    + " ELSE 'UNKNOWN' END"
)


def sensor_type_from_sub_id(sensor_sub_id) -> Optional[str]:
    try:
        return SENSOR_TYPE_BY_SUB_ID.get(int(sensor_sub_id))
    except (TypeError, ValueError):
        return None