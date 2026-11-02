"""Vendor-backed alarm features: alarm types (5.7), AI events (5.1), routine alarms (5.4 / 5.8)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import VendorInvalidResponseError
from app.core.responses import no_data, ok
from app.core.security import CurrentUser
from app.core.timeutil import to_int, validate_range
from app.db.session import transaction
from app.repositories import alarms as alarm_repo
from app.repositories.common import PersistStats, truncate
from app.repositories.devices import DeviceRef, by_terminal
from app.schemas.alarms import AiEventQuery, RoutineAlarmQuery
from app.services.alarm_ingest import AlarmIngestor
from app.services.common import expect_list, fetch_all_devices, resolve_scope
from app.vendor.api import GpsTrackTechApi

AI_CATEGORIES = [2, 4, 5]       # ADAS, DSM, BSD  (vendor 5.7 "type")
ROUTINE_CATEGORIES = [3]        # general alarms


def sync_alarm_types(db: Session, api: GpsTrackTechApi, category: int = 0) -> tuple[list[dict], PersistStats]:
    rows = expect_list(api.alarm_types(category))
    items = []
    for row in rows:
        type_id, kind, label = to_int(row.get("id")), to_int(row.get("type")), str(row.get("label") or "").strip()
        if type_id is None or kind is None or not 1 <= kind <= 5 or not label:
            continue
        items.append({"id": type_id, "category": kind, "label": truncate(label, 120),
                      "code": truncate(row.get("value") or type_id, 40)})
    if rows and not items:
        raise VendorInvalidResponseError("The vendor returned alarm types in an unexpected format")
    stats = PersistStats()
    if items:
        with transaction(db):
            stats = alarm_repo.upsert_alarm_types(db, items)
    return items, stats


def ensure_type_ids(db: Session, api: GpsTrackTechApi, categories: list[int]) -> list[int]:
    rows = alarm_repo.alarm_types(db, categories)
    if not rows:
        sync_alarm_types(db, api, 0)
        rows = alarm_repo.alarm_types(db, categories)
    return [r.id for r in rows]


def list_alarm_types(db: Session, api: GpsTrackTechApi, category: int) -> dict:
    items, stats = sync_alarm_types(db, api, category)
    if not items:
        return no_data()
    return ok(items, meta={"persisted": stats})


def _visible(rows: list[dict], include_hidden: bool) -> tuple[list[dict], int]:
    if include_hidden:
        return rows, 0
    visible = [r for r in rows if not r.get("hidden")]
    return visible, len(rows) - len(visible)


def ai_events(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, q: AiEventQuery) -> dict:
    start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings)
    type_ids = q.alarm_type_ids or ensure_type_ids(db, api, AI_CATEGORIES)
    response = api.adas_alarms([d.terminal_no for d in devices], type_ids, start, end, q.page, q.page_size)
    rows = expect_list(response)
    if not rows:
        return no_data()
    ingestor = AlarmIngestor(db, user.tenant_id)
    with transaction(db):
        enriched = ingestor.ingest_adas(rows, by_terminal(devices))
    visible, hidden = _visible(enriched, q.include_hidden)
    return ok(visible, meta={"total": response.total, "page": q.page, "pageSize": q.page_size,
                             "hiddenByRules": hidden, "persisted": ingestor.stats})


def routine_alarms(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings,
                   q: RoutineAlarmQuery) -> dict:
    devices = resolve_scope(db, user, q.device_ids, q.group_id, settings)
    type_ids = q.alarm_type_ids or ensure_type_ids(db, api, ROUTINE_CATEGORIES)
    terminals = [d.terminal_no for d in devices]
    if q.start_time is None:
        response = api.recent_routine_alarms(terminals, type_ids, q.page, q.page_size)
        source = "recentlyList (last 24 hours)"
    else:
        start, end = validate_range(q.start_time, q.end_time, settings.query_max_range_days)
        response = api.routine_alarms(terminals, type_ids, start, end, q.page, q.page_size)
        source = "getAlarmInfo"
    rows = expect_list(response)
    if not rows:
        return no_data()
    ingestor = AlarmIngestor(db, user.tenant_id)
    with transaction(db):
        enriched = ingestor.ingest_routine(rows, by_terminal(devices), type_ids)
    visible, hidden = _visible(enriched, q.include_hidden)
    return ok(visible, meta={"total": response.total, "page": q.page, "pageSize": q.page_size, "source": source,
                             "hiddenByRules": hidden, "persisted": ingestor.stats})


def collect_ai_events(db: Session, api: GpsTrackTechApi, tenant_id: int, settings: Settings,
                      devices: list[DeviceRef], start: datetime, end: datetime,
                      type_ids: list[int] | None = None) -> tuple[list[dict], bool, PersistStats]:
    """All AI events for an aggregate view (all pages, all device chunks), persisted as a side effect."""
    type_ids = type_ids or ensure_type_ids(db, api, AI_CATEGORIES)
    rows, truncated = fetch_all_devices(
        lambda terminals, page, size: api.adas_alarms(terminals, type_ids, start, end, page, size), devices, settings)
    ingestor = AlarmIngestor(db, tenant_id)
    if rows:
        with transaction(db):
            rows = ingestor.ingest_adas(rows, by_terminal(devices))
    return rows, truncated, ingestor.stats


def collect_routine_alarms(db: Session, api: GpsTrackTechApi, tenant_id: int, settings: Settings,
                           devices: list[DeviceRef], start: datetime, end: datetime,
                           type_ids: list[int] | None = None) -> tuple[list[dict], bool, PersistStats]:
    type_ids = type_ids or ensure_type_ids(db, api, ROUTINE_CATEGORIES)
    rows, truncated = fetch_all_devices(
        lambda terminals, page, size: api.routine_alarms(terminals, type_ids, start, end, page, size),
        devices, settings)
    ingestor = AlarmIngestor(db, tenant_id)
    if rows:
        with transaction(db):
            rows = ingestor.ingest_routine(rows, by_terminal(devices), type_ids)
    return rows, truncated, ingestor.stats
