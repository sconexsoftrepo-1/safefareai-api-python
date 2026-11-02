from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import Session, Settings, get_db, get_settings, get_vendor_api
from app.core.responses import ENVELOPE, ERROR_RESPONSES
from app.core.security import require_permissions
from app.schemas.common import ScopedRangeQuery
from app.schemas.reports import AlarmReportQuery, DailyMileageQuery, ExportIn, MultimediaQuery
from app.services import export_service, report_service

router = APIRouter(prefix="/reports", tags=["Reports"], responses=ERROR_RESPONSES)
reader = require_permissions("report.read")


@router.post("/mileage", **ENVELOPE, summary="Mileage report (range totals per device)",
             description="Vendor 5.6 mileageReport/list. Persists dbo.device_mileage_reports.")
def mileage(body: ScopedRangeQuery, user=Depends(reader), db: Session = Depends(get_db), api=Depends(get_vendor_api),
            settings: Settings = Depends(get_settings)):
    return report_service.mileage(db, api, user, settings, body)


@router.post("/mileage/daily", **ENVELOPE, summary="Mileage per device per day",
             description="Vendor 5.6 called once per UTC day in the range. Persists dbo.device_mileage_reports.")
def mileage_daily(body: DailyMileageQuery, user=Depends(reader), db: Session = Depends(get_db),
                  api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return report_service.mileage_daily(db, api, user, settings, body)


@router.post("/driving", **ENVELOPE, summary="Driving time report",
             description="Vendor 5.5 drivingReport/list. Persists dbo.device_activity_periods (DRIVING).")
def driving(body: ScopedRangeQuery, user=Depends(reader), db: Session = Depends(get_db), api=Depends(get_vendor_api),
            settings: Settings = Depends(get_settings)):
    return report_service.driving(db, api, user, settings, body)


@router.post("/parking", **ENVELOPE, summary="Parking report",
             description="Vendor 5.2 parkingReport/list. Persists dbo.device_activity_periods (PARKING).")
def parking(body: ScopedRangeQuery, user=Depends(reader), db: Session = Depends(get_db), api=Depends(get_vendor_api),
            settings: Settings = Depends(get_settings)):
    return report_service.parking(db, api, user, settings, body)


@router.post("/multimedia", **ENVELOPE, summary="Multimedia report (photos and videos)",
             description="Vendor 5.3 multi/list. Persists dbo.device_media.")
def multimedia(body: MultimediaQuery, user=Depends(reader), db: Session = Depends(get_db),
               api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return report_service.multimedia(db, api, user, settings, body)


@router.post("/alarms", **ENVELOPE, summary="Alarm report",
             description="Vendor 5.8 getAlarmInfo. Persists dbo.alarms.")
def alarms(body: AlarmReportQuery, user=Depends(require_permissions("report.read", "alarm.read")),
           db: Session = Depends(get_db), api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return report_service.alarm_report(db, api, user, settings, body)


@router.post("/export", summary="Export a report to XLSX, PDF or CSV",
             description="Fetches all pages of the chosen vendor report, records dbo.report_jobs and streams the "
                         "file. Returns the JSON 'No Data from Vendor' envelope when there are no rows.",
             responses={**ERROR_RESPONSES, 200: {"description": "The report file, or the No Data envelope",
                                                 "content": {"application/octet-stream": {}}}})
def export(body: ExportIn, user=Depends(reader), db: Session = Depends(get_db), api=Depends(get_vendor_api),
           settings: Settings = Depends(get_settings)):
    result = export_service.export(db, api, user, settings, body)
    if isinstance(result, dict):
        return result
    return Response(content=result.content, media_type=result.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{result.filename}"',
                             "X-Report-Job-Id": str(result.job_id), "X-Report-Rows": str(result.rows)})
