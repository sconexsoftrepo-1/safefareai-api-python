from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.tenant import get_tenant_id
from app.schemas.tyre_maintenance import (
    RegisterTyreMaintenanceRequest,
    TyreChangeCompleteRequest,
)
from app.services import tyre_maintenance_service as service
from app.repositories import tyre_maintenance_repository as repo


router = APIRouter(
    prefix="/api/v1/tyre-maintenance",
    tags=["Tyre Maintenance"],
)


@router.get("")
def get_all_tyre_maintenance(
    tenant_id: int = Depends(get_tenant_id),
):
    """Get tyre maintenance details for the current tenant."""

    device_keys = repo.get_all_maintenance_keys(
        tenant_id=tenant_id
    )

    results = []

    for record_tenant_id, device_id in device_keys:
        try:
            result = service.get_tyre_maintenance(
                tenant_id=tenant_id,
                device_id=device_id,
            )
            results.append(result)

        except ValueError:
            continue

    return {
        "count": len(results),
        "items": results,
    }


@router.get("/alerts")
def get_alerts(
    vehicle_number: str | None = Query(
        None,
        description="Only return alerts for this vehicle. Omit for all vehicles.",
    ),
    limit: int = Query(50, ge=1, le=500),
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Alerts created by the background scheduler for the current tenant,
    newest first. Optionally filter by vehicle_number.
    """

    items = service.get_alerts(tenant_id, limit, vehicle_number)

    return {
        "count": len(items),
        "items": items,
    }


@router.get("/vehicle/{vehicle_number}")
def get_tyre_maintenance_by_vehicle(
    vehicle_number: str,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get tyre maintenance details using vehicle number."""

    try:
        return service.get_tyre_maintenance_by_vehicle(
            tenant_id=tenant_id,
            vehicle_number=vehicle_number,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post("/vehicle/{vehicle_number}/register")
def register_existing_tyre(
    vehicle_number: str,
    payload: RegisterTyreMaintenanceRequest,
    tenant_id: int = Depends(get_tenant_id),
):
    """Register existing tyres using vehicle number."""

    try:
        return service.register_existing_tyre_by_vehicle(
            tenant_id=tenant_id,
            vehicle_number=vehicle_number,
            installation_date=payload.installation_date,
        )

    except ValueError as exc:
        message = str(exc)

        if "already registered" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )


@router.post("/vehicle/{vehicle_number}/complete")
def complete_tyre_replacement(
    vehicle_number: str,
    payload: TyreChangeCompleteRequest,
    tenant_id: int = Depends(get_tenant_id),
):
    """Complete tyre replacement using vehicle number."""

    try:
        return service.complete_tyre_replacement_by_vehicle(
            tenant_id=tenant_id,
            vehicle_number=vehicle_number,
            replacement_date=payload.replacement_date,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )