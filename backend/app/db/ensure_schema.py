"""
Additive schema drift repair.

create_all (run by the entrypoint) creates missing TABLES but never adds
missing COLUMNS to existing ones - so a model change like "add users.plan"
would make every query against the old table fail with
"Unknown column" until someone ran a manual ALTER (this actually happened
on staging, 2026-09-14).

This module closes that gap: for every table/column in the ORM metadata
that is missing from the live database, it issues an ALTER TABLE ... ADD
COLUMN compiled for the runtime dialect. Works on any SQLAlchemy-supported
engine (MariaDB, MySQL, PostgreSQL, SQLite) - no version-specific SQL.

Known limitation: indexes/unique constraints on NEW columns are not
created here (create_all only does them with the table). Columns added
with index=True/unique=True need a manual CREATE INDEX.

NOT NULL columns must carry a server_default in the model (or be added to
an empty table), otherwise the ALTER fails on a populated table; failures
are logged loudly with the exact manual statement instead of crashing the
container.
"""

import logging
import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn

logger = logging.getLogger(__name__)


def _sync_engine() -> Engine:
    """Sync engine from DATABASE_URL (async URLs converted, like the entrypoint)."""
    db_url = (
        os.getenv("DATABASE_URL", "")
        .replace("aiomysql", "pymysql")
        .replace("asyncpg", "postgresql+psycopg2")
    )
    return create_engine(db_url)


def ensure_columns(engine: Engine | None = None) -> int:
    """
    Add ORM columns missing from existing tables. Returns the number added.

    Missing tables are NOT handled here (that's create_all's job); only
    tables that already exist in the database are inspected.
    """
    engine = engine or _sync_engine()

    import app.models  # noqa: F401 - imports register all models on Base
    from app.db.base import Base

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    preparer = engine.dialect.identifier_preparer

    added = 0
    failed = 0
    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        if table.name not in existing_tables:
            continue  # fresh table - create_all already made it complete
        existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            ddl = str(CreateColumn(column).compile(dialect=engine.dialect))
            stmt = f"ALTER TABLE {preparer.quote(table.name)} ADD COLUMN {ddl}"
            try:
                with engine.begin() as conn:
                    conn.exec_driver_sql(stmt)
                added += 1
                logger.warning("SCHEMA: added missing column - %s", stmt)
            except Exception as exc:
                failed += 1
                logger.error(
                    "SCHEMA: could not add missing column %s.%s (%s). "
                    "Run this manually on the database: %s",
                    table.name,
                    column.name,
                    exc,
                    stmt,
                )
            if column.index or column.unique:
                logger.warning(
                    "SCHEMA: column %s.%s is indexed in the model but ALTER ADD COLUMN "
                    "does not create indexes - create the index manually if needed.",
                    table.name,
                    column.name,
                )

    if added or failed:
        logger.warning("SCHEMA: %d column(s) added, %d failed", added, failed)
    return added
