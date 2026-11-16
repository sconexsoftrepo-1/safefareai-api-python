
from fastapi import Header, HTTPException


def get_tenant_id(
    x_tenant_id: int = Header(..., alias="X-Tenant-ID")
) -> int:
    """
    Temporary tenant identification for development and testing.

    Reads tenant_id from the X-Tenant-ID request header.

    IMPORTANT:
    Before production, replace this with the tenant_id
    extracted from the authenticated JWT/user context.
    """

    if x_tenant_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid tenant ID."
        )

    return x_tenant_id
