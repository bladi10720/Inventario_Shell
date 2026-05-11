from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_schema_migrations(*, engine: Engine) -> None:
    """
    Idempotent fixes for existing databases: relax actor_role checks, add roles tables.
    Safe to call on every app startup.
    """
    stmts_roles = [
        """
        CREATE TABLE IF NOT EXISTS roles (
          id SERIAL PRIMARY KEY,
          slug TEXT NOT NULL UNIQUE,
          display_name TEXT NOT NULL,
          is_admin BOOLEAN NOT NULL DEFAULT FALSE,
          active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_roles_active ON roles (active)",
        """
        CREATE TABLE IF NOT EXISTS role_pins (
          id SERIAL PRIMARY KEY,
          role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
          pin TEXT NOT NULL,
          label TEXT,
          active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT uq_role_pins_pin UNIQUE (pin)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_role_pins_pin_active ON role_pins (pin) WHERE active = TRUE",
    ]
    with engine.begin() as conn:
        for stmt in stmts_roles:
            conn.execute(text(stmt.strip()))

        def _table_exists(table: str) -> bool:
            return bool(
                conn.execute(
                    text(
                        """
                        SELECT EXISTS (
                          SELECT 1 FROM information_schema.tables
                          WHERE table_schema = 'public' AND table_name = :t
                        )
                        """
                    ),
                    {"t": table},
                ).scalar()
            )

        if _table_exists("movements"):
            conn.execute(text("ALTER TABLE movements DROP CONSTRAINT IF EXISTS movements_actor_role_check"))
        if _table_exists("daily_out_closures"):
            conn.execute(text("ALTER TABLE daily_out_closures DROP CONSTRAINT IF EXISTS daily_out_closures_actor_role_check"))


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
    ensure_schema_migrations(engine=engine)


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

