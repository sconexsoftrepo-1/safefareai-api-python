"""Bridge to YOUR existing authentication / RBAC.

>>> WIRE-UP POINT 1 <<<
Replace the body of ``get_current_user`` with a call to your existing auth
dependency (e.g. ``Depends(get_current_active_user)``) and map its result with
``map_user``. The module never reads tenant_id or role from a request body.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from fastapi import Request

from app.services.errors import MaintenanceError


class Role(str, Enum):
    ADMIN = "admin"
    FLEET_OWNER = "fleet_owner"
    DRIVER = "driver"


_ROLE_ALIASES = {
    "admin": Role.ADMIN,
    "super_admin": Role.ADMIN,
    "superadmin": Role.ADMIN,
    "fleet_owner": Role.FLEET_OWNER,
    "fleetowner": Role.FLEET_OWNER,
    "owner": Role.FLEET_OWNER,
    "driver": Role.DRIVER,
}


@dataclass(frozen=True)
class CurrentUser:
    user_id: Any
    role: Role
    tenant_id: Any = None
    # Admin only: tenants the admin may see. None = all tenants.
    authorized_tenant_ids: Optional[tuple] = None


def normalise_role(raw: Any) -> Role:
    key = str(getattr(raw, "value", raw) or "").strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return _ROLE_ALIASES[key]
    except KeyError:
        raise MaintenanceError(403, "Your role is not permitted to use vehicle maintenance")


def _pick(obj: Any, *names: str) -> Any:
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value is not None:
            return value
    return None


def map_user(raw: Any) -> CurrentUser:
    """Map your auth object/dict (or JWT claims) to CurrentUser. Adjust attribute names if needed."""
    if raw is None:
        raise MaintenanceError(401, "Authentication required")
    user_id = _pick(raw, "user_id", "id", "sub")
    role = normalise_role(_pick(raw, "role", "role_name", "user_role"))
    tenant_id = _pick(raw, "tenant_id", "tenantId")
    authorized = _pick(raw, "authorized_tenant_ids", "tenant_ids")
    if user_id is None:
        raise MaintenanceError(401, "Authentication required")
    if role != Role.ADMIN and tenant_id is None:
        raise MaintenanceError(403, "No tenant is associated with this account")
    return CurrentUser(
        user_id=user_id,
        role=role,
        tenant_id=tenant_id,
        authorized_tenant_ids=tuple(authorized) if authorized is not None else None,
    )


def get_current_user(request: Request) -> CurrentUser:
    """Default: read the user your auth middleware placed on ``request.state.user``.

    Replace with your own dependency if your project authenticates differently, e.g.:

        def get_current_user(user = Depends(existing_get_current_user)) -> CurrentUser:
            return map_user(user)
    """
    return map_user(getattr(request.state, "user", None))
