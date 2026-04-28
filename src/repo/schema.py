from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine


def apply_schema(*, engine: Engine) -> None:
    sql_path = Path(__file__).resolve().parents[1] / "models.sql"
    sql = sql_path.read_text(encoding="utf-8")

    # models.sql contains multiple statements; SQLAlchemy can execute them as-is on Postgres
    # when passed via a raw connection.
    with engine.begin() as conn:
        for statement in _split_sql_statements(sql):
            stmt = statement.strip()
            if not stmt:
                continue
            conn.execute(text(stmt))


def _split_sql_statements(sql: str) -> list[str]:
    # Minimal splitter for our DDL file (no procedural blocks).
    parts: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        current.append(line)
        if ";" in line:
            joined = "\n".join(current)
            for chunk in joined.split(";"):
                parts.append(chunk)
            current = []
    if current:
        parts.append("\n".join(current))
    return parts

