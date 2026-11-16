
import logging
from datetime import datetime, timedelta

from app.database.sensor_connection import get_db_connection

from app.services.iot_kit_notification_service import (
    send_individual_missing_email,
    send_all_missing_email,
    send_recovery_email,
)

logger = logging.getLogger(__name__)

# Use 5 minutes for testing.
# Change to 30 minutes when moving to production.
MISSING_DATA_MINUTES = 30
NOTIFICATION_INTERVAL_MINUTES = MISSING_DATA_MINUTES # for every 30 minutes of missing data, send a notification.


def get_registered_kits():
    """
    Get all registered IoT kits and their monitoring status.

    For kits without a monitoring record, vehicles.created_at
    is used as their initial reference time.
    """

    query = """
        SELECT
            v.tenant_id,
            v.vehicle_number,
            v.iot_kit,
            v.created_at,
            vm.last_file_received_at,
            vm.is_missing,
            vm.missing_since,
            vm.last_notified_at,
            vm.notification_scope
        FROM dbo.vehicles v
        LEFT JOIN dbo.vehicle_data_monitoring vm
            ON vm.tenant_id = v.tenant_id
            AND vm.vehicle_number = v.vehicle_number
            AND vm.iot_kit = v.iot_kit
        WHERE
            v.iot_kit IS NOT NULL
            AND LTRIM(RTRIM(v.iot_kit)) <> ''
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query)

        columns = [column[0] for column in cursor.description]

        kits = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

        return kits

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def ensure_monitoring_record(kit):
    """Create a monitoring record if one does not exist."""

    query = """
        IF NOT EXISTS (
            SELECT 1
            FROM dbo.vehicle_data_monitoring
            WHERE tenant_id = ?
              AND vehicle_number = ?
              AND iot_kit = ?
        )
        BEGIN
            INSERT INTO dbo.vehicle_data_monitoring
            (
                tenant_id,
                vehicle_number,
                iot_kit,
                is_missing,
                missing_since,
                last_notified_at,
                notification_scope,
                last_file_received_at
            )
            VALUES (?, ?, ?, 0, NULL, NULL, 'INDIVIDUAL', ?)
        END
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            query,
            kit["tenant_id"],
            kit["vehicle_number"],
            kit["iot_kit"],
            kit["tenant_id"],
            kit["vehicle_number"],
            kit["iot_kit"],
            kit["created_at"],
        )

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def update_missing_status(
    kit,
    is_missing,
    missing_since=None,
    last_notified_at=None,
    notification_scope="INDIVIDUAL",
):
    """Update the existing monitoring record."""

    query = """
        UPDATE dbo.vehicle_data_monitoring
        SET
            is_missing = ?,
            missing_since = ?,
            last_notified_at = ?,
            notification_scope = ?
        WHERE
            tenant_id = ?
            AND vehicle_number = ?
            AND iot_kit = ?
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            query,
            is_missing,
            missing_since,
            last_notified_at,
            notification_scope,
            kit["tenant_id"],
            kit["vehicle_number"],
            kit["iot_kit"],
        )

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def record_successful_csv(tenant_id, vehicle_number, iot_kit):
    """
    Call this only after the CSV has been successfully
    processed and its database transaction has committed.

    Updates the last successful file processing time.
    Sends an immediate recovery email if the kit was missing.
    """

    now = datetime.now()

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                is_missing
            FROM dbo.vehicle_data_monitoring
            WHERE tenant_id = ?
              AND vehicle_number = ?
              AND iot_kit = ?
            """,
            tenant_id,
            vehicle_number,
            iot_kit,
        )

        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                """
                INSERT INTO dbo.vehicle_data_monitoring
                (
                    tenant_id,
                    vehicle_number,
                    iot_kit,
                    is_missing,
                    missing_since,
                    last_notified_at,
                    notification_scope,
                    last_file_received_at
                )
                VALUES (?, ?, ?, 0, NULL, NULL, 'INDIVIDUAL', ?)
                """,
                tenant_id,
                vehicle_number,
                iot_kit,
                now,
            )

            connection.commit()

            logger.info(
                "Initial monitoring record created for %s",
                iot_kit,
            )

            return

        was_missing = bool(row[0])

        # Update last successful CSV processing time.
        cursor.execute(
            """
            UPDATE dbo.vehicle_data_monitoring
            SET last_file_received_at = ?
            WHERE tenant_id = ?
              AND vehicle_number = ?
              AND iot_kit = ?
            """,
            now,
            tenant_id,
            vehicle_number,
            iot_kit,
        )

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

    if was_missing:
        kit = {
            "tenant_id": tenant_id,
            "vehicle_number": vehicle_number,
            "iot_kit": iot_kit,
        }

        if send_recovery_email(kit):
            update_missing_status(
                kit,
                is_missing=0,
                missing_since=None,
                last_notified_at=None,
                notification_scope="INDIVIDUAL",
            )

            logger.info(
                "IoT kit recovered: %s",
                iot_kit,
            )

        else:
            logger.error(
                "Recovery email failed for %s. "
                "The kit will remain marked missing until retry.",
                iot_kit,
            )


def check_missing_iot_kits():
    """
    Check all registered IoT kits.

    If all registered kits are missing:
        Send one consolidated email.

    Otherwise:
        Send individual emails for missing kits.
    """

    now = datetime.now()

    try:
        kits = get_registered_kits()

        if not kits:
            logger.warning("No registered IoT kits found.")
            return

        # Ensure every registered kit has a monitoring record.
        for kit in kits:
            ensure_monitoring_record(kit)

        # Refresh monitoring records after initialization.
        kits = get_registered_kits()

        missing_kits = []

        for kit in kits:
            try:
                last_received = (
                    kit["last_file_received_at"]
                    or kit["created_at"]
                )

                if last_received is None:
                    logger.warning(
                        "No initial timestamp for %s",
                        kit["iot_kit"],
                    )
                    continue

                is_missing = bool(kit["is_missing"])

                elapsed = now - last_received

                if (
                    not is_missing
                    and elapsed >= timedelta(
                        minutes=MISSING_DATA_MINUTES
                    )
                ):
                    # Mark the kit missing.
                    update_missing_status(
                        kit,
                        is_missing=1,
                        missing_since=last_received,
                        last_notified_at=None,
                        notification_scope="INDIVIDUAL",
                    )

                    kit["is_missing"] = 1
                    kit["missing_since"] = last_received
                    kit["last_notified_at"] = None
                    kit["notification_scope"] = "INDIVIDUAL"

                    logger.warning(
                        "IoT kit marked missing: %s",
                        kit["iot_kit"],
                    )

                if kit["is_missing"]:
                    missing_kits.append(kit)

            except Exception:
                logger.exception(
                    "Monitoring failed for IoT kit %s",
                    kit.get("iot_kit"),
                )

        if not missing_kits:
            logger.info("All IoT kits are online.")
            return

        # Determine whether every registered kit is missing.
        all_kits_missing = (
            len(missing_kits) == len(kits)
        )

        if all_kits_missing:
            # Send a consolidated email on first transition
            # to ALL scope, or after the repeat interval.
            scope_changed = any(
                kit["notification_scope"] != "ALL"
                for kit in missing_kits
            )

            notification_due = any(
                kit["last_notified_at"] is None
                or now - kit["last_notified_at"]
                >= timedelta(
                    minutes=NOTIFICATION_INTERVAL_MINUTES
                )
                for kit in missing_kits
            )

            if scope_changed or notification_due:
                if send_all_missing_email(missing_kits):

                    for kit in missing_kits:
                        update_missing_status(
                            kit,
                            is_missing=1,
                            missing_since=kit["missing_since"],
                            last_notified_at=now,
                            notification_scope="ALL",
                        )

                    logger.warning(
                        "Consolidated missing-data email sent "
                        "for %s IoT kits.",
                        len(missing_kits),
                    )

            return

        # Some kits are online. Switch remaining missing kits
        # from ALL scope to individual notification scope.
        for kit in missing_kits:
            try:
                last_notified = kit["last_notified_at"]

                if kit["notification_scope"] == "ALL":
                    update_missing_status(
                        kit,
                        is_missing=1,
                        missing_since=kit["missing_since"],
                        last_notified_at=last_notified,
                        notification_scope="INDIVIDUAL",
                    )

                should_notify = (
                    last_notified is None
                    or now - last_notified >= timedelta(
                        minutes=NOTIFICATION_INTERVAL_MINUTES
                    )
                )

                if should_notify:
                    if send_individual_missing_email(kit):
                        update_missing_status(
                            kit,
                            is_missing=1,
                            missing_since=kit["missing_since"],
                            last_notified_at=now,
                            notification_scope="INDIVIDUAL",
                        )

                        logger.warning(
                            "Individual missing-data email sent: %s",
                            kit["iot_kit"],
                        )

            except Exception:
                logger.exception(
                    "Individual notification failed for %s",
                    kit.get("iot_kit"),
                )

    except Exception:
        logger.exception("IoT kit monitoring check failed.")
