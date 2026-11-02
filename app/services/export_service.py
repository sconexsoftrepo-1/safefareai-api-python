"""Report export to XLSX / PDF / CSV (no vendor API). Data comes from the same documented vendor reports;
every export is recorded in dbo.report_jobs. Files are streamed back and not stored (no S3 bucket is configured
for this service, so report_jobs.s3_* stay NULL)."""
import csv
import io
from dataclasses import dataclass

from fpdf import FPDF
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.responses import no_data
from app.core.security import CurrentUser
from app.core.timeutil import utcnow, validate_range
from app.db.session import transaction
from app.repositories import reports as report_repo
from app.repositories.common import to_json
from app.repositories.devices import by_terminal
from app.schemas.reports import ExportIn
from app.services import alarm_service, report_service
from app.services.common import fetch_all_devices, resolve_scope
from app.vendor.api import GpsTrackTechApi

COLUMNS: dict[str, list[tuple[str, str]]] = {
    "mileage": [("deviceName", "Device"), ("deviceId", "Device ID"), ("group", "Group"), ("plateColor", "Plate colour"),
                ("drvingMileage", "Mileage (km)"), ("startMileage", "Start mileage (km)"),
                ("endMileage", "End mileage (km)"), ("startTime", "Start"), ("endTime", "End")],
    "driving": [("deviceName", "Device"), ("deviceId", "Device ID"), ("deviceType", "Device type"),
                ("group", "Group"), ("startTime", "Start"), ("endTime", "End"), ("drivingTime", "Driving time")],
    "parking": [("deviceName", "Device"), ("deviceId", "Device ID"), ("deviceType", "Device type"),
                ("group", "Group"), ("startTime", "Start"), ("endTime", "End"), ("duration", "Parking time")],
    "multimedia": [("deviceName", "Device"), ("deviceId", "Device ID"), ("group", "Group"), ("channel", "Channel"),
                   ("mediaType", "Media type (0 image, 1 video)"), ("operatorTime", "Time"), ("lon", "Longitude"),
                   ("lat", "Latitude"), ("previewPath", "Preview URL")],
    "alarm": [("deviceName", "Device"), ("deviceId", "Device ID"), ("group", "Group"), ("alarmType", "Alarm type"),
              ("startTime", "Start"), ("endTime", "End"), ("speed", "Speed (km/h)"), ("mileage", "Mileage (km)"),
              ("lonAndLat", "Lon,Lat"), ("timeOfDuration", "Duration")],
    "ai_events": [("deviceName", "Device"), ("deviceId", "Device ID"), ("group", "Group"),
                  ("alarmName", "Event"), ("alarmTime", "Time"), ("speed", "Speed (km/h)"), ("lon", "Longitude"),
                  ("lat", "Latitude"), ("duration", "Duration"), ("aviPath", "Video"), ("imagePath", "Image")],
}
TITLES = {"mileage": "Mileage report", "driving": "Driving time report", "parking": "Parking report",
          "multimedia": "Multimedia report", "alarm": "Alarm report", "ai_events": "AI event report"}
MEDIA_TYPES = {"XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
               "PDF": "application/pdf", "CSV": "text/csv; charset=utf-8"}


@dataclass
class ExportFile:
    content: bytes
    media_type: str
    filename: str
    job_id: int
    rows: int


def _fetch(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings, req: ExportIn, devices,
           start, end) -> list[dict]:
    index = by_terminal(devices)
    kind = req.report_type
    if kind == "ai_events":
        rows, _, _ = alarm_service.collect_ai_events(db, api, user.tenant_id, settings, devices, start, end,
                                                     req.alarm_type_ids)
        return [r for r in rows if not r.get("hidden")]
    if kind == "alarm":
        rows, _, _ = alarm_service.collect_routine_alarms(db, api, user.tenant_id, settings, devices, start, end,
                                                          req.alarm_type_ids)
        return [r for r in rows if not r.get("hidden")]
    calls = {
        "mileage": lambda t, p, s: api.mileage_report(t, start, end, p, s),
        "driving": lambda t, p, s: api.driving_report(t, start, end, p, s),
        "parking": lambda t, p, s: api.parking_report(t, start, end, p, s),
        "multimedia": lambda t, p, s: api.multimedia(t, start, end, req.media_type, p, s),
    }
    rows, _ = fetch_all_devices(calls[kind], devices, settings)
    if rows:
        with transaction(db):
            if kind == "mileage":
                report_service.persist_mileage(db, user.tenant_id, rows, index)
            elif kind == "multimedia":
                report_service.persist_media(db, user.tenant_id, rows, index)
            else:
                report_service.persist_activity(db, user.tenant_id, kind.upper(), rows, index)
    if kind == "parking":
        for row in rows:
            row["duration"] = row.get("parkingTime", row.get("drivingTime"))
    return rows


def _table(kind: str, rows: list[dict]) -> tuple[list[str], list[list[str]]]:
    columns = COLUMNS[kind]
    return [c[1] for c in columns], [["" if r.get(k) is None else str(r.get(k)) for k, _ in columns] for r in rows]


def build_csv(headers, body) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(body)
    return buffer.getvalue().encode("utf-8-sig")


def build_xlsx(title, headers, body) -> bytes:
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title[:31])
    ws.append(headers)
    for row in body:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _latin1(text: str, limit: int) -> str:
    text = text if len(text) <= limit else text[:limit - 3] + "..."
    return text.encode("latin-1", "replace").decode("latin-1")


def build_pdf(title, subtitle, headers, body) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _latin1(title, 120), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 6, _latin1(subtitle, 200), new_x="LMARGIN", new_y="NEXT")
    width = (pdf.w - pdf.l_margin - pdf.r_margin) / max(len(headers), 1)
    limit = max(int(width / 1.6), 6)
    pdf.set_font("Helvetica", "B", 7)
    for h in headers:
        pdf.cell(width, 6, _latin1(h, limit), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for row in body:
        for value in row:
            pdf.cell(width, 5, _latin1(value, limit), border=1)
        pdf.ln()
    return bytes(pdf.output())


def export(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings,
           req: ExportIn) -> ExportFile | dict:
    start, end = validate_range(req.start_time, req.end_time, settings.query_max_range_days)
    devices = resolve_scope(db, user, req.device_ids, req.group_id, settings, enforce_query_limit=False)
    with transaction(db):
        job_id = report_repo.create_report_job(db, user.tenant_id, user.user_id, req.report_type,
                                               to_json(req.model_dump(mode="json", by_alias=True)), req.format)
    try:
        rows = _fetch(db, api, user, settings, req, devices, start, end)
    except AppError as exc:
        with transaction(db):
            report_repo.finish_report_job(db, job_id, "FAILED", error=exc.code)
        raise
    if not rows:
        with transaction(db):
            report_repo.finish_report_job(db, job_id, "DONE", size_bytes=0, error="No Data from Vendor")
        return no_data()
    headers, body = _table(req.report_type, rows)
    title = TITLES[req.report_type]
    subtitle = f"{start:%Y-%m-%d %H:%M:%S} - {end:%Y-%m-%d %H:%M:%S} UTC | {len(rows)} rows"
    content = {"CSV": lambda: build_csv(headers, body), "XLSX": lambda: build_xlsx(title, headers, body),
               "PDF": lambda: build_pdf(title, subtitle, headers, body)}[req.format]()
    with transaction(db):
        report_repo.finish_report_job(db, job_id, "DONE", size_bytes=len(content))
    filename = f"{req.report_type}_report_{utcnow():%Y%m%d%H%M%S}.{req.format.lower()}"
    return ExportFile(content=content, media_type=MEDIA_TYPES[req.format], filename=filename, job_id=job_id,
                      rows=len(rows))
