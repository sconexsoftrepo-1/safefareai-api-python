"""Application settings, loaded from environment variables and an optional project-root `.env` file.

Secrets (DB password, JWT secret, vendor keys) are never hardcoded. Vendor keys are resolved per tenant at
request time from `dbo.vendor_accounts.secret_ref` (see app/vendor/credentials.py).
"""
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Real environment variables always win over values in .env.
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _odbc_value(value: str) -> str:
    """Brace-quote an ODBC connection-string value so ';', '=' or '}' in passwords are safe."""
    return "{" + value.replace("}", "}}") + "}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # --- Application ---------------------------------------------------------------------------------------
    app_name: str = "SafeFare Fleet Python API"
    app_api_prefix: str = "/api/v1"
    app_log_level: str = "INFO"
    app_cors_origins: str = ""  # comma separated

    # --- SQL Server (same variables as the Java fleet-bff datasource) ----------------------------------------
    safefare_db_host: str | None = None
    safefare_db_port: int = 1433
    safefare_db_name: str | None = None
    safefare_db_username: str | None = None
    safefare_db_password: SecretStr | None = None
    safefare_db_trust_server_cert: bool = True
    safefare_db_encrypt: bool = True
    safefare_db_odbc_driver: str = "ODBC Driver 17 for SQL Server"
    safefare_db_pool_size: int = 10
    safefare_db_max_overflow: int = 10
    safefare_db_login_timeout: int = 15

    # --- Authentication (tokens are issued by the Java BFF; Python only verifies them) -----------------------
    # Defaults mirror the Java JwtTokenService / SecurityConfig / SecurityProperties:
    #   * HS256, key = Base64-decode(FLEET_JWT_SECRET)  -> SAFEFARE_JWT_SECRET must be the SAME Base64 string
    #   * claims: iss, sub (user id), iat, exp, tid (tenant id), role (role code), perms (permission list)
    #   * no "aud" claim is issued, so leave SAFEFARE_JWT_AUDIENCE empty
    safefare_jwt_secret: SecretStr | None = None
    safefare_jwt_secret_base64: bool = True
    safefare_jwt_algorithms: str = "HS256"
    safefare_jwt_issuer: str | None = None  # must equal fleet.security.issuer on the Java side
    safefare_jwt_audience: str | None = None
    safefare_jwt_leeway_seconds: int = 60  # Spring's default clock skew for exp/nbf
    safefare_jwt_user_claim: str = "sub"
    safefare_jwt_tenant_claim: str = "tid"
    safefare_jwt_role_claim: str = "role"
    safefare_jwt_permissions_claim: str = "perms"
    # Where effective permissions come from: "token" = the `perms` claim (what the Java BFF enforces), or
    # "database" = re-read users -> role_permissions on every request (revocations apply immediately).
    safefare_jwt_permissions_source: str = "database"

    # --- GPS TrackTech vendor API -----------------------------------------------------------------------------
    gpstracktech_language: str = "en"
    gpstracktech_timeout: None = None
    gpstracktech_max_retries: int = 2
    gpstracktech_retry_backoff: float = 0.5
    gpstracktech_page_size: int = 100
    gpstracktech_max_pages: int = 20
    gpstracktech_max_devices_per_query: int = 200
    gpstracktech_command_chunk_size: int = 100
    gpstracktech_video_demo_base_url: str = "https://y.gpstracktech.com"

    # --- Business limits ------------------------------------------------------------------------------------
    query_max_range_days: int = 31
    track_max_range_days: int = 7
    voice_max_upload_mb: float = 5.0
    fence_max_points: int = 500

    # Safety rating weights per alarm severity (1 severe .. 4 notice). Penalty points per 100 km.
    safety_weight_severe: float = 10.0
    safety_weight_moderate: float = 5.0
    safety_weight_general: float = 2.0
    safety_weight_notice: float = 1.0
    safety_min_distance_km: float = 1.0

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]

    @property
    def jwt_algorithms(self) -> list[str]:
        return [a.strip() for a in self.safefare_jwt_algorithms.split(",") if a.strip()]

    @property
    def database_configured(self) -> bool:
        return bool(self.safefare_db_host and self.safefare_db_name and self.safefare_db_username
                    and self.safefare_db_password)

    def sqlalchemy_url(self) -> str:
        if not self.database_configured:
            raise RuntimeError("SAFEFARE_DB_HOST, SAFEFARE_DB_NAME, SAFEFARE_DB_USERNAME and "
                               "SAFEFARE_DB_PASSWORD must be set")
        parts = [
            f"DRIVER={_odbc_value(self.safefare_db_odbc_driver)}",
            f"SERVER={self.safefare_db_host},{self.safefare_db_port}",
            f"DATABASE={_odbc_value(self.safefare_db_name)}",
            f"UID={_odbc_value(self.safefare_db_username)}",
            f"PWD={_odbc_value(self.safefare_db_password.get_secret_value())}",
            f"Encrypt={'yes' if self.safefare_db_encrypt else 'no'}",
            f"TrustServerCertificate={'yes' if self.safefare_db_trust_server_cert else 'no'}",
            "APP=fleet-bff-python",
        ]
        return "mssql+pyodbc:///?odbc_connect=" + quote_plus(";".join(parts))

    def severity_weight(self, severity: int | None) -> float:
        return {1: self.safety_weight_severe, 2: self.safety_weight_moderate,
                3: self.safety_weight_general, 4: self.safety_weight_notice}.get(severity or 3,
                                                                                  self.safety_weight_general)


@lru_cache
def get_settings() -> Settings:
    return Settings()