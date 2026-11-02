"""Persist vendor alarms into dbo.alarms / alarm_media, applying the tenant's alarm linkage rules.

* AI events (5.1 recentlyAdasList) carry a vendor `alarmId` -> dbo.alarms.vendor_alarm_id.
* Routine alarms (5.4 / 5.8) carry no id and a textual alarm type. A deterministic id is derived from
  (deviceId, alarmType, startTime) so repeated fetches update the same row instead of duplicating it,
  and the type label is mapped back to dbo.alarm_types.
* Rules (dbo.alarm_rules) are matched for NEW alarms only: enabled, alarm type listed in alarm_rule_types,
  group_id NULL or equal to the device's group; lowest `priority` wins. PROCESS+AUTO rules with an
  auto_outcome close the alarm immediately and record an automatic alarm_actions row.
"""
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.timeutil import parse_duration_seconds, parse_vendor_time, to_float, to_int, utcnow, valid_lat_lon
from app.repositories import alarms as alarm_repo
from app.repositories import rules as rule_repo
from app.repositories.common import PersistStats, to_json, truncate
from app.repositories.devices import DeviceRef

DISMISS_OUTCOMES = {"FALSE_POSITIVE", "TEST"}


def routine_alarm_id(device_id: str, alarm_type: str, start_time: str) -> str:
    digest = hashlib.sha1(f"{device_id}|{alarm_type}|{start_time}".encode()).hexdigest()
    return "R" + digest[:39]


class AlarmIngestor:
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.types = alarm_repo.alarm_type_map(db)
        self._rules: list[tuple] | None = None
        self.stats = PersistStats()

    # --- rules ---------------------------------------------------------------------------------------------
    def _load_rules(self) -> list[tuple]:
        if self._rules is None:
            rows = rule_repo.list_rules(self.db, self.tenant_id, enabled_only=True)
            type_map = rule_repo.rule_type_ids(self.db, [r.id for r in rows])
            self._rules = [(r, set(type_map.get(r.id, []))) for r in rows]
        return self._rules

    def match_rule(self, alarm_type_id: int, group_id: int):
        for rule, type_ids in self._load_rules():
            if alarm_type_id in type_ids and (rule.group_id is None or rule.group_id == group_id):
                return rule
        return None

    def is_hidden(self, rule_id: int | None) -> bool:
        if rule_id is None:
            return False
        return any(rule.id == rule_id and rule.handling_mode == "HIDE" for rule, _ in self._load_rules())

    # --- storage -------------------------------------------------------------------------------------------
    def _store(self, device: DeviceRef, alarm_type_id: int, vendor_alarm_id: str, alarm_time: datetime,
               values: dict, media: list[tuple[str, str]]) -> dict:
        existing = alarm_repo.find_alarm(self.db, self.tenant_id, vendor_alarm_id, alarm_time)
        if existing is not None:
            updates = {k: values[k] for k in ("ended_at", "duration_seconds")
                       if values.get(k) is not None and getattr(existing, k) is None}
            added = sum(alarm_repo.add_media_if_absent(self.db, self.tenant_id, existing.id, alarm_time, kind, url)
                        for kind, url in media)
            if added and existing.media_status == "NONE":
                updates["media_status"] = "PENDING"
            if updates:
                alarm_repo.update_alarm(self.db, existing.id, alarm_time, updates)
            self.stats.add("updated" if updates or added else "unchanged")
            return {"localAlarmId": existing.id, "handlingStatus": existing.handling_status,
                    "hidden": self.is_hidden(existing.rule_id)}

        rule = self.match_rule(alarm_type_id, device.group_id)
        status, outcome, handled_at = "NEW", None, None
        auto = rule is not None and rule.handling_mode == "PROCESS" and rule.process_mode == "AUTO" \
            and rule.auto_outcome
        if auto:
            outcome = rule.auto_outcome
            status = "DISMISSED" if outcome in DISMISS_OUTCOMES else "RESOLVED"
            handled_at = utcnow()
        type_row = self.types.get(alarm_type_id)
        alarm_id = alarm_repo.insert_alarm(self.db, {
            "tenant_id": self.tenant_id, "device_id": device.id, "alarm_type_id": alarm_type_id,
            "vendor_alarm_id": vendor_alarm_id, "alarm_time": alarm_time,
            "severity": (type_row.default_severity if type_row else None) or 3, "source": 1,
            "media_status": "PENDING" if media else "NONE", "handling_status": status,
            "handling_outcome": outcome, "handled_at": handled_at, "rule_id": rule.id if rule else None,
            "ingested_at": utcnow(), **values})
        for kind, url in media:
            alarm_repo.add_media_if_absent(self.db, self.tenant_id, alarm_id, alarm_time, kind, url)
        if auto:
            alarm_repo.insert_action(self.db, {
                "tenant_id": self.tenant_id, "alarm_id": alarm_id, "alarm_time": alarm_time,
                "action_type": outcome, "is_automatic": True, "note": truncate(f"Auto-processed by rule '{rule.name}'",
                                                                               1000),
                "created_at": utcnow()})
        self.stats.add("inserted")
        return {"localAlarmId": alarm_id, "handlingStatus": status,
                "hidden": rule is not None and rule.handling_mode == "HIDE"}

    # --- vendor 5.1 ----------------------------------------------------------------------------------------
    def ingest_adas(self, rows: list[dict], devices: dict[str, DeviceRef]) -> list[dict]:
        result = []
        for row in rows:
            device = devices.get(str(row.get("deviceId") or ""))
            type_id = to_int(row.get("alarmType"))
            alarm_time = parse_vendor_time(row.get("alarmTime"))
            vendor_id = truncate(row.get("alarmId"), 40)
            local = {"localDeviceId": device.id if device else None, "localAlarmId": None, "handlingStatus": None,
                     "hidden": False}
            if device is None:
                self.stats.add("skippedUnknownDevice")
            elif type_id not in self.types:
                self.stats.add("skippedUnknownAlarmType")
            elif alarm_time is None or not vendor_id:
                self.stats.add("skippedInvalid")
            else:
                lat, lon = valid_lat_lon(row.get("lat"), row.get("lon"))
                media = [(kind, str(url)[:1000]) for kind, url in
                         (("VIDEO", row.get("aviPath")), ("IMAGE", row.get("imagePath"))) if url]
                if row.get("filePath") and row.get("mediaType") in (2, 4):
                    media.append(("VIDEO" if row.get("mediaType") == 2 else "IMAGE", str(row["filePath"])[:1000]))
                local.update(self._store(device, type_id, vendor_id, alarm_time, {
                    "speed_kmh": to_float(row.get("speed")), "lat": lat, "lon": lon,
                    "duration_seconds": parse_duration_seconds(row.get("duration")),
                    "raw_payload": to_json(row)}, list(dict.fromkeys(media))))
            result.append({**row, **local})
        return result

    # --- vendor 5.4 / 5.8 ----------------------------------------------------------------------------------
    def ingest_routine(self, rows: list[dict], devices: dict[str, DeviceRef],
                       requested_type_ids: list[int]) -> list[dict]:
        labels = {}
        for type_id in requested_type_ids:
            row = self.types.get(type_id)
            if row is not None:
                labels.setdefault(row.label.strip().lower(), type_id)
        single = requested_type_ids[0] if len(requested_type_ids) == 1 else None
        result = []
        for row in rows:
            device = devices.get(str(row.get("deviceId") or ""))
            label = str(row.get("alarmType") or "").strip()
            type_id = labels.get(label.lower(), single)
            alarm_time = parse_vendor_time(row.get("startTime"))
            local = {"localDeviceId": device.id if device else None, "localAlarmId": None, "handlingStatus": None,
                     "hidden": False, "startTimeUtc": alarm_time.isoformat() if alarm_time else None}
            if device is None:
                self.stats.add("skippedUnknownDevice")
            elif type_id is None or type_id not in self.types:
                self.stats.add("skippedUnknownAlarmType")
            elif alarm_time is None:
                self.stats.add("skippedInvalid")
            else:
                lon_lat = str(row.get("lonAndLat") or "").split(",")
                lat, lon = valid_lat_lon(lon_lat[1] if len(lon_lat) == 2 else None, lon_lat[0])
                vendor_id = routine_alarm_id(str(row.get("deviceId")), label, str(row.get("startTime")))
                local.update(self._store(device, type_id, vendor_id, alarm_time, {
                    "speed_kmh": to_float(row.get("speed")), "lat": lat, "lon": lon,
                    "ended_at": parse_vendor_time(row.get("endTime")),
                    "duration_seconds": parse_duration_seconds(row.get("timeOfDuration")),
                    "raw_payload": to_json(row)}, []))
            result.append({**row, **local})
        return result
