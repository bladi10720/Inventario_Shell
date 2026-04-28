from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class Product:
    code: str
    name: str
    category: str
    active: bool


def get_product(*, engine: Engine, code: str) -> Product | None:
    code = str(code).strip()
    if not code:
        return None
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT code, name, category, active
                FROM products
                WHERE code = :code
                """
            ),
            {"code": code},
        ).mappings().first()
    if not row:
        return None
    return _row_to_product(row)


def upsert_products(*, engine: Engine, rows: list[dict[str, Any]]) -> tuple[int, int]:
    """
    Upserts products.

    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0
    if not rows:
        return (0, 0)

    stmt = text(
        """
        INSERT INTO products (code, name, category, active, updated_at)
        VALUES (:code, :name, :category, TRUE, NOW())
        ON CONFLICT (code)
        DO UPDATE SET
          name = EXCLUDED.name,
          category = EXCLUDED.category,
          active = TRUE,
          updated_at = NOW()
        """
    )

    with engine.begin() as conn:
        for r in rows:
            # We can't easily know whether it was insert vs update without extra queries.
            # Do a cheap existence check for accurate counts (small dataset).
            existing = conn.execute(
                text("SELECT 1 FROM products WHERE code = :code"),
                {"code": r["code"]},
            ).first()
            conn.execute(stmt, r)
            if existing:
                updated += 1
            else:
                inserted += 1

    return (inserted, updated)


def list_categories(*, engine: Engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT category
                FROM products
                WHERE active = TRUE
                ORDER BY category
                """
            )
        ).scalars().all()
    return [r for r in rows if r]


def search_products(*, engine: Engine, query: str, category: str | None = None) -> list[Product]:
    q = (query or "").strip()
    params: dict[str, Any] = {}

    where = ["active = TRUE"]
    if category and category != "Todas":
        where.append("category = :category")
        params["category"] = category

    if q:
        # Exact code match first, but allow contains on name for admin convenience.
        where.append("(code = :q OR name ILIKE :like)")
        params["q"] = q
        params["like"] = f"%{q}%"

    sql = f"""
    SELECT code, name, category, active
    FROM products
    WHERE {' AND '.join(where)}
    ORDER BY category, name
    LIMIT 500
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [_row_to_product(r) for r in rows]


def update_product(*, engine: Engine, code: str, name: str, category: str, active: bool) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE products
                SET name = :name,
                    category = :category,
                    active = :active,
                    updated_at = NOW()
                WHERE code = :code
                """
            ),
            {"code": code, "name": name, "category": category, "active": active},
        )


def _row_to_product(row: Any) -> Product:
    return Product(
        code=str(row["code"]),
        name=str(row["name"]),
        category=str(row["category"]),
        active=bool(row["active"]),
    )

