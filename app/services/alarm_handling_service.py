"""Local alarm handling (no vendor API exists for these features).

Alarm handling        : dbo.alarms.handling_status / handling_outcome + dbo.alarm_actions history.
High-priority closure : alarms matched by a HIGH_PRIORITY rule need 5 sequential HIGH_PRIORITY_STEP actions
                        (alarm_actions.step_no 1..5) before they can be closed. The PDF/Excel do not define the
                        content of each step, so only the order is enforced.
Linkage rules         : dbo.alarm_rules + alarm_rule_types (HIDE / DISPLAY_ONLY / PROCESS / HIGH_PRIORITY).
Pop-ups and sound     : user_preferences.alarm_popup_close_sec / alarm_popup_max + rule popup/sound flags.
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.responses import ok
from app.core.security import CurrentUser
from app.core.timeutil import to_utc_naive, utcnow
from app.db.session import transaction
from app.repositories import alarms as alarm_repo
from app.repositories import devices as device_repo
from app.repositories import preferences as pref_repo
from app.repositories import rules as rule_repo
from app.repositories.common import from_json
from app.schemas.alarms import AlarmActionIn, AlarmRuleCreate, AlarmRuleUpdate, LocalAlarmQuery, PopupSettingsIn

CLOSED = ("RESOLVED", "DISMISSED")
OUTCOME_ACTIONS = {"DISPATCH_EMERGENCY", "DISPATCH_TERMINAL", "VOICE_COMMAND", "TEST", "FALSE_POSITIVE",
                   "CONFIRMED_ALARM"}
DISMISS_OUTCOMES = {"FALSE_POSITIVE", "TEST"}
HIGH_PRIORITY_STEPS = 5


def _alarm_view(row) -> dict:
    return {"alarmId": row.id, "alarmTime": row.alarm_time, "deviceId": row.device_id,
            "alarmTypeId": row.alarm_type_id, "alarmType": getattr(row, "alarm_type_label", None),
            "category": getattr(row, "alarm_category", None), "vendorAlarmId": row.vendor_alarm_id,
            "severity": row.severity, "speedKmh": row.speed_kmh, "lat": row.lat, "lon": row.lon,
            "durationSeconds": row.duration_seconds, "mediaStatus": row.media_status,
            "handlingStatus": row.handling_status, "handlingOutcome": row.handling_outcome,
            "handledBy": row.handled_by, "handledAt": row.handled_at, "ruleId": row.rule_id}


def list_alarms(db: Session, user: CurrentUser, q: LocalAlarmQuery) -> dict:
    rows, total = alarm_repo.list_alarms(
        db, user.tenant_id, start=to_utc_naive(q.start_time) if q.start_time else None,
        end=to_utc_naive(q.end_time) if q.end_time else None, statuses=q.statuses, device_ids=q.device_ids,
        type_ids=q.alarm_type_ids, include_hidden=q.include_hidden, page=q.page, page_size=q.page_size)
    return ok([_alarm_view(r) for r in rows], meta={"total": total, "page": q.page, "pageSize": q.page_size})


def _rule(db: Session, tenant_id: int, rule_id: int | None):
    if rule_id is None:
        return None
    try:
        return rule_repo.get_rule(db, tenant_id, rule_id)
    except NotFoundError:
        return None


def alarm_detail(db: Session, user: CurrentUser, alarm_id: int) -> dict:
    alarm = alarm_repo.get_alarm(db, user.tenant_id, alarm_id)
    if alarm is None:
        raise NotFoundError("Alarm not found", code="ALARM_NOT_FOUND")
    rule = _rule(db, user.tenant_id, alarm.rule_id)
    steps = alarm_repo.completed_steps(db, alarm.id, alarm.alarm_time)
    actions = alarm_repo.alarm_actions(db, alarm.id, alarm.alarm_time)
    media = alarm_repo.alarm_media(db, alarm.id, alarm.alarm_time)
    return ok({**_alarm_view(alarm), "raw": from_json(alarm.raw_payload),
               "rule": {"ruleId": rule.id, "name": rule.name, "handlingMode": rule.handling_mode} if rule else None,
               "highPriority": {"required": bool(rule and rule.handling_mode == "HIGH_PRIORITY"),
                                "completedSteps": steps, "totalSteps": HIGH_PRIORITY_STEPS},
               "media": [{"id": m.id, "type": m.media_type, "channel": m.channel, "url": m.vendor_url,
                          "status": m.status} for m in media],
               "actions": [{"id": a.id, "action": a.action_type, "stepNo": a.step_no, "actorUserId": a.actor_user_id,
                            "assigneeUserId": a.assignee_user_id, "note": a.note, "automatic": a.is_automatic,
                            "createdAt": a.created_at} for a in actions]})


def act(db: Session, user: CurrentUser, alarm_id: int, req: AlarmActionIn) -> dict:
    with transaction(db):
        alarm = alarm_repo.get_alarm(db, user.tenant_id, alarm_id, for_update=True)
        if alarm is None:
            raise NotFoundError("Alarm not found", code="ALARM_NOT_FOUND")
        rule = _rule(db, user.tenant_id, alarm.rule_id)
        mode = rule.handling_mode if rule else None
        closed = alarm.handling_status in CLOSED
        action = req.action
        now = utcnow()
        updates: dict = {}

        if action != "COMMENT" and mode in ("HIDE", "DISPLAY_ONLY"):
            raise ConflictError(f"Alarms under a {mode} rule cannot be processed", code="ALARM_NOT_PROCESSABLE")
        if action == "REOPEN":
            if not closed:
                raise ConflictError("Only closed alarms can be reopened", code="ALARM_NOT_CLOSED")
            updates = {"handling_status": "NEW", "handling_outcome": None, "handled_by": None, "handled_at": None}
        elif action != "COMMENT" and closed:
            raise ConflictError("The alarm is already closed", code="ALARM_CLOSED")
        elif action == "ACKNOWLEDGE":
            if alarm.handling_status == "NEW":
                updates = {"handling_status": "ACKNOWLEDGED", "handled_by": user.user_id, "handled_at": now}
        elif action == "ASSIGN":
            if not alarm_repo.active_user_exists(db, user.tenant_id, req.assignee_user_id):
                raise NotFoundError("Assignee not found", code="USER_NOT_FOUND")
            updates = {"handling_status": "IN_PROGRESS"}
        elif action == "HIGH_PRIORITY_STEP":
            if mode != "HIGH_PRIORITY":
                raise ConflictError("This alarm is not a high-priority alarm", code="NOT_HIGH_PRIORITY")
            done = alarm_repo.completed_steps(db, alarm.id, alarm.alarm_time)
            expected = len(done) + 1
            if req.step_no != expected:
                raise ConflictError(f"Step {expected} must be completed next", code="STEP_OUT_OF_ORDER",
                                    details={"expectedStep": expected})
            updates = {"handling_status": "IN_PROGRESS"}
            if req.step_no == HIGH_PRIORITY_STEPS:
                updates = {"handling_status": "DISMISSED" if req.outcome in DISMISS_OUTCOMES else "RESOLVED",
                           "handling_outcome": req.outcome, "handled_by": user.user_id, "handled_at": now}
        elif action in OUTCOME_ACTIONS or action == "CLOSE":
            if mode == "HIGH_PRIORITY":
                done = alarm_repo.completed_steps(db, alarm.id, alarm.alarm_time)
                if len(done) < HIGH_PRIORITY_STEPS:
                    raise ConflictError("High-priority alarms require all 5 confirmation steps before closing",
                                        code="HIGH_PRIORITY_STEPS_PENDING", details={"completedSteps": done})
            outcome = action if action in OUTCOME_ACTIONS else alarm.handling_outcome
            updates = {"handling_status": "DISMISSED" if outcome in DISMISS_OUTCOMES else "RESOLVED",
                       "handling_outcome": outcome, "handled_by": user.user_id, "handled_at": now}

        if updates:
            alarm_repo.update_alarm(db, alarm.id, alarm.alarm_time, updates)
        alarm_repo.insert_action(db, {
            "tenant_id": user.tenant_id, "alarm_id": alarm.id, "alarm_time": alarm.alarm_time, "action_type": action,
            "step_no": req.step_no, "actor_user_id": user.user_id, "assignee_user_id": req.assignee_user_id,
            "note": req.note, "is_automatic": False, "created_at": now})
    return alarm_detail(db, user, alarm_id)


# --- pop-ups & sound -----------------------------------------------------------------------------------------
def popups(db: Session, user: CurrentUser, since_minutes: int) -> dict:
    prefs = pref_repo.alarm_popup_prefs(db, user.tenant_id, user.user_id)
    rows = alarm_repo.popup_candidates(db, user.tenant_id, utcnow() - timedelta(minutes=since_minutes),
                                       prefs["popupMax"])
    return ok({"closeAfterSec": prefs["popupCloseSec"], "maxPopups": prefs["popupMax"],
               "bellCount": alarm_repo.open_alarm_count(db, user.tenant_id),
               "popups": [{"alarmId": r.id, "alarmTime": r.alarm_time, "deviceId": r.device_id,
                           "alarmTypeId": r.alarm_type_id, "alarmType": r.alarm_type_label, "severity": r.severity,
                           "lat": r.lat, "lon": r.lon, "highPriority": r.handling_mode == "HIGH_PRIORITY",
                           "sound": True if r.sound_enabled is None else bool(r.sound_enabled)} for r in rows]})


def get_popup_settings(db: Session, user: CurrentUser) -> dict:
    return ok(pref_repo.alarm_popup_prefs(db, user.tenant_id, user.user_id))


def save_popup_settings(db: Session, user: CurrentUser, req: PopupSettingsIn) -> dict:
    with transaction(db):
        pref_repo.save_alarm_popup_prefs(db, user.tenant_id, user.user_id, req.popup_close_sec, req.popup_max)
    return get_popup_settings(db, user)


# --- linkage rules -------------------------------------------------------------------------------------------
def _rule_view(row, type_ids: list[int]) -> dict:
    return {"ruleId": row.id, "name": row.name, "handlingMode": row.handling_mode, "processMode": row.process_mode,
            "autoOutcome": row.auto_outcome, "popupEnabled": row.popup_enabled, "notifyEnabled": row.notify_enabled,
            "soundEnabled": row.sound_enabled, "groupId": row.group_id, "priority": row.priority,
            "enabled": row.enabled, "alarmTypeIds": type_ids, "createdAt": row.created_at, "updatedAt": row.updated_at}


def _validate_rule(db: Session, tenant_id: int, values: dict, type_ids: list[int] | None) -> None:
    mode, process, auto = values["handling_mode"], values.get("process_mode"), values.get("auto_outcome")
    if mode == "PROCESS" and process is None:
        raise BadRequestError("processMode is required when handlingMode is PROCESS", code="INVALID_RULE")
    if mode != "PROCESS" and process is not None:
        raise BadRequestError("processMode is only allowed when handlingMode is PROCESS", code="INVALID_RULE")
    if auto is not None and process != "AUTO":
        raise BadRequestError("autoOutcome requires processMode AUTO", code="INVALID_RULE")
    if values.get("group_id") is not None:
        device_repo.get_group(db, tenant_id, values["group_id"])
    if type_ids:
        known = set(alarm_repo.alarm_type_map(db))
        unknown = [i for i in type_ids if i not in known]
        if unknown:
            raise BadRequestError("Unknown alarm type ids", code="UNKNOWN_ALARM_TYPE", details={"ids": unknown})


def list_rules(db: Session, user: CurrentUser) -> dict:
    rows = rule_repo.list_rules(db, user.tenant_id)
    types = rule_repo.rule_type_ids(db, [r.id for r in rows])
    return ok([_rule_view(r, types.get(r.id, [])) for r in rows])


def get_rule(db: Session, user: CurrentUser, rule_id: int) -> dict:
    row = rule_repo.get_rule(db, user.tenant_id, rule_id)
    return ok(_rule_view(row, rule_repo.rule_type_ids(db, [row.id])[row.id]))


def create_rule(db: Session, user: CurrentUser, req: AlarmRuleCreate) -> dict:
    values = {"tenant_id": user.tenant_id, "name": req.name.strip(), "handling_mode": req.handling_mode,
              "process_mode": req.process_mode, "auto_outcome": req.auto_outcome,
              "popup_enabled": True if req.popup_enabled is None else req.popup_enabled,
              "notify_enabled": True if req.notify_enabled is None else req.notify_enabled,
              "sound_enabled": True if req.sound_enabled is None else req.sound_enabled,
              "group_id": req.group_id, "priority": 100 if req.priority is None else req.priority,
              "enabled": True if req.enabled is None else req.enabled, "created_at": utcnow(), "updated_at": utcnow()}
    type_ids = list(dict.fromkeys(req.alarm_type_ids))
    _validate_rule(db, user.tenant_id, values, type_ids)
    if rule_repo.name_taken(db, user.tenant_id, values["name"]):
        raise ConflictError("A rule with this name already exists", code="ALARM_RULE_NAME_EXISTS")
    with transaction(db):
        rule_id = rule_repo.create_rule(db, values, type_ids)
    return get_rule(db, user, rule_id)


def update_rule(db: Session, user: CurrentUser, rule_id: int, req: AlarmRuleUpdate) -> dict:
    current = rule_repo.get_rule(db, user.tenant_id, rule_id)
    changes = req.model_dump(exclude_unset=True)
    type_ids = changes.pop("alarm_type_ids", None)
    merged = {c: getattr(current, c) for c in ("name", "handling_mode", "process_mode", "auto_outcome",
                                                "popup_enabled", "notify_enabled", "sound_enabled", "group_id",
                                                "priority", "enabled")}
    merged.update(changes)
    if "handling_mode" in changes and changes["handling_mode"] != "PROCESS":
        merged["process_mode"] = changes.get("process_mode")
        merged["auto_outcome"] = changes.get("auto_outcome")
    if merged.get("process_mode") != "AUTO" and "auto_outcome" not in changes:
        merged["auto_outcome"] = None
    if merged["name"] is not None:
        merged["name"] = merged["name"].strip()
    _validate_rule(db, user.tenant_id, merged, list(dict.fromkeys(type_ids)) if type_ids else None)
    if rule_repo.name_taken(db, user.tenant_id, merged["name"], exclude_id=rule_id):
        raise ConflictError("A rule with this name already exists", code="ALARM_RULE_NAME_EXISTS")
    with transaction(db):
        rule_repo.update_rule(db, user.tenant_id, rule_id, {**merged, "updated_at": utcnow()},
                              list(dict.fromkeys(type_ids)) if type_ids else None)
    return get_rule(db, user, rule_id)


def delete_rule(db: Session, user: CurrentUser, rule_id: int) -> dict:
    rule_repo.get_rule(db, user.tenant_id, rule_id)
    with transaction(db):
        rule_repo.delete_rule(db, user.tenant_id, rule_id)
    return ok({"ruleId": rule_id}, message="Alarm rule deleted")
