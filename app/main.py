"""SafeFare Fleet Python API (FastAPI). Implements the features assigned to Python in
Fleet_Features_Tasks_List.xlsx; the Java BFF keeps every other feature and issues the auth tokens."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, public_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.session import dispose_engine
from app.vendor.client import VendorClient


def create_app(vendor_client: VendorClient | None = None) -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.app_log_level.upper(),
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.vendor_client = vendor_client or VendorClient(settings)
        try:
            yield
        finally:
            app.state.vendor_client.close()
            dispose_engine()

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan,
                  description="Python endpoints of the SafeFare fleet BFF: dashboards, track playback, video, "
                              "AI events & alarm handling, reports, fence voices and sensor commands. "
                              "Authenticate with the bearer token issued by the Java BFF.")
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                           allow_methods=["*"], allow_headers=["*"])
    register_exception_handlers(app)
    app.include_router(public_router)
    app.include_router(api_router, prefix=settings.app_api_prefix)
    return app


app = create_app()
