"""Configuration of the alarm media migration (GPS TrackTech vendor server -> our AWS S3 bucket).

Every value comes from .env (ALARM_MEDIA_*), with the defaults from the requirement. Kept in its own file so
app/config/settings.py is untouched. The S3 bucket, region and credentials are NOT repeated here: the existing
settings (S3_BUCKET_NAME, AWS_REGION, AWS_ACCESS_KEY_ID ...) are reused.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping, Optional


def _flag(value: Optional[str], default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class AlarmMediaConfig:
    enabled: bool = True
    interval_seconds: int = 5                 # worker cycle
    vendor_base_url: str = "https://y.gpstracktech.com"
    s3_prefix: str = "alerts"                 # folder in the existing bucket: alerts/<yyyy-mm-dd>/img|video/<file>
    table: str = "dbo.alarm_media"
    batch_size: int = 20                      # most records started per cycle
    scan_limit: int = 200                     # rows read from the table per cycle (cursor based, see the service)
    max_parallel: int = 4                     # files downloaded / uploaded at the same time
    download_timeout_seconds: int = 30        # connect / read timeout of the vendor request (per socket operation)
    max_attempts: int = 10                    # failures in a row before the record is parked
    backoff_base_seconds: int = 30            # retry delay after the 1st failure, doubled after every further failure
    backoff_max_seconds: int = 3600           # the retry delay never grows beyond this
    park_seconds: int = 86400                 # after max_attempts failures wait this long, then start counting again

    def validate(self) -> "AlarmMediaConfig":
        if not re.fullmatch(r"[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)?", self.table):
            raise ValueError("ALARM_MEDIA_TABLE must look like dbo.table_name")
        if not self.vendor_base_url.lower().startswith(("http://", "https://")):
            raise ValueError("ALARM_MEDIA_VENDOR_BASE_URL must start with http:// or https://")
        if not self.s3_prefix.strip("/"):
            raise ValueError("ALARM_MEDIA_S3_PREFIX must not be empty")
        for name in ("interval_seconds", "batch_size", "scan_limit", "max_parallel", "download_timeout_seconds",
                     "max_attempts", "backoff_base_seconds", "backoff_max_seconds", "park_seconds"):
            if getattr(self, name) < 1:
                raise ValueError(f"ALARM_MEDIA_{name.upper()} must be >= 1")
        return self


def load_alarm_media_config(env: Optional[Mapping[str, str]] = None) -> AlarmMediaConfig:
    """Read AlarmMediaConfig from the environment (or a mapping, for tests)."""
    if env is None:
        from dotenv import load_dotenv      # .env is loaded by app.config.settings too; harmless twice
        load_dotenv()
        env = os.environ

    d = AlarmMediaConfig()

    def num(name: str, default: int) -> int:
        raw = env.get(name)
        return default if raw is None or str(raw).strip() == "" else int(raw)

    def text(name: str, default: str) -> str:
        return (env.get(name) or default).strip() or default

    return AlarmMediaConfig(
        enabled=_flag(env.get("ALARM_MEDIA_MIGRATION_ENABLED"), d.enabled),
        interval_seconds=num("ALARM_MEDIA_INTERVAL_SECONDS", d.interval_seconds),
        vendor_base_url=text("ALARM_MEDIA_VENDOR_BASE_URL", d.vendor_base_url),
        s3_prefix=text("ALARM_MEDIA_S3_PREFIX", d.s3_prefix),
        table=text("ALARM_MEDIA_TABLE", d.table),
        batch_size=num("ALARM_MEDIA_BATCH_SIZE", d.batch_size),
        scan_limit=num("ALARM_MEDIA_SCAN_LIMIT", d.scan_limit),
        max_parallel=num("ALARM_MEDIA_MAX_PARALLEL", d.max_parallel),
        download_timeout_seconds=num("ALARM_MEDIA_DOWNLOAD_TIMEOUT_SECONDS", d.download_timeout_seconds),
        max_attempts=num("ALARM_MEDIA_MAX_ATTEMPTS", d.max_attempts),
        backoff_base_seconds=num("ALARM_MEDIA_BACKOFF_BASE_SECONDS", d.backoff_base_seconds),
        backoff_max_seconds=num("ALARM_MEDIA_BACKOFF_MAX_SECONDS", d.backoff_max_seconds),
        park_seconds=num("ALARM_MEDIA_PARK_SECONDS", d.park_seconds),
    ).validate()