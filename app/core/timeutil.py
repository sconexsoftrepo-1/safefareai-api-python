"""Time and value parsing helpers for vendor payloads.

The vendor documents all query times as UTC `yyyy-MM-dd HH:mm:ss`. Some responses (5.4/5.8 routine alarms)
return Java `Date.toString()` values such as `Tue Oct 24 17:36:49 CST 2023`; see parse_vendor_time.
All datetimes inside this service are naive UTC, matching the datetime2 columns.
"""
import math
import re
from datetime import UTC, date, datetime, timedelta

from app.core.exceptions import BadRequestError

VENDOR_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                       "Nov", "Dec"], start=1)}
_JAVA_DATE = re.compile(r"^[A-Z][a-z]{2} ([A-Z][a-z]{2}) (\d{1,2}) (\d{2}):(\d{2}):(\d{2}) ([A-Z]{2,5}) (\d{4})$")
# ASSUMPTION: the vendor platform is hosted in China, so Java's "CST" is China Standard Time (UTC+8).
_ZONE_OFFSET_HOURS = {"UTC": 0, "GMT": 0, "CST": 8}
_DURATION_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*(days?|d|hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)",
                             re.IGNORECASE)
_DURATION_UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def to_utc_naive(value: datetime) -> datetime:
    """Normalise a request datetime: aware values are converted to UTC, naive values are taken as UTC."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value.replace(microsecond=0)


def fmt_vendor(value: datetime) -> str:
    return to_utc_naive(value).strftime(VENDOR_TIME_FORMAT)


def validate_range(start: datetime, end: datetime, max_days: int) -> tuple[datetime, datetime]:
    start, end = to_utc_naive(start), to_utc_naive(end)
    if end <= start:
        raise BadRequestError("endTime must be after startTime", code="INVALID_TIME_RANGE")
    if end - start > timedelta(days=max_days):
        raise BadRequestError(f"Time range must not exceed {max_days} days", code="INVALID_TIME_RANGE")
    return start, end


def parse_vendor_time(value) -> datetime | None:
    """Parse the vendor's time formats into naive UTC. Returns None for empty / '-' / unparseable values."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in ("-", "null"):
        return None
    for fmt in (VENDOR_TIME_FORMAT, "%Y-%m-%d", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    match = _JAVA_DATE.match(text)
    if match:
        mon, day, hh, mm, ss, zone, year = match.groups()
        if mon in _MONTHS and zone in _ZONE_OFFSET_HOURS:
            local = datetime(int(year), _MONTHS[mon], int(day), int(hh), int(mm), int(ss))
            return local - timedelta(hours=_ZONE_OFFSET_HOURS[zone])
    return None


def parse_vendor_date(value) -> date | None:
    parsed = parse_vendor_time(value)
    return parsed.date() if parsed else None


def parse_duration_seconds(value) -> int | None:
    """Parse vendor duration text ('0s', '1h2m3s', '2 min', '01:02:03', '75') into seconds."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return int(float(text))
    if re.fullmatch(r"\d+:\d{2}:\d{2}", text):
        h, m, s = (int(p) for p in text.split(":"))
        return h * 3600 + m * 60 + s
    tokens = _DURATION_TOKEN.findall(text)
    if not tokens or _DURATION_TOKEN.sub("", text).strip():
        return None
    return int(sum(float(n) * _DURATION_UNITS[unit[0].lower()] for n, unit in tokens))


def to_float(value) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def to_int(value) -> int | None:
    result = to_float(value)
    return int(result) if result is not None else None


def valid_lat_lon(lat, lon) -> tuple[float | None, float | None]:
    lat, lon = to_float(lat), to_float(lon)
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None, None
    return lat, lon


def day_range(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into UTC calendar-day windows."""
    windows = []
    cursor = start
    while cursor <= end:
        day_end = min(datetime.combine(cursor.date(), datetime.max.time()).replace(microsecond=0), end)
        windows.append((cursor, day_end))
        cursor = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time())
    return windows
