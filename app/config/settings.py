import os
from pathlib import Path
from dotenv import load_dotenv

# Locate the project-root .env automatically (shared with Iris AI)
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)


class Settings:

    # ==========================================
    # AWS S3 CONFIGURATION
    # ==========================================

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    S3_FOLDER = os.getenv("S3_FOLDER", "test-backend/")

    # ==========================================
    # SQL SERVER CONFIGURATION
    # Read from SENSOR_DB_* so they don't clash with the
    # Iris AI DB_* variables (different database).
    # ==========================================

    DB_SERVER = os.getenv("SENSOR_DB_SERVER")
    DB_NAME = os.getenv("SENSOR_DB_NAME")
    DB_USERNAME = os.getenv("SENSOR_DB_USERNAME")
    DB_PASSWORD = os.getenv("SENSOR_DB_PASSWORD")

    DB_DRIVER = os.getenv(
        "SENSOR_DB_DRIVER",
        "ODBC Driver 17 for SQL Server"
    )

    DB_TRUST_SERVER_CERTIFICATE = os.getenv(
        "SENSOR_DB_TRUST_SERVER_CERTIFICATE", "yes"
    ).lower() in ("yes", "true", "1")

    # ==========================================
    # SENSOR INGESTION CONFIGURATION
    # ==========================================

    # Normal sensor files (-> sensor_readings): every 5 seconds
    S3_POLL_INTERVAL = int(
        os.getenv("S3_POLL_INTERVAL", "5")
    )

    # PRS seat files (-> prs_sensor_readings): every 10 seconds
    PRS_POLL_INTERVAL = int(
        os.getenv("PRS_POLL_INTERVAL", "10")
    )

    # A PRS reading gets lat/long from the device_positions row whose received_at
    # is closest to the reading time. Rows further away than this are not used
    # (lat/long stay NULL). Use a big number to always take the closest row.
    PRS_POSITION_MAX_GAP_SECONDS = int(
        os.getenv("PRS_POSITION_MAX_GAP_SECONDS", "900")
    )

    # Where PRS readings get lat/long from:
    #   vendor_api       -> the GPS vendor's /monitor/getRealTimeInfo API (current position)
    #   device_positions -> nearest row of dbo.device_positions (PRS_POSITION_MAX_GAP_SECONDS above)
    PRS_LOCATION_SOURCE = os.getenv("PRS_LOCATION_SOURCE", "vendor_api").strip().lower()

    # GPS vendor API
    VENDOR_API_BASE_URL = os.getenv("VENDOR_API_BASE_URL", "").strip()
    VENDOR_API_PATH = os.getenv("VENDOR_API_PATH", "/monitor/getRealTimeInfo").strip()
    # Extra request headers as JSON, e.g. {"Authorization": "Bearer xxx"} or {"token": "xxx"}
    VENDOR_API_HEADERS = os.getenv("VENDOR_API_HEADERS", "").strip()
    # 0 = ask by device name (vehicles.vehicle_number), 1 = ask by device ID (vehicles.device_id)
    VENDOR_QUERY_TYPE = int(os.getenv("VENDOR_QUERY_TYPE", "0"))
    VENDOR_API_TIMEOUT = int(os.getenv("VENDOR_API_TIMEOUT", "10"))
    # A position is reused for this many seconds (many PRS files arrive per minute)
    VENDOR_LOCATION_CACHE_SECONDS = int(os.getenv("VENDOR_LOCATION_CACHE_SECONDS", "10"))

    TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

    # ==========================================
    # EMAIL CONFIGURATION
    # ==========================================

    ALERT_EMAIL = os.getenv("ALERT_EMAIL")

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    SMTP_USE_TLS = os.getenv(
        "SMTP_USE_TLS", "true"
    ).lower() in ("true", "1", "yes")


settings = Settings()