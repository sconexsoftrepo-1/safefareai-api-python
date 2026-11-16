
from decimal import Decimal


# Maintenance status values stored in SQL Server
NORMAL = "NORMAL"
DUE_SOON = "DUE_SOON"
CRITICAL_85 = "CRITICAL_85"
CRITICAL_95 = "CRITICAL_95"
OVERDUE = "OVERDUE"


# Tyre usage thresholds
TYRE_WARNING_THRESHOLDS = {
    Decimal("75"): DUE_SOON,
    Decimal("85"): CRITICAL_85,
    Decimal("95"): CRITICAL_95,
    Decimal("100"): OVERDUE,
}


def calculate_maintenance_status(
    current_distance_km: Decimal,
    tyre_life_limit_km: Decimal,
) -> str:
    """
    Calculate tyre maintenance status based on tyre usage percentage.
    """

    if tyre_life_limit_km <= 0:
        raise ValueError("Tyre life limit must be greater than zero.")

    usage_percentage = (
        current_distance_km / tyre_life_limit_km
    ) * Decimal("100")

    if usage_percentage >= Decimal("100"):
        return OVERDUE

    if usage_percentage >= Decimal("95"):
        return CRITICAL_95

    if usage_percentage >= Decimal("85"):
        return CRITICAL_85

    if usage_percentage >= Decimal("75"):
        return DUE_SOON

    return NORMAL
