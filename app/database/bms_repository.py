"""SQL Server access for the BMS vs Sensor comparison - uses ONLY the three existing tables:

    dbo.prs_sensor_readings   (read)   seat rows written by the existing PRS ingestion
    dbo.bms_stop_details      (read)   the BMS stops - never modified
    dbo.bms_sensor_comparison (write)  one final row per confirmed stop visit

The comparison table is used exactly as it is: only the columns that exist in it are written (journey_id / bms_stop_id
are filled when the table has them, ignored when it does not).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.bms_stop_tracker import FinalVisit, Stop, VehicleState
from app.services.sensor_types import PRS_SENSOR_SUB_ID

logger = logging.getLogger(__name__)


def _connect():
    # imported here so unit tests (no ODBC driver installed) can import this module
    from app.database.sensor_connection import get_db_connection
    return get_db_connection()


def _rows(cursor) -> List[Dict[str, Any]]:
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class BmsRepository:
    """SQL Server implementation. Tests use an in-memory fake with the same methods."""

    def __init__(self, source_table: str = "dbo.prs_sensor_readings"):
        if not re.fullmatch(r"[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)?", source_table):
            raise ValueError("invalid source table name")
        self.source_table = source_table
        self._snapshot_id_exists: Optional[bool] = None
        self._comparison_columns: Optional[Set[str]] = None

    # ------------------------------------------------------------------ worker reads
    def list_active_vehicles(self) -> List[Dict[str, Any]]:
        """Vehicles that have BMS stops AND a matching dbo.vehicles row (same tenant, vehicle number and device)."""
        sql = """
            SELECT DISTINCT b.tenant_id, b.vehicle_number, b.device_id, b.iot_kit
            FROM dbo.bms_stop_details b
            JOIN dbo.vehicles v
              ON v.tenant_id = b.tenant_id
             AND v.vehicle_number = b.vehicle_number
             AND TRY_CAST(v.device_id AS BIGINT) = b.device_id
        """
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            return _rows(cur)
        finally:
            conn.close()

    def get_stops(self, tenant_id: int, vehicle_number: str, device_id: int) -> List[Stop]:
        sql = """
            SELECT id, stop_sequence, stop_name, lat, [long], bms_in, bms_out, bms_total
            FROM dbo.bms_stop_details
            WHERE tenant_id = ? AND vehicle_number = ? AND device_id = ?
            ORDER BY stop_sequence
        """
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, (tenant_id, vehicle_number, device_id))
            return [
                Stop(id=r[0], sequence=r[1], name=r[2], lat=float(r[3]), lon=float(r[4]),
                     bms_in=r[5], bms_out=r[6], bms_total=r[7])
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def fetch_snapshot_rows(self, tenant_id: int, vehicle_number: str, after: datetime, limit_rows: int,
                            inclusive: bool = False) -> List[Dict[str, Any]]:
        """Seat rows of one vehicle with timestamp > after (>= when inclusive), oldest first. The 60 rows of a file are
        inserted in one transaction, so a snapshot is either fully visible or not at all."""
        has_snapshot_id = self._has_snapshot_id()
        sql = f"""
            SELECT TOP ({int(limit_rows)})
                   id, tenant_id, vehicle_number, iot_kit, [timestamp], sensor_data, lat, [long],
                   {"CAST(snapshot_id AS VARCHAR(36))" if has_snapshot_id else "CAST(NULL AS VARCHAR(36))"} AS snapshot_id
            FROM {self.source_table}
            WHERE tenant_id = ? AND vehicle_number = ? AND sensor_sub_id = ? AND [timestamp] {">=" if inclusive else ">"} ?
            ORDER BY [timestamp], id
        """
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, (tenant_id, vehicle_number, PRS_SENSOR_SUB_ID, after))
            return _rows(cur)
        finally:
            conn.close()

    def _has_snapshot_id(self) -> bool:
        """snapshot_id is optional: without it the 60 rows of a file are grouped by their identical timestamp."""
        if self._snapshot_id_exists is None:
            conn = _connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COL_LENGTH(?, 'snapshot_id')", (self.source_table,))
                self._snapshot_id_exists = cur.fetchone()[0] is not None
            finally:
                conn.close()
        return self._snapshot_id_exists

    def latest_snapshot(self, tenant_id: int, vehicle_number: str) -> Optional[Dict[str, Any]]:
        """The newest seat snapshot of a vehicle (for the 'latest record vs BMS stop' view)."""
        has_snapshot_id = self._has_snapshot_id()
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT TOP 1 [timestamp] FROM {self.source_table} "
                "WHERE tenant_id = ? AND vehicle_number = ? AND sensor_sub_id = ? ORDER BY [timestamp] DESC, id DESC",
                (tenant_id, vehicle_number, PRS_SENSOR_SUB_ID),
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute(
                f"""SELECT id, tenant_id, vehicle_number, iot_kit, [timestamp], sensor_data, lat, [long],
                           {"CAST(snapshot_id AS VARCHAR(36))" if has_snapshot_id else "CAST(NULL AS VARCHAR(36))"} AS snapshot_id
                    FROM {self.source_table}
                    WHERE tenant_id = ? AND vehicle_number = ? AND sensor_sub_id = ? AND [timestamp] = ?""",
                (tenant_id, vehicle_number, PRS_SENSOR_SUB_ID, row[0]),
            )
            rows = _rows(cur)
        finally:
            conn.close()
        from app.services.bms_snapshot import build_snapshots
        snap = build_snapshots(rows)[-1]
        return {"timestamp": snap.timestamp, "lat": snap.lat, "long": snap.lon, "occupied_seats": snap.occupied_count,
                "valid": snap.seats_valid, "problems": snap.problems, "row_count": snap.row_count}

    # ------------------------------------------------------------------ comparison table
    def _columns(self, cur) -> Set[str]:
        if self._comparison_columns is None:
            cur.execute("SELECT name FROM sys.columns WHERE object_id = OBJECT_ID('dbo.bms_sensor_comparison')")
            self._comparison_columns = {r[0].lower() for r in cur.fetchall()}
        return self._comparison_columns

    def last_comparison(self, tenant_id: int, vehicle_number: str, device_id: int) -> Optional[Dict[str, Any]]:
        """Newest stored comparison of the vehicle: used to rebuild the progress after a restart."""
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT TOP 1 stop_sequence, sensor_timestamp FROM dbo.bms_sensor_comparison
                   WHERE tenant_id = ? AND vehicle_number = ? AND device_id = ? ORDER BY id DESC""",
                (tenant_id, vehicle_number, device_id),
            )
            rows = _rows(cur)
            return rows[0] if rows else None
        finally:
            conn.close()

    def insert_comparison(self, row: Dict[str, Any]) -> int:
        """Insert the final comparison of one stop visit in ONE transaction. Idempotent: a visit is identified by
        (tenant, vehicle, device, stop_sequence, sensor_timestamp), so a retry / second worker inserts nothing new.
        Returns 1 when inserted, 0 when it already existed."""
        conn = _connect()
        try:
            cur = conn.cursor()
            existing = self._columns(cur)
            names = [c for c in row if c.lower() in existing]
            sql = (
                "IF NOT EXISTS (SELECT 1 FROM dbo.bms_sensor_comparison WITH (UPDLOCK, HOLDLOCK) "
                "WHERE tenant_id = ? AND vehicle_number = ? AND device_id = ? AND stop_sequence = ? AND sensor_timestamp = ?) "
                f"INSERT INTO dbo.bms_sensor_comparison ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})"
            )
            cur.execute(sql, (row["tenant_id"], row["vehicle_number"], row["device_id"], row["stop_sequence"],
                              row["sensor_timestamp"], *[row[c] for c in names]))
            inserted = max(cur.rowcount, 0)
            conn.commit()
            return inserted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------ API reads (always tenant-scoped)
    def list_stops(self, tenant_id: int, vehicle_number: Optional[str], device_id: Optional[int]) -> List[Dict[str, Any]]:
        where, params = ["tenant_id = ?"], [tenant_id]
        if vehicle_number is not None:
            where.append("vehicle_number = ?"); params.append(vehicle_number)
        if device_id is not None:
            where.append("device_id = ?"); params.append(device_id)
        sql = f"""
            SELECT id, tenant_id, vehicle_number, device_id, iot_kit, stop_sequence, stop_name,
                   lat, [long], bms_in, bms_out, bms_total, created_at
            FROM dbo.bms_stop_details WHERE {" AND ".join(where)}
            ORDER BY vehicle_number, device_id, stop_sequence
        """
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            return _rows(cur)
        finally:
            conn.close()

    def list_comparisons(self, tenant_id: int, filters: Dict[str, Any], page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
        where, params = ["tenant_id = ?"], [tenant_id]
        for column in ("vehicle_number", "device_id", "stop_sequence", "comparison_status"):
            if filters.get(column) is not None:
                where.append(f"{column} = ?"); params.append(filters[column])
        clause = " AND ".join(where)

        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM dbo.bms_sensor_comparison WHERE {clause}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""SELECT * FROM dbo.bms_sensor_comparison WHERE {clause}
                    ORDER BY created_at DESC, id DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
                params + [(page - 1) * page_size, page_size],
            )
            return _rows(cur), total
        finally:
            conn.close()

    def list_comparisons_for_summary(self, tenant_id: int, filters: Dict[str, Any], limit: int = 5000) -> List[Dict[str, Any]]:
        """Newest-first rows (only the columns the summary needs, no paging) for the KPI summary of the comparisons API."""
        where, params = ["tenant_id = ?"], [tenant_id]
        for column in ("vehicle_number", "device_id", "stop_sequence", "comparison_status"):
            if filters.get(column) is not None:
                where.append(f"{column} = ?"); params.append(filters[column])
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""SELECT TOP ({int(limit)}) id, stop_sequence, bms_in, bms_out, bms_total,
                           sensor_in, sensor_out, sensor_total, total_difference, comparison_status, sensor_timestamp
                    FROM dbo.bms_sensor_comparison WHERE {" AND ".join(where)}
                    ORDER BY created_at DESC, id DESC""",
                params,
            )
            return _rows(cur)
        finally:
            conn.close()

    def get_comparison(self, tenant_id: int, comparison_id: int) -> Optional[Dict[str, Any]]:
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM dbo.bms_sensor_comparison WHERE id = ? AND tenant_id = ?", (comparison_id, tenant_id))
            rows = _rows(cur)
            return rows[0] if rows else None
        finally:
            conn.close()


def comparison_row(state: VehicleState, stop: Stop, iot_kit: Optional[str], final: FinalVisit) -> Dict[str, Any]:
    """dict for dbo.bms_sensor_comparison from a finished visit (extra keys are dropped if the table lacks them)."""
    return {
        "tenant_id": state.tenant_id, "vehicle_number": state.vehicle_number, "device_id": state.device_id,
        "iot_kit": iot_kit, "journey_id": None,
        "bms_stop_id": stop.id, "stop_sequence": stop.sequence, "stop_name": stop.name,
        "bms_lat": stop.lat, "bms_long": stop.lon,
        "bms_in": stop.bms_in, "bms_out": stop.bms_out, "bms_total": stop.bms_total,
        "sensor_in": final.sensor_in, "sensor_out": final.sensor_out,
        "sensor_lat": final.sensor_lat, "sensor_long": final.sensor_long,
        "sensor_total": final.sensor_total, "total_difference": final.total_difference,
        "comparison_status": final.comparison_status, "sensor_timestamp": final.sensor_timestamp,
    }