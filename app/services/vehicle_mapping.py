import logging

from app.database.sensor_connection import get_db_connection

logger = logging.getLogger(__name__)


def get_vehicle_by_iot_kit(iot_kit: str):
    """
    Find the vehicle associated with an IoT kit.

    Matches:
        CSV filename IoT kit ID
        against vehicles.iot_kit

    Returns:
        tenant_id
        vehicle_number
        iot_kit

    Returns None if no matching vehicle exists.
    """

    query = """
        SELECT
            tenant_id,
            vehicle_number,
            iot_kit
        FROM dbo.vehicles
        WHERE iot_kit = ?
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(query, (iot_kit,))

        row = cursor.fetchone()

        if not row:
            logger.warning(
                "No vehicle found for IoT kit: %s",
                iot_kit
            )
            return None

        vehicle = {
            "tenant_id": row[0],
            "vehicle_number": row[1],
            "iot_kit": row[2]
        }

        logger.info(
            "Vehicle mapped successfully: IoT kit=%s, vehicle=%s",
            iot_kit,
            vehicle["vehicle_number"]
        )

        return vehicle

    except Exception:
        logger.exception(
            "Failed to map IoT kit to vehicle: %s",
            iot_kit
        )
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()