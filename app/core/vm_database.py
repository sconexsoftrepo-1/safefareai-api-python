"""SQL Server connection management (pyodbc).

If your project already exposes a pyodbc connection factory, pass it to
``Database(connection_factory=...)`` so this module reuses it instead of
opening its own connections.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

from app.core.vm_config import Settings

log = logging.getLogger(__name__)


def _odbc_value(value: str) -> str:
    """Brace-quote a connection-string value so ; and } in passwords are safe."""
    return "{" + str(value).replace("}", "}}") + "}"


def build_connection_string(s: Settings) -> str:
    return (
        f"DRIVER={_odbc_value(s.db_driver)};"
        f"SERVER={s.db_server},{s.db_port};"
        f"DATABASE={_odbc_value(s.db_database)};"
        f"UID={_odbc_value(s.db_username)};"
        f"PWD={_odbc_value(s.db_password)};"
        f"Encrypt={s.db_encrypt};"
        f"TrustServerCertificate={s.db_trust_server_certificate};"
    )


class Database:
    def __init__(self, settings: Settings, connection_factory: Optional[Callable[[], Any]] = None):
        self._settings = settings
        self._factory = connection_factory

    def _connect(self):
        if self._factory is not None:
            return self._factory()
        import pyodbc  # imported lazily so unit tests do not need the ODBC driver

        try:
            return pyodbc.connect(
                build_connection_string(self._settings),
                autocommit=False,
                timeout=self._settings.db_connect_timeout,
            )
        except pyodbc.Error as exc:
            # Do not log the connection string: it contains the password.
            log.error("SQL Server connection failed (server=%s, database=%s): %s",
                      self._settings.db_server, self._settings.db_database, type(exc).__name__)
            raise

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Yield a connection inside one transaction: commit on success, roll back on any error."""
        conn = self._connect()
        try:
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute(f"SET LOCK_TIMEOUT {int(self._settings.db_lock_timeout_ms)}")
            cur.close()
            yield conn
            conn.commit()
        except BaseException:
            try:
                conn.rollback()
            except Exception:  # pragma: no cover
                log.exception("Rollback failed")
            raise
        finally:
            try:
                conn.close()
            except Exception:  # pragma: no cover
                pass
