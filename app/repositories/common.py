"""Generic persistence helpers."""
import json
from typing import Any

from sqlalchemy import Table, insert, select, update
from sqlalchemy.orm import Session

# Serialises concurrent upserts of the same key on SQL Server; ignored by other dialects (tests use SQLite).
_LOCK_HINT = "WITH (UPDLOCK, HOLDLOCK)"


def upsert(db: Session, table: Table, key: dict[str, Any], values: dict[str, Any],
           insert_only: dict[str, Any] | None = None) -> str:
    """Update the row identified by `key` (a unique key of the table) or insert it. Returns 'inserted'/'updated'."""
    conditions = [table.c[k] == v for k, v in key.items()]
    existing = db.execute(select(*[table.c[k] for k in key]).where(*conditions)
                          .with_hint(table, _LOCK_HINT, dialect_name="mssql")).first()
    if existing is not None:
        if values:
            db.execute(update(table).where(*conditions).values(**values))
        return "updated"
    db.execute(insert(table).values(**key, **values, **(insert_only or {})))
    return "inserted"


def insert_returning_id(db: Session, table: Table, values: dict[str, Any]) -> int:
    return db.execute(insert(table).values(**values).returning(table.c.id)).scalar_one()


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def from_json(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def truncate(value: Any, length: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:length] if text else None


class PersistStats(dict):
    """Counter of persistence outcomes, returned to clients in `meta.persisted`."""

    def add(self, outcome: str, count: int = 1) -> None:
        self[outcome] = self.get(outcome, 0) + count
