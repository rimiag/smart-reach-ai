#!/usr/bin/env python
"""
Regenerate database/schema_full.sql from the ORM models.

The generated file is the manual fallback for environments where the
entrypoint's automatic schema check (create_all + ensure_schema) cannot
run. Run this after EVERY model change and commit the result, so the SQL
file always matches the code:

    cd backend
    .venv/Scripts/python generate_schema_sql.py      (Windows)
    python generate_schema_sql.py                    (Linux/Mac)

The DDL is compiled by SQLAlchemy's MySQL dialect, which is valid on BOTH
MySQL 8.x and MariaDB 10.1+ (MariaDB is a MySQL fork and accepts the
MySQL table-option syntax; the <=191-char indexed strings keep it under
MariaDB 10.1's 767-byte index limit as well).
"""

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "database"
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.dialects.mysql import base as mysql_dialects  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

import app.models  # noqa: F401,E402 - imports register all models on Base
from app.db.base import Base  # noqa: E402

MYSQL_DIALECT = mysql_dialects.MySQLDialect()


def compile_table(table, dialect) -> str:
    """CREATE TABLE IF NOT EXISTS statement for one table, indexes included."""
    table.kwargs.setdefault("mysql_engine", "InnoDB")
    table.kwargs.setdefault("mysql_charset", "utf8mb4")
    ddl = str(CreateTable(table).compile(dialect=dialect)).strip()

    # MySQL's CreateTable renders constraints but NOT secondary indexes
    # (those would become separate CREATE INDEX statements, which have no
    # IF NOT EXISTS on MySQL and would break the re-runnable design).
    # Append them as inline KEY clauses instead - skipped together with the
    # table on re-runs, and valid on MySQL 8 + MariaDB.
    index_clauses = []
    for ix in sorted(table.indexes, key=lambda i: i.name):
        prep = dialect.identifier_preparer
        cols = ", ".join(prep.quote(c.name) for c in ix.columns)
        prefix = "UNIQUE KEY" if ix.unique else "KEY"
        index_clauses.append(f"\t{prefix} {prep.quote(ix.name)} ({cols})")
    if index_clauses:
        closing = ddl.rfind(")")
        body = ddl[:closing].rstrip().rstrip(",")
        ddl = body + ",\n" + ",\n".join(index_clauses) + "\n" + ddl[closing:]

    # CreateTable has no IF NOT EXISTS switch - add it deterministically.
    ddl = ddl.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
    return ddl + ";"


def build_script(dialect) -> str:
    """Full schema as one SQL string, FK-safe order, re-runnable."""
    lines = [
        "-- =========================================================================",
        "-- SmartReach AI - full database schema",
        f"-- AUTO-GENERATED from the ORM models on {date.today().isoformat()} - DO NOT EDIT BY HAND.",
        "-- Regenerate after model changes:  cd backend && python generate_schema_sql.py",
        "--",
        "-- Re-runnable: CREATE TABLE IF NOT EXISTS + FK checks disabled during run.",
        "-- Compatible with MySQL 8.x and MariaDB 10.1+ (utf8mb4, 191-char index caps).",
        "-- Usage: mysql -u <user> -p <database> < database/schema_full.sql",
        "-- See database/README.md for when and how to run this.",
        "-- =========================================================================",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]
    for table in Base.metadata.sorted_tables:
        lines.append(f"-- ---- {table.name} " + "-" * max(1, 60 - len(table.name)))
        lines.append(compile_table(table, dialect))
        lines.append("")
    lines += ["SET FOREIGN_KEY_CHECKS = 1;", ""]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    mysql_sql = build_script(MYSQL_DIALECT)

    out = OUT_DIR / "schema_full.sql"
    out.write_text(mysql_sql, encoding="utf-8", newline="\n")
    print(f"OK: wrote {out} ({len(mysql_sql)} chars)")

    tables = [t for t in Base.metadata.sorted_tables]
    print(f"Tables included ({len(tables)}):", ", ".join(t.name for t in tables))


if __name__ == "__main__":
    main()
