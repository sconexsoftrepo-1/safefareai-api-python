"""SQL access for the alarm media migration. Only the existing dbo.alarm_media table is used (no schema change).

Columns used: id, alarm_time, media_type, vendor_url, s3_key.

"One worker per record" is enforced with a SQL Server application lock (sp_getapplock, owner = Session) taken on a
dedicated connection that stays open while the file is transferred. It needs no extra column or table, works across
several backend processes and is released automatically if the process dies. The final UPDATE also repeats
"AND s3_key IS NULL", so a record that is already done can never be overwritten.

The connection comes from app.database.sensor_connection (the same SQL Server connection the sensor / PRS tables use).
If alarm_media lives in another database, change _connect() below - nothing else.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOCK_PREFIX = "alarm_media:"


def _connect():
    from app.database.sensor_connection import get_db_connection
    return get_db_connection()


def _rows(cur) -> List[Dict[str, Any]]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _is_unique_violation(error: Exception) -> bool:
    """SQL Server 2601 (duplicate key in a unique index) / 2627 (unique constraint)."""
    text = str(error)
    return "23000" in text and ("(2601)" in text or "(2627)" in text)


class MediaClaim:
    """An exclusive lock on one alarm_media record (use as a context manager)."""

    def __init__(self, conn, table: str, record_id: int):
        self._conn = conn
        self._table = table
        self.record_id = record_id

    def mark_done(self, s3_url: str) -> bool:
        """Store the full S3 URL in s3_key. False when the record already had an s3_key (nothing is overwritten)."""
        cur = self._conn.cursor()
        try:
            cur.execute(f"UPDATE {self._table} SET s3_key = ? WHERE id = ? AND s3_key IS NULL", (s3_url, self.record_id))
        except Exception as error:
            if not _is_unique_violation(error):
                raise
            from app.services.alarm_media_service import DuplicateMediaError
            owner = None
            try:
                row = self._conn.cursor().execute(
                    f"SELECT TOP 1 id FROM {self._table} WHERE s3_key = ? AND id <> ?", (s3_url, self.record_id)).fetchone()
                owner = row[0] if row else None
            except Exception:
                pass
            raise DuplicateMediaError(s3_url, owner) from None
        return cur.rowcount == 1

    def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is None:
            return
        try:
            conn.cursor().execute("EXEC sp_releaseapplock @Resource = ?, @LockOwner = 'Session'",
                                  (_LOCK_PREFIX + str(self.record_id),))
        except Exception:
            logger.debug("alarm_media id=%s: releasing the lock failed (closing the connection releases it)", self.record_id)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def __enter__(self) -> "MediaClaim":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class AlarmMediaRepository:
    def __init__(self, table: str = "dbo.alarm_media"):
        self.table = table

    def fetch_pending(self, after_id: int, limit: int) -> List[Dict[str, Any]]:
        """Up to `limit` records with s3_key IS NULL and id > after_id, oldest id first."""
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""SELECT TOP ({int(limit)}) id, alarm_time, media_type, vendor_url
                    FROM {self.table}
                    WHERE s3_key IS NULL AND id > ?
                    ORDER BY id""",
                (after_id,),
            )
            return _rows(cur)
        finally:
            conn.close()

    def fetch_by_ids(self, ids: List[int]) -> List[Dict[str, Any]]:
        """id, media_type, s3_key of the given records (used to create viewing links)."""
        ids = [int(i) for i in ids][:100]
        if not ids:
            return []
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT id, media_type, s3_key FROM {self.table} WHERE id IN ({','.join('?' * len(ids))})", ids)
            return _rows(cur)
        finally:
            conn.close()

    def claim(self, record_id: int) -> Optional[MediaClaim]:
        """Lock the record for this worker. None when another worker holds it or it is no longer pending."""
        conn = _connect()
        claim: Optional[MediaClaim] = None
        try:
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                """SET NOCOUNT ON;
                   DECLARE @r INT;
                   EXEC @r = sp_getapplock @Resource = ?, @LockMode = 'Exclusive', @LockOwner = 'Session', @LockTimeout = 0;
                   SELECT @r;""",
                (_LOCK_PREFIX + str(record_id),),
            )
            if cur.fetchone()[0] < 0:                       # < 0: not granted (someone else is working on it)
                conn.close()
                return None
            claim = MediaClaim(conn, self.table, record_id)
            cur.execute(f"SELECT 1 FROM {self.table} WHERE id = ? AND s3_key IS NULL", (record_id,))
            if cur.fetchone() is None:                      # finished by someone else in the meantime
                claim.close()
                return None
            return claim
        except Exception:
            if claim is not None:
                claim.close()
            else:
                try:
                    conn.close()
                except Exception:
                    pass
            raise