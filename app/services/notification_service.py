import logging
import smtplib

from email.message import EmailMessage

from app.config.settings import settings
from app.services.sensor_types import sensor_type_from_sub_id

logger = logging.getLogger(__name__)


def send_alert_email(alert: dict) -> bool:
    """
    Send an email when a sensor alert is detected.
    """

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.error("SMTP credentials are missing in .env")
        return False

    if not settings.ALERT_EMAIL:
        logger.error("ALERT_EMAIL is missing in .env")
        return False

    message = EmailMessage()

    message["Subject"] = (
        f"Sensor Alert - {alert.get('vehicle_number', 'Unknown Vehicle')}"
    )

    message["From"] = settings.SMTP_USERNAME
    message["To"] = settings.ALERT_EMAIL

    message.set_content(
        f"""
A sensor alert has been detected.

Tenant ID: {alert.get('tenant_id')}
Vehicle Number: {alert.get('vehicle_number')}
IoT Kit: {alert.get('iot_kit')}
Sensor Type: {sensor_type_from_sub_id(alert.get('sensor_sub_id')) or 'UNKNOWN'}
Sensor Sub ID: {alert.get('sensor_sub_id')}
Timestamp: {alert.get('timestamp')}

Sensor Data:
{alert.get('sensor_data')}

Please check the vehicle and sensor status.
"""
    )

    try:
        if settings.SMTP_USE_TLS:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=30
            ) as server:

                server.starttls()
                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD
                )
                server.send_message(message)

        else:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=30
            ) as server:

                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD
                )
                server.send_message(message)

        logger.info(
            "Alert email sent for vehicle: %s",
            alert.get("vehicle_number")
        )

        return True

    except Exception:
        logger.exception("Failed to send sensor alert email.")
        return False