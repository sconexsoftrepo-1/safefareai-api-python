
import pyodbc
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Establish and return a SQL Server database connection.
    Uses credentials from the .env file.
    """

    required_values = {
        "DB_SERVER": settings.DB_SERVER,
        "DB_NAME": settings.DB_NAME,
        "DB_USERNAME": settings.DB_USERNAME,
        "DB_PASSWORD": settings.DB_PASSWORD,
    }

    missing = [
        key for key, value in required_values.items()
        if not value
    ]

    if missing:
        raise ValueError(
            f"Missing database configuration: {', '.join(missing)}"
        )

    connection_string = (
        f"DRIVER={{{settings.DB_DRIVER}}};"
        f"SERVER={settings.DB_SERVER};"
        f"DATABASE={settings.DB_NAME};"
        f"UID={settings.DB_USERNAME};"
        f"PWD={settings.DB_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate="
        f"{'yes' if settings.DB_TRUST_SERVER_CERTIFICATE else 'no'};"
        f"Connection Timeout=30;"
    )

    try:
        connection = pyodbc.connect(connection_string)
        logger.info("SQL Server connection established successfully.")
        return connection

    except pyodbc.Error:
        logger.exception("Failed to connect to SQL Server.")
        raise


def test_db_connection():
    """
    Test SQL Server connectivity.
    """

    connection = None

    try:
        connection = get_db_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME(), GETDATE()")

        result = cursor.fetchone()

        logger.info(
            "Database: %s | Server time: %s",
            result[0],
            result[1]
        )

        return {
            "success": True,
            "database": result[0],
            "server_time": str(result[1])
        }

    except Exception as error:
        logger.exception("Database connection test failed.")

        return {
            "success": False,
            "error": str(error)
        }

    finally:
        if connection:
            connection.close()
