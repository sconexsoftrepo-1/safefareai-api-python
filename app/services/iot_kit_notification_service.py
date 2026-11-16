
import logging
import smtplib
from email.message import EmailMessage

from app.config.settings import settings

logger = logging.getLogger(__name__)


def send_email(subject: str, body: str) -> bool:
    """Send email through configured SMTP."""

    if not all([
        settings.ALERT_EMAIL,
        settings.SMTP_USERNAME,
        settings.SMTP_PASSWORD
    ]):
        logger.error("SMTP configuration is incomplete.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_USERNAME
    message["To"] = settings.ALERT_EMAIL
    message.set_content(body)

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=20
        ) as server:

            if settings.SMTP_USE_TLS:
                server.starttls()

            server.login(
                settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD
            )

            server.send_message(message)

        logger.info("Email sent successfully: %s", subject)
        return True

    except Exception:
        logger.exception("Email sending failed: %s", subject)
        return False


def send_individual_missing_email(kit: dict) -> bool:
    """Send an email for one offline IoT kit."""

    subject = f"IoT Kit Offline - {kit['iot_kit']}"

    body = f"""
Dear Fleet Administrator,

No new CSV data has been received for this IoT kit
for the configured 5-minute threshold.

Tenant ID: {kit['tenant_id']}
Vehicle Number: {kit['vehicle_number']}
IoT Kit: {kit['iot_kit']}

Last Successful CSV Processing:
{kit.get('last_file_received_at') or 'Never'}

Missing Since:
{kit.get('missing_since')}

Please check the device power, internet connection,
sensor connections and S3 upload process.

This notification will repeat every 5 minutes
while the IoT kit remains offline.

Regards,
IoT Monitoring System
"""

    return send_email(subject, body)


def send_all_missing_email(kits: list) -> bool:
    """Send one consolidated email for all offline kits."""

    subject = "Critical Alert - All IoT Kits Offline"

    details = []

    for index, kit in enumerate(kits, start=1):
        details.append(
            f"""
Kit {index}
-------------------------
Tenant ID: {kit['tenant_id']}
Vehicle Number: {kit['vehicle_number']}
IoT Kit: {kit['iot_kit']}
Last Successful CSV Processing:
{kit.get('last_file_received_at') or 'Never'}
Missing Since: {kit.get('missing_since')}
"""
        )

    body = f"""
Dear Fleet Administrator,

CRITICAL ALERT!

All registered IoT kits have stopped uploading CSV data.

Total Offline Kits: {len(kits)}

Offline Kit Details:

{''.join(details)}

Please investigate the IoT devices, network connectivity
and S3 upload pipeline.

This consolidated notification will repeat every
5 minutes while all registered kits remain offline.

Regards,
IoT Monitoring System
"""

    return send_email(subject, body)


def send_recovery_email(kit: dict) -> bool:
    """Send an immediate recovery email for one recovered kit."""

    subject = f"IoT Kit Recovered - {kit['iot_kit']}"

    body = f"""
Dear Fleet Administrator,

Sensor data uploads have resumed for this IoT kit.

Tenant ID: {kit['tenant_id']}
Vehicle Number: {kit['vehicle_number']}
IoT Kit: {kit['iot_kit']}

The latest CSV file has been successfully processed
and the sensor readings have been saved.

The IoT kit has returned to normal monitoring.

Regards,
IoT Monitoring System
"""

    return send_email(subject, body)
