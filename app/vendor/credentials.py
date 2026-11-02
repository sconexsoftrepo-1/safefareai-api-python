"""Per-tenant vendor account + secret key resolution.

`dbo.vendor_accounts.secret_ref` is a reference, never the key itself. Supported forms:
  * `env:NAME`  -> key read from environment variable NAME (e.g. env:GPSTRACKTECH_KEY_TENANT1)
  * `NAME`      -> a bare environment-variable name ([A-Z0-9_]+)
If secret_ref cannot be resolved, the convention `GPSTRACKTECH_KEY_TENANT{tenant_id}` is tried.
Other references (e.g. AWS Secrets Manager ARNs) are not supported by this service yet.
"""
import os
import re

from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.core.exceptions import ConfigurationError
from app.db import tables as t
from app.vendor.client import VendorAccount

_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def resolve_secret(secret_ref: str | None, tenant_id: int) -> str | None:
    candidates: list[str] = []
    ref = (secret_ref or "").strip()
    if ref.startswith("env:"):
        candidates.append(ref[4:].strip())
    elif _ENV_NAME.match(ref):
        candidates.append(ref)
    candidates.append(f"GPSTRACKTECH_KEY_TENANT{tenant_id}")
    for name in candidates:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def load_vendor_account(db: Session, tenant_id: int) -> VendorAccount:
    row = db.execute(
        select(t.vendor_accounts.c.id, t.vendor_accounts.c.base_url, t.vendor_accounts.c.api_version,
               t.vendor_accounts.c.secret_ref, t.vendor_accounts.c.vendor_user_id)
        .where(t.vendor_accounts.c.tenant_id == tenant_id, t.vendor_accounts.c.status == "ACTIVE")
        .order_by(t.vendor_accounts.c.id)
    ).first()
    if row is None:
        raise ConfigurationError("No active vendor account is configured for this tenant",
                                 code="VENDOR_ACCOUNT_MISSING")
    key = resolve_secret(row.secret_ref, tenant_id)
    if not key:
        raise ConfigurationError("The vendor API key for this tenant is not configured",
                                 code="VENDOR_KEY_MISSING")
    vendor_user_id = row.vendor_user_id
    if vendor_user_id is None:
        vendor_user_id = db.execute(
            select(t.vendor_users.c.vendor_user_id)
            .where(t.vendor_users.c.tenant_id == tenant_id, t.vendor_users.c.is_key_owner == true(),
                   t.vendor_users.c.deleted_at.is_(None))
            .order_by(t.vendor_users.c.id)
        ).scalar()
    return VendorAccount(account_id=row.id, tenant_id=tenant_id,
                         base_url=row.base_url or "https://y.gpstracktech.com/api",
                         api_version=row.api_version or "1.0", api_key=key, vendor_user_id=vendor_user_id)
