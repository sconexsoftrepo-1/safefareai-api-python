"""Device commands (8.3 wake, 8.20-8.23 calibration, 8.29 pass-through) with a dbo.commands audit trail.

Workflow per request:
 1. every device id is checked against the caller's tenant (nothing is sent otherwise);
 2. a dbo.commands row is committed (status PENDING) before anything is sent;
 3. terminals are sent in chunks (comma-separated terminalNo, up to 1000 targets per batch);
 4. each vendor successList entry -> command_targets SENT (+ vendor commandNo), failList -> FAILED;
 5. the command status becomes SENT / PARTIAL / FAILED.
"SENT" means the vendor accepted the command for delivery, not that the device executed it. Execution results
are read with vendor 8.2 /command/getResult (Command result lookup, a Java-assigned feature).
Commands are never retried automatically.
"""
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import VendorError, VendorInvalidResponseError
from app.core.responses import no_data, ok
from app.core.security import CurrentUser
from app.core.timeutil import parse_vendor_time, to_int, utcnow, validate_range
from app.db.session import transaction
from app.repositories import commands as command_repo
from app.repositories import devices as device_repo
from app.repositories.common import from_json, to_json, truncate
from app.schemas.commands import (
    AinCalibrationIn,
    FuelCalibrationIn,
    LoadCalibrationIn,
    PassThroughIn,
    PassThroughQueryIn,
    TemperatureCalibrationIn,
)
from app.services.common import chunks, expect_list, expect_object
from app.vendor.api import GpsTrackTechApi
from app.vendor.client import VendorResponse

logger = logging.getLogger(__name__)


def _vendor_lists(response: VendorResponse) -> tuple[list[dict], list[dict]]:
    data = expect_object(response)
    if data is None:
        raise VendorInvalidResponseError("The vendor did not return command results")
    success, fail = data.get("successList") or [], data.get("failList") or []
    if not isinstance(success, list) or not isinstance(fail, list) or \
            any(not isinstance(i, dict) for i in success + fail):
        raise VendorInvalidResponseError("The vendor returned command results in an unexpected format")
    return success, fail


def dispatch(db: Session, user: CurrentUser, settings: Settings, command_type: str, vendor_endpoint: str,
             device_ids: list[int], audit_payload: dict, send: Callable[[list[str]], VendorResponse]) -> dict:
    devices = device_repo.get_devices(db, user.tenant_id, device_ids)
    with transaction(db):
        command_id = command_repo.create_command(db, user.tenant_id, user.user_id, command_type, vendor_endpoint,
                                                 to_json(audit_payload), len(devices))

    results: dict[str, dict] = {}
    errors: list[VendorError] = []
    batches = list(chunks(devices, settings.gpstracktech_command_chunk_size))
    for chunk in batches:
        terminals = [d.terminal_no for d in chunk]
        try:
            success, fail = _vendor_lists(send(terminals))
        except VendorError as exc:
            errors.append(exc)
            for terminal in terminals:
                results[terminal] = {"status": "FAILED", "reason": exc.code}
            continue
        for item in success:
            results[str(item.get("terminalNo"))] = {"status": "SENT",
                                                    "commandNo": truncate(item.get("commandNo"), 64)}
        for item in fail:
            results[str(item.get("terminalNo"))] = {"status": "FAILED",
                                                    "reason": truncate(item.get("failMsg") or "unknown", 200)}
        for terminal in terminals:
            results.setdefault(terminal, {"status": "FAILED", "reason": "NOT_IN_VENDOR_RESPONSE"})

    now = utcnow()
    target_rows, targets_view = [], []
    for device in devices:
        result = results[device.terminal_no]
        target_rows.append({
            "tenant_id": user.tenant_id, "command_id": command_id, "device_id": device.id,
            "terminal_no": device.terminal_no, "vendor_command_no": result.get("commandNo"),
            "status": result["status"], "fail_reason": result.get("reason"),
            "sent_at": now if result["status"] == "SENT" else None,
            "finished_at": now if result["status"] == "FAILED" else None})
        targets_view.append({"deviceId": device.id, "terminalNo": device.terminal_no, **result})
    sent = sum(1 for r in target_rows if r["status"] == "SENT")
    status = "SENT" if sent == len(target_rows) else ("FAILED" if sent == 0 else "PARTIAL")
    with transaction(db):
        command_repo.add_targets(db, target_rows)
        command_repo.finish_command(db, command_id, status)

    if len(errors) == len(batches):
        # The vendor rejected every batch: surface the vendor error (the audit row is already saved as FAILED).
        logger.warning("command %s (%s) failed at the vendor for all targets", command_id, command_type)
        errors[0].details = {**(errors[0].details or {}), "commandId": command_id}
        raise errors[0]
    return ok({"commandId": command_id, "commandType": command_type, "status": status, "sent": sent,
               "failed": len(target_rows) - sent, "targets": targets_view},
              message="Command sent" if status == "SENT" else
              ("Command partially sent" if status == "PARTIAL" else "Command was not accepted for any device"))


def fuel(db, api: GpsTrackTechApi, user, settings, req: FuelCalibrationIn) -> dict:
    scales = [{"oilNo": s.oil_no, "oilNumber": s.oil_number, "scale": s.scale, "unit": s.unit} for s in req.scales]
    return dispatch(db, user, settings, "FUEL_CALIBRATION", "/command/fuelSet", req.device_ids, {"scales": scales},
                    lambda terminals: api.fuel_set(terminals, scales))


def temperature(db, api: GpsTrackTechApi, user, settings, req: TemperatureCalibrationIn) -> dict:
    params = [{"high": p.high, "low": p.low, "number": p.number} for p in req.temperature_param]
    return dispatch(db, user, settings, "TEMPERATURE_CALIBRATION", "/command/temperatureSet", req.device_ids,
                    {"name": req.name, "temperatureParam": params},
                    lambda terminals: api.temperature_set(terminals, req.name, params))


def load(db, api: GpsTrackTechApi, user, settings, req: LoadCalibrationIn) -> dict:
    info = [{"channel": i.channel, "loadAD": i.load_ad, "loadQuality": i.load_quality, "noLoadAD": i.no_load_ad,
             "noLoadQuality": i.no_load_quality} for i in req.load_info_list]
    return dispatch(db, user, settings, "LOAD_CALIBRATION", "/command/loadSet", req.device_ids,
                    {"loadInfoList": info}, lambda terminals: api.load_set(terminals, info))


def ain(db, api: GpsTrackTechApi, user, settings, req: AinCalibrationIn) -> dict:
    sensor_req = {"data": [{"adValue": d.ad_value, "channel": d.channel, "fuelValue": d.fuel_value,
                            "fullAdValue": d.full_ad_value, "fullFuelValue": d.full_fuel_value, "unit": d.unit}
                           for d in req.sensor_req.data],
                  "name": req.sensor_req.name, "sensor": req.sensor_req.sensor}
    return dispatch(db, user, settings, "AIN_CALIBRATION", "/command/ainSet", req.device_ids,
                    {"sensorReq": sensor_req}, lambda terminals: api.ain_set(terminals, sensor_req))


def pass_through(db, api: GpsTrackTechApi, user, settings, req: PassThroughIn) -> dict:
    return dispatch(db, user, settings, "PASS_THROUGH", "/command/passThroughSet", req.device_ids,
                    {"passThroughType": req.pass_through_type, "content": req.content},
                    lambda terminals: api.pass_through_set(terminals, req.pass_through_type, req.content))


def wake(db, api: GpsTrackTechApi, user, settings, device_ids: list[int]) -> dict:
    return dispatch(db, user, settings, "WAKEN_DEVICE", "/command/wakenDevice", device_ids, {},
                    lambda terminals: api.waken_device(terminals))


def pass_through_data(db: Session, api: GpsTrackTechApi, user: CurrentUser, settings: Settings,
                      req: PassThroughQueryIn) -> dict:
    devices = device_repo.get_devices(db, user.tenant_id, req.device_ids)
    start, end = validate_range(req.start_time, req.end_time, settings.query_max_range_days)
    rows = expect_list(api.query_pass_through([d.terminal_no for d in devices], req.pass_through_type, start, end))
    if not rows:
        return no_data()
    by_vehicle = {d.vendor_vehicle_id: d for d in devices if d.vendor_vehicle_id is not None}
    stats: dict[str, int] = {}
    enriched = []
    with transaction(db):
        for row in rows:
            device = by_vehicle.get(to_int(row.get("vehicleId"))) or (devices[0] if len(devices) == 1 else None)
            message_id = truncate(row.get("id"), 40)
            if device is None or not message_id:
                stats["skipped"] = stats.get("skipped", 0) + 1
                enriched.append({**row, "localDeviceId": None})
                continue
            outcome = command_repo.upsert_passthrough(db, user.tenant_id, device.id, message_id, {
                "message_type": to_int(row.get("messageType")), "content": row.get("content"),
                "vendor_created_at": parse_vendor_time(row.get("createTime")),
                "vendor_updated_at": parse_vendor_time(row.get("updateTime"))})
            stats[outcome] = stats.get(outcome, 0) + 1
            enriched.append({**row, "localDeviceId": device.id})
    return ok(enriched, meta={"total": len(rows), "persisted": stats})


def get_command(db: Session, user: CurrentUser, command_id: int) -> dict:
    command, targets = command_repo.get_command(db, user.tenant_id, command_id)
    return ok({
        "commandId": command.id, "commandType": command.command_type, "vendorEndpoint": command.vendor_endpoint,
        "status": command.status, "targetCount": command.target_count, "payload": from_json(command.payload, {}),
        "createdAt": command.created_at, "completedAt": command.completed_at, "requestedBy": command.requested_by,
        "targets": [{"deviceId": tg.device_id, "terminalNo": tg.terminal_no, "status": tg.status,
                     "commandNo": tg.vendor_command_no, "failReason": tg.fail_reason, "sentAt": tg.sent_at,
                     "finishedAt": tg.finished_at, "vendorResult": tg.vendor_result} for tg in targets]})
