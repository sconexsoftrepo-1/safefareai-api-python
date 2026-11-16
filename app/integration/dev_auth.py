"""Development-only "pretend login" for the Vehicle Maintenance API.

This is the logic that used to live in safefare_vm/main.py. There is no real login
in that module yet: the "logged-in user" comes from .env.

    DEV_TENANT_ID   tenant_id from your vehicles table   (setting this turns the dev login ON)
    DEV_ROLE        fleet_owner | admin                  (default fleet_owner)
    DEV_USER_ID     the fleet owner's users.id, e.g. 73   (default owner-1)

When DEV_TENANT_ID is empty/unset the module falls back to its normal behaviour
(reads the user from ``request.state.user`` set by your own auth middleware).
Remove DEV_TENANT_ID from .env before deploying.

``install_dev_auth()`` MUST run before ``app.api.vehicle_maintenance`` is imported,
because that module binds ``get_current_user`` at import time.
"""
from __future__ import annotations

import logging
import os

from app.integration import auth_adapter
from app.services.errors import MaintenanceError

log = logging.getLogger(__name__)


def _dev_config() -> dict:
    return {
        "user_id": os.getenv("DEV_USER_ID", "owner-1"),
        "role": os.getenv("DEV_ROLE", "fleet_owner"),
        "tenant_id": os.getenv("DEV_TENANT_ID", "").strip(),
    }


def dev_user():
    dev = _dev_config()
    if not dev["tenant_id"]:
        raise MaintenanceError(401, "Set DEV_TENANT_ID in .env (a tenant_id from your vehicles table) and restart")
    tenant = int(dev["tenant_id"]) if dev["tenant_id"].isdigit() else dev["tenant_id"]
    uid = int(dev["user_id"]) if str(dev["user_id"]).isdigit() else dev["user_id"]   # users.id is numeric
    return auth_adapter.map_user({
        "id": uid,
        "role": dev["role"],
        "tenant_id": tenant,
        "authorized_tenant_ids": [tenant] if dev["role"] == "admin" else None,
    })


def install_dev_auth() -> bool:
    """Swap in the dev login if DEV_TENANT_ID is set. Returns True when it was installed."""
    from dotenv import load_dotenv
    load_dotenv()
    if not _dev_config()["tenant_id"]:
        return False
    auth_adapter.get_current_user = dev_user
    log.warning("Vehicle Maintenance: DEV login is ON (DEV_TENANT_ID=%s, role=%s). Do not deploy like this.",
                _dev_config()["tenant_id"], _dev_config()["role"])
    return True
