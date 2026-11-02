from fastapi import APIRouter, Depends

from app.api.deps import Session, Settings, get_db, get_settings, get_vendor_api
from app.core.responses import ENVELOPE, ERROR_RESPONSES
from app.core.security import require_permissions
from app.schemas.reports import DashboardQuery, SafetyQuery
from app.services import dashboard_service

router = APIRouter(tags=["Dashboard & Safety"], responses=ERROR_RESPONSES)


@router.post("/dashboard/alarm-trend", **ENVELOPE,
             summary="Alarm and AI event trend (per day)",
             description="Vendor 5.1 recentlyAdasList + 5.8 getAlarmInfo, counted per UTC day. Alarms are persisted.")
def alarm_trend(body: DashboardQuery, user=Depends(require_permissions("alarm.read")), db: Session = Depends(get_db),
                api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return dashboard_service.alarm_trend(db, api, user, settings, body)


@router.post("/dashboard/top-devices", **ENVELOPE,
             summary="Top devices by mileage and driving time",
             description="Vendor 5.6 mileageReport + 5.5 drivingReport aggregated per device.")
def top_devices(body: DashboardQuery, user=Depends(require_permissions("report.read")), db: Session = Depends(get_db),
                api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return dashboard_service.top_rankings(db, api, user, settings, body)


@router.post("/dashboard/ai-events", **ENVELOPE,
             summary="AI event dashboard (ranking by type, hourly trend, top vehicles, map cells)",
             description="Vendor 5.1 recentlyAdasList; hours are UTC; map cells are 0.01 degree buckets.")
def ai_event_dashboard(body: DashboardQuery, user=Depends(require_permissions("alarm.read")),
                       db: Session = Depends(get_db), api=Depends(get_vendor_api),
                       settings: Settings = Depends(get_settings)):
    return dashboard_service.ai_dashboard(db, api, user, settings, body)


@router.post("/safety/ratings", **ENVELOPE, summary="Fleet and vehicle safety rating",
             description="Vendor 5.1 + 5.5 + 5.6. Scoring formula is documented in the response `method`.")
def safety_ratings(body: SafetyQuery, user=Depends(require_permissions("report.read", "alarm.read")),
                   db: Session = Depends(get_db), api=Depends(get_vendor_api),
                   settings: Settings = Depends(get_settings)):
    return dashboard_service.safety_rating(db, api, user, settings, body)
