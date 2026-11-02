"""Helpers shared by services: device scope resolution, vendor payload validation and pagination."""
from collections.abc import Callable, Iterable
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BadRequestError, NotFoundError, VendorInvalidResponseError
from app.core.security import CurrentUser
from app.repositories import devices as device_repo
from app.repositories.devices import DeviceRef
from app.vendor.client import VendorResponse


def resolve_scope(db: Session, user: CurrentUser, device_ids: list[int] | None, group_id: int | None,
                  settings: Settings, *, enforce_query_limit: bool = True) -> list[DeviceRef]:
    """Devices the caller asked for, always restricted to the caller's tenant."""
    if device_ids:
        devices = device_repo.get_devices(db, user.tenant_id, device_ids)
        if group_id is not None:
            device_repo.get_group(db, user.tenant_id, group_id)
            outside = [d.id for d in devices if d.group_id != group_id]
            if outside:
                raise BadRequestError("Devices do not belong to the requested group", code="DEVICE_GROUP_MISMATCH",
                                      details={"deviceIds": outside})
    elif group_id is not None:
        device_repo.get_group(db, user.tenant_id, group_id)
        devices = device_repo.tenant_devices(db, user.tenant_id, group_id)
    else:
        devices = device_repo.tenant_devices(db, user.tenant_id)
    if not devices:
        raise NotFoundError("No devices found for the requested scope", code="NO_DEVICES")
    if enforce_query_limit and len(devices) > settings.gpstracktech_max_devices_per_query:
        raise BadRequestError(
            f"Too many devices for one query (max {settings.gpstracktech_max_devices_per_query}); "
            "filter by deviceIds or groupId", code="TOO_MANY_DEVICES")
    return devices


def chunks(items: list, size: int) -> Iterable[list]:
    for i in range(0, len(items), max(size, 1)):
        yield items[i:i + size]


def expect_list(response: VendorResponse) -> list[dict]:
    """`data` must be an array of objects (null is treated as an empty result)."""
    data = response.data
    if data is None:
        return []
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise VendorInvalidResponseError("The vendor returned data in an unexpected format")
    return data


def expect_object(response: VendorResponse) -> dict | None:
    data = response.data
    if data is None:
        return None
    if not isinstance(data, dict):
        raise VendorInvalidResponseError("The vendor returned data in an unexpected format")
    return data


def fetch_all_pages(call: Callable[[int, int], VendorResponse], settings: Settings) -> tuple[list[dict], bool]:
    """Walk vendor pages (pageNumber starts at 1). Returns (rows, truncated)."""
    size = settings.gpstracktech_page_size
    rows: list[dict] = []
    page = 1
    while True:
        response = call(page, size)
        items = expect_list(response)
        rows.extend(items)
        if not items or len(items) < size or (response.total is not None and len(rows) >= response.total):
            return rows, False
        if page >= settings.gpstracktech_max_pages:
            return rows, True
        page += 1


def fetch_all_devices(call: Callable[[list[str], int, int], VendorResponse], devices: list[DeviceRef],
                      settings: Settings) -> tuple[list[dict], bool]:
    """fetch_all_pages over device chunks (for aggregate views that may span many devices)."""
    rows: list[dict] = []
    truncated = False
    terminals = [d.terminal_no for d in devices]
    for chunk in chunks(terminals, settings.gpstracktech_max_devices_per_query):
        chunk_rows, chunk_truncated = fetch_all_pages(lambda page, size, c=chunk: call(c, page, size), settings)
        rows.extend(chunk_rows)
        truncated = truncated or chunk_truncated
    return rows, truncated


def device_view(device: DeviceRef | None) -> dict[str, Any] | None:
    if device is None:
        return None
    return {"id": device.id, "name": device.name, "terminalNo": device.terminal_no, "groupId": device.group_id}
