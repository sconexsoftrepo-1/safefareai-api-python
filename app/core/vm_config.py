"""Settings for the vehicle maintenance module.

If your project already has a settings object, map these values onto it in
``get_settings`` instead of reading the environment twice.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import time
from functools import lru_cache

try:  # optional: load .env when python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else default


def _identifier(name: str, default: str) -> str:
    value = (os.getenv(name) or default).strip()
    if not _IDENTIFIER.match(value):
        raise ValueError(f"{name} must be a plain SQL identifier")
    return value


def _tenant_windows(name: str) -> dict:
    """VM_TENANT_WINDOWS="101=45;202=60" -> {"101": 45, "202": 60} (per-organization default window)."""
    raw = (os.getenv(name) or "").strip()
    out: dict = {}
    for part in filter(None, (p.strip() for p in re.split(r"[;,]", raw))):
        tenant, _, days = part.partition("=")
        if not tenant.strip() or not days.strip().isdigit() or int(days) <= 0:
            raise ValueError(f"{name} must look like 101=45;202=60 (tenant_id=days)")
        out[tenant.strip()] = int(days)
    return out


def _time(name: str, default: str) -> time:
    raw = (os.getenv(name) or default).strip()
    hh, mm = raw.split(":")
    return time(int(hh), int(mm))


@dataclass(frozen=True)
class Settings:
    db_server: str
    db_database: str
    db_username: str
    db_password: str
    db_port: int
    db_driver: str
    db_encrypt: str
    db_trust_server_certificate: str
    db_schema: str
    db_connect_timeout: int
    db_lock_timeout_ms: int

    app_timezone: str
    db_timestamps_utc: bool

    vehicles_table: str
    max_reason_length: int
    default_window_days: int
    tenant_windows: dict
    max_page_size: int
    driver_can_postpone: bool

    scheduler_enabled: bool
    scheduler_run_at: time
    scheduler_run_on_startup: bool
    overdue_reminder_every_days: int
    notify_fleet_owner: bool

    def __repr__(self) -> str:  # never leak the password through logs
        return (
            f"Settings(db_server={self.db_server!r}, db_database={self.db_database!r}, "
            f"db_username={self.db_username!r}, db_password='***', app_timezone={self.app_timezone!r})"
        )


@lru_cache
def get_settings() -> Settings:
    every = _int("VM_OVERDUE_REMINDER_EVERY_DAYS", 1)
    if every < 1:
        raise ValueError("VM_OVERDUE_REMINDER_EVERY_DAYS must be >= 1")
    return Settings(
        db_server=os.getenv("VM_DB_SERVER", ""),
        db_database=os.getenv("VM_DB_DATABASE", ""),
        db_username=os.getenv("VM_DB_USERNAME", ""),
        db_password=os.getenv("VM_DB_PASSWORD", ""),
        db_port=_int("VM_DB_PORT", 1433),
        db_driver=os.getenv("VM_DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        db_encrypt=os.getenv("VM_DB_ENCRYPT", "yes"),
        db_trust_server_certificate=os.getenv("VM_DB_TRUST_SERVER_CERTIFICATE", "no"),
        db_schema=_identifier("VM_DB_SCHEMA", "dbo"),
        db_connect_timeout=_int("VM_DB_CONNECT_TIMEOUT", 15),
        db_lock_timeout_ms=_int("VM_DB_LOCK_TIMEOUT_MS", 10000),
        app_timezone=os.getenv("VM_APP_TIMEZONE", "Asia/Kolkata"),
        db_timestamps_utc=_bool("VM_DB_TIMESTAMPS_UTC", False),
        vehicles_table=_identifier("VM_VEHICLES_TABLE", "vehicles"),
        max_reason_length=_int("VM_MAX_REASON_LENGTH", 500),
        default_window_days=_int("VM_DEFAULT_WINDOW_DAYS", 30),
        tenant_windows=_tenant_windows("VM_TENANT_WINDOWS"),
        max_page_size=_int("VM_MAX_PAGE_SIZE", 100),
        driver_can_postpone=_bool("VM_DRIVER_CAN_POSTPONE", True),
        scheduler_enabled=_bool("VM_SCHEDULER_ENABLED", True),
        scheduler_run_at=_time("VM_SCHEDULER_RUN_AT", "08:00"),
        scheduler_run_on_startup=_bool("VM_SCHEDULER_RUN_ON_STARTUP", False),
        overdue_reminder_every_days=every,
        notify_fleet_owner=_bool("VM_NOTIFY_FLEET_OWNER", False),
    )
