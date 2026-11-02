from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import Session, Settings, get_db, get_settings, get_vendor_api
from app.core.exceptions import BadRequestError
from app.core.responses import ENVELOPE, ERROR_RESPONSES
from app.core.security import require_permissions
from app.schemas.alarms import (
    AiEventQuery,
    AlarmActionIn,
    AlarmRuleCreate,
    AlarmRuleUpdate,
    LocalAlarmQuery,
    PopupSettingsIn,
    RoutineAlarmQuery,
)
from app.schemas.reports import MultimediaQuery
from app.services import alarm_handling_service, alarm_service, report_service

router = APIRouter(tags=["AI events & Alarms"], responses=ERROR_RESPONSES)
HandlingStatus = Literal["NEW", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "DISMISSED"]


@router.post("/alarms/ai-events", **ENVELOPE, summary="AI event list (ADAS/DSM/BSD) with clips",
             description="Vendor 5.1 recentlyAdasList. Persists dbo.alarms + dbo.alarm_media and applies linkage "
                         "rules.")
def ai_events(body: AiEventQuery, user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db),
              api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return alarm_service.ai_events(db, api, user, settings, body)


@router.post("/alarms/routine", **ENVELOPE, summary="Routine alarm list (overspeed, general)",
             description="Vendor 5.8 getAlarmInfo (time range) or 5.4 recentlyList (no times: last 24 h). "
                         "Persists dbo.alarms.")
def routine(body: RoutineAlarmQuery, user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db),
            api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return alarm_service.routine_alarms(db, api, user, settings, body)


@router.get("/alarms/types", **ENVELOPE, summary="Alarm type filters",
            description="Vendor 5.7 getAlarmType (0 all, 2 ADAS, 3 general, 4 DSM, 5 BSD). Upserts dbo.alarm_types.")
def alarm_types(category: int = Query(0, description="0 all, 2 ADAS, 3 general, 4 DSM, 5 BSD"),
                user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db),
                api=Depends(get_vendor_api)):
    if category not in (0, 2, 3, 4, 5):
        raise BadRequestError("category must be one of 0, 2, 3, 4, 5", code="INVALID_CATEGORY")
    return alarm_service.list_alarm_types(db, api, category)


@router.post("/alarms/multimedia", **ENVELOPE, summary="Photos and videos list",
             description="Vendor 5.3 multi/list. Persists dbo.device_media.")
def multimedia(body: MultimediaQuery, user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db),
               api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return report_service.multimedia(db, api, user, settings, body)


@router.get("/alarms/popups", **ENVELOPE, summary="Alarm pop-ups, sound and bell count",
            description="Local: NEW alarms not hidden by rules, limited by the user's pop-up preferences.")
def popups(since_minutes: int = Query(1440, alias="sinceMinutes", ge=1, le=10080),
           user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db)):
    return alarm_handling_service.popups(db, user, since_minutes)


@router.get("/alarms", **ENVELOPE, summary="Stored alarms with handling status (local)")
def list_alarms(start_time: datetime | None = Query(None, alias="startTime"),
                end_time: datetime | None = Query(None, alias="endTime"),
                statuses: list[HandlingStatus] | None = Query(None),
                device_ids: list[int] | None = Query(None, alias="deviceIds"),
                alarm_type_ids: list[int] | None = Query(None, alias="alarmTypeIds"),
                include_hidden: bool = Query(False, alias="includeHidden"), page: int = Query(1, ge=1),
                page_size: int = Query(50, alias="pageSize", ge=1, le=1000),
                user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db)):
    q = LocalAlarmQuery(start_time=start_time, end_time=end_time, statuses=statuses, device_ids=device_ids,
                        alarm_type_ids=alarm_type_ids, include_hidden=include_hidden, page=page, page_size=page_size)
    return alarm_handling_service.list_alarms(db, user, q)


@router.get("/alarms/{alarm_id}", **ENVELOPE, summary="Alarm detail with media and handling history")
def alarm_detail(alarm_id: int = Path(gt=0), user=Depends(require_permissions("alarm.read")),
                 db: Session = Depends(get_db)):
    return alarm_handling_service.alarm_detail(db, user, alarm_id)


@router.post("/alarms/{alarm_id}/actions", **ENVELOPE,
             summary="Handle an alarm (dispatch, voice command, test, false positive, confirm, 5-step closure)",
             description="Local only: updates dbo.alarms handling columns and appends dbo.alarm_actions.")
def alarm_action(body: AlarmActionIn, alarm_id: int = Path(gt=0), user=Depends(require_permissions("alarm.handle")),
                 db: Session = Depends(get_db)):
    return alarm_handling_service.act(db, user, alarm_id, body)


@router.get("/alarm-settings/popups", **ENVELOPE, summary="My alarm pop-up settings")
def get_popup_settings(user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db)):
    return alarm_handling_service.get_popup_settings(db, user)


@router.put("/alarm-settings/popups", **ENVELOPE, summary="Update my alarm pop-up settings")
def put_popup_settings(body: PopupSettingsIn, user=Depends(require_permissions("alarm.read")),
                       db: Session = Depends(get_db)):
    return alarm_handling_service.save_popup_settings(db, user, body)


rules = require_permissions("alarm.rule.manage")


@router.get("/alarm-rules", **ENVELOPE, summary="Alarm linkage rules")
def list_rules(user=Depends(rules), db: Session = Depends(get_db)):
    return alarm_handling_service.list_rules(db, user)


@router.post("/alarm-rules", **ENVELOPE, status_code=201, summary="Create an alarm linkage rule")
def create_rule(body: AlarmRuleCreate, user=Depends(rules), db: Session = Depends(get_db)):
    return alarm_handling_service.create_rule(db, user, body)


@router.get("/alarm-rules/{rule_id}", **ENVELOPE, summary="Alarm linkage rule")
def get_rule(rule_id: int = Path(gt=0), user=Depends(rules), db: Session = Depends(get_db)):
    return alarm_handling_service.get_rule(db, user, rule_id)


@router.put("/alarm-rules/{rule_id}", **ENVELOPE, summary="Update an alarm linkage rule")
def update_rule(body: AlarmRuleUpdate, rule_id: int = Path(gt=0), user=Depends(rules), db: Session = Depends(get_db)):
    return alarm_handling_service.update_rule(db, user, rule_id, body)


@router.delete("/alarm-rules/{rule_id}", **ENVELOPE, summary="Delete an alarm linkage rule")
def delete_rule(rule_id: int = Path(gt=0), user=Depends(rules), db: Session = Depends(get_db)):
    return alarm_handling_service.delete_rule(db, user, rule_id)
