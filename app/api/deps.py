"""Shared FastAPI dependencies."""
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.vendor.api import GpsTrackTechApi
from app.vendor.client import VendorClient
from app.vendor.credentials import load_vendor_account


def get_vendor_client(request: Request) -> VendorClient:
    return request.app.state.vendor_client


def get_vendor_api(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db),
                   client: VendorClient = Depends(get_vendor_client)) -> GpsTrackTechApi:
    """Vendor API bound to the caller's tenant account; the key never leaves the backend."""
    return GpsTrackTechApi(client, load_vendor_account(db, user.tenant_id))


__all__ = ["get_db", "get_settings", "get_vendor_api", "get_vendor_client", "Settings", "Session"]
