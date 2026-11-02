"""Bearer-token authentication and permission checks.

Tokens are issued by the Java BFF (Python never issues sessions). This module only verifies them with the
shared secret (HS256, Base64-decoded key, issuer, exp with 60s skew), reads the Java claims
(sub=user id, tid=tenant id, role, perms), then re-checks the user and tenant status in SQL Server. Permissions
come from users -> role_permissions by default (revocations apply immediately) or from the `perms` claim when
SAFEFARE_JWT_PERMISSIONS_SOURCE=token.
"""
import base64
import binascii
from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, ForbiddenError, UnauthorizedError
from app.db import tables as t
from app.db.session import get_db

MAX_BIGINT = 2**63 - 1  # SQL Server BIGINT

_bearer = HTTPBearer(auto_error=False, description="JWT issued by the SafeFare Java BFF")


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    tenant_id: int
    vendor_user_id: int | None
    permissions: frozenset[str]
    role: str | None = None  # role code from the Java token's `role` claim

    def has(self, permission: str) -> bool:
        return permission in self.permissions


@dataclass(frozen=True)
class TokenClaims:
    """Claims of a Java-issued access token (AuthPrincipal.from(Jwt) on the Java side)."""
    subject: str
    tenant_id: int
    role: str
    permissions: frozenset[str]


MIN_SECRET_BYTES = 32  # same floor as the Java SecurityProperties.secretKey()


def _secret(settings: Settings) -> bytes:
    if settings.safefare_jwt_secret is None or not settings.safefare_jwt_secret.get_secret_value().strip():
        raise ConfigurationError("Authentication is not configured (SAFEFARE_JWT_SECRET)")
    raw = settings.safefare_jwt_secret.get_secret_value().strip()
    if not settings.safefare_jwt_secret_base64:
        return raw.encode()
    try:  # Java: Base64.getDecoder().decode(jwtSecret.trim()) -> standard alphabet, strict
        key = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise ConfigurationError("SAFEFARE_JWT_SECRET must be Base64 encoded") from None
    if len(key) < MIN_SECRET_BYTES:
        raise ConfigurationError("SAFEFARE_JWT_SECRET must decode to at least 32 bytes")
    return key


def _invalid(message: str = "Invalid or expired token") -> UnauthorizedError:
    return UnauthorizedError(message, code="INVALID_TOKEN")


def decode_token(token: str, settings: Settings) -> dict:
    """Verify signature (HS256), expiry/not-before (with Spring's 60s skew) and issuer; return the claims."""
    key = _secret(settings)  # configuration problems are a 500, never a 401
    try:
        return jwt.decode(
            token, key, algorithms=settings.jwt_algorithms,
            audience=settings.safefare_jwt_audience or None, issuer=settings.safefare_jwt_issuer or None,
            leeway=settings.safefare_jwt_leeway_seconds,
            options={"require": ["exp", settings.safefare_jwt_user_claim, settings.safefare_jwt_tenant_claim],
                     "verify_aud": bool(settings.safefare_jwt_audience)},
        )
    except jwt.PyJWTError as exc:
        raise _invalid() from exc


def extract_claims(claims: dict, settings: Settings) -> TokenClaims:
    """Read user / tenant / role / permissions exactly as the Java AuthPrincipal does: `sub` is the user id,
    `tid` a number, `role` a string, `perms` a list of strings (possibly empty)."""
    subject = claims.get(settings.safefare_jwt_user_claim)
    if not isinstance(subject, str) or not subject.strip():
        raise _invalid("Token has no user claim")
    tenant = claims.get(settings.safefare_jwt_tenant_claim)
    if isinstance(tenant, bool) or not isinstance(tenant, int) or not 0 < tenant <= MAX_BIGINT:
        raise _invalid("Invalid tenant claim")
    role = claims.get(settings.safefare_jwt_role_claim)
    if not isinstance(role, str) or not role:
        raise _invalid("Invalid role claim")
    perms = claims.get(settings.safefare_jwt_permissions_claim)
    if not isinstance(perms, list) or not all(isinstance(p, str) for p in perms):
        raise _invalid("Invalid permissions claim")
    return TokenClaims(subject=subject.strip(), tenant_id=tenant, role=role, permissions=frozenset(perms))


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
                     db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    token = extract_claims(decode_token(credentials.credentials, settings), settings)

    query = (select(t.users.c.id, t.users.c.tenant_id, t.users.c.role_id, t.users.c.vendor_user_id)
             .join(t.tenants, t.tenants.c.id == t.users.c.tenant_id)
             .where(t.users.c.deleted_at.is_(None), t.users.c.status == "ACTIVE", t.tenants.c.status == "ACTIVE",
                    t.users.c.tenant_id == token.tenant_id))  # the token's tenant must own the user
    if token.subject.isdigit():
        query = query.where(t.users.c.id == int(token.subject))
    elif "@" in token.subject:
        query = query.where(t.users.c.email == token.subject)
    else:
        raise _invalid("Unsupported user claim")
    rows = db.execute(query).all()
    if len(rows) != 1:
        raise UnauthorizedError("User is not active", code="USER_INACTIVE")
    user = rows[0]
    if settings.safefare_jwt_permissions_source.strip().lower() == "token":
        permissions = token.permissions  # same source of truth as the Java BFF
    else:
        permissions = frozenset(db.execute(select(t.role_permissions.c.permission_code)
                                           .where(t.role_permissions.c.role_id == user.role_id)).scalars())
    return CurrentUser(user_id=user.id, tenant_id=user.tenant_id, vendor_user_id=user.vendor_user_id,
                       permissions=permissions, role=token.role)


def require_permissions(*codes: str, any_of: bool = False):
    """Dependency factory: all `codes` are required (or at least one when any_of=True)."""

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        granted = [c for c in codes if user.has(c)]
        if (any_of and not granted) or (not any_of and len(granted) != len(codes)):
            raise ForbiddenError(details={"required": list(codes), "mode": "any" if any_of else "all"})
        return user

    return dependency