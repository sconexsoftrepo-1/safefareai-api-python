from fastapi import APIRouter, Depends, Path

from app.api.deps import Session, Settings, get_db, get_settings, get_vendor_api
from app.core.responses import ENVELOPE, ERROR_RESPONSES
from app.core.security import require_permissions
from app.schemas.commands import (
    AinCalibrationIn,
    FuelCalibrationIn,
    LoadCalibrationIn,
    PassThroughIn,
    PassThroughQueryIn,
    TemperatureCalibrationIn,
)
from app.services import command_service

router = APIRouter(prefix="/commands", tags=["Command center"], responses=ERROR_RESPONSES)
sender = require_permissions("command.send")
_NOTE = (" Accepts 1-1000 deviceIds (batch command); recorded in dbo.commands/command_targets. "
         "'SENT' means accepted by the vendor, not executed by the device. Never auto-retried.")


@router.post("/fuel-calibration", **ENVELOPE, summary="Fuel calibration",
             description="Vendor 8.20 /command/fuelSet." + _NOTE)
def fuel(body: FuelCalibrationIn, user=Depends(sender), db: Session = Depends(get_db), api=Depends(get_vendor_api),
         settings: Settings = Depends(get_settings)):
    return command_service.fuel(db, api, user, settings, body)


@router.post("/temperature-calibration", **ENVELOPE, summary="High/low temperature thresholds",
             description="Vendor 8.21 /command/temperatureSet." + _NOTE)
def temperature(body: TemperatureCalibrationIn, user=Depends(sender), db: Session = Depends(get_db),
                api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return command_service.temperature(db, api, user, settings, body)


@router.post("/load-calibration", **ENVELOPE, summary="Load calibration",
             description="Vendor 8.22 /command/loadSet." + _NOTE)
def load(body: LoadCalibrationIn, user=Depends(sender), db: Session = Depends(get_db), api=Depends(get_vendor_api),
         settings: Settings = Depends(get_settings)):
    return command_service.load(db, api, user, settings, body)


@router.post("/ain-calibration", **ENVELOPE, summary="AIN calibration",
             description="Vendor 8.23 /command/ainSet." + _NOTE)
def ain(body: AinCalibrationIn, user=Depends(sender), db: Session = Depends(get_db), api=Depends(get_vendor_api),
        settings: Settings = Depends(get_settings)):
    return command_service.ain(db, api, user, settings, body)


@router.post("/pass-through", **ENVELOPE, summary="Send pass-through (raw hex) data",
             description="Vendor 8.29 /command/passThroughSet." + _NOTE)
def pass_through(body: PassThroughIn, user=Depends(sender), db: Session = Depends(get_db),
                 api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return command_service.pass_through(db, api, user, settings, body)


@router.post("/pass-through/data", **ENVELOPE, summary="Read pass-through data uploaded by devices",
             description="Vendor 8.30 /command/queryPassThroughData. Persists dbo.device_passthrough_messages.")
def pass_through_data(body: PassThroughQueryIn, user=Depends(sender), db: Session = Depends(get_db),
                      api=Depends(get_vendor_api), settings: Settings = Depends(get_settings)):
    return command_service.pass_through_data(db, api, user, settings, body)


@router.get("/{command_id}", **ENVELOPE, summary="Batch command status (local audit)")
def get_command(command_id: int = Path(gt=0), user=Depends(sender), db: Session = Depends(get_db)):
    return command_service.get_command(db, user, command_id)
