from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.engine import Engine

MovementType = Literal["IN", "OUT", "ADJUST"]
Role = Literal["admin", "operador"]


@dataclass(frozen=True)
class StockRow:
    code: str
    name: str
    category: str
    stock: int


def get_stock_by_code(*, engine: Engine, code: str) -> int | None:
    code = str(code).strip()
    if not code:
        return None

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  COALESCE(SUM(CASE WHEN m.type = 'IN' THEN m.qty ELSE 0 END), 0) -
                  COALESCE(SUM(CASE WHEN m.type = 'OUT' THEN m.qty ELSE 0 END), 0) AS stock
                FROM products p
                LEFT JOIN movements m ON m.product_code = p.code
                WHERE p.code = :code
                GROUP BY p.code
                """
            ),
            {"code": code},
        ).first()
    if not row:
        return None
    return int(row[0])


def insert_movement(*, engine: Engine, movement_type: MovementType, movement_date: date, product_code: str, qty: int, actor_role: Role, note: str | None = None) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO movements (type, movement_date, product_code, qty, actor_role, note)
                VALUES (:type, :movement_date, :product_code, :qty, :actor_role, :note)
                """
            ),
            {
                "type": movement_type,
                "movement_date": movement_date,
                "product_code": str(product_code).strip(),
                "qty": int(qty),
                "actor_role": actor_role,
                "note": note,
            },
        )


def ensure_no_active_out_closure(*, engine: Engine, movement_date: date) -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT status, actor_role, created_at
                FROM daily_out_closures
                WHERE date = :date
                """
            ),
            {"date": movement_date},
        ).mappings().first()
    if row and row["status"] == "active":
        raise RuntimeError(
            f"Ya existe una carga activa para {movement_date} (rol: {row['actor_role']}, creada: {row['created_at']})."
        )


def create_out_closure(*, engine: Engine, movement_date: date, actor_role: Role) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO daily_out_closures (date, actor_role, status)
                VALUES (:date, :actor_role, 'active')
                ON CONFLICT (date)
                DO UPDATE SET
                  actor_role = EXCLUDED.actor_role,
                  status = 'active',
                  voided_at = NULL,
                  created_at = NOW()
                """
            ),
            {"date": movement_date, "actor_role": actor_role},
        )


def void_out_closure(*, engine: Engine, movement_date: date) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE daily_out_closures
                SET status = 'voided', voided_at = NOW()
                WHERE date = :date AND status = 'active'
                """
            ),
            {"date": movement_date},
        )


def void_out_closure_and_delete_out_movements(*, engine: Engine, movement_date: date) -> int:
    """
    Voids the daily closure and deletes OUT movements for that movement_date.

    Returns number of OUT movement rows deleted.
    """
    with engine.begin() as conn:
        updated = conn.execute(
            text(
                """
                UPDATE daily_out_closures
                SET status = 'voided', voided_at = NOW()
                WHERE date = :date AND status = 'active'
                RETURNING date
                """
            ),
            {"date": movement_date},
        ).first()

        if updated is None:
            # nothing to void
            return 0

        deleted = conn.execute(
            text(
                """
                DELETE FROM movements
                WHERE type = 'OUT' AND movement_date = :date
                """
            ),
            {"date": movement_date},
        )
        return int(deleted.rowcount or 0)

def insert_daily_out_batch(
    *,
    engine: Engine,
    movement_date: date,
    items: list[dict[str, Any]],
    actor_role: Role,
) -> None:
    """
    items: [{product_code: str, qty: int}]
    """
    with engine.begin() as conn:
        # Claim the date first (prevents duplicates even under concurrency).
        claimed = conn.execute(
            text(
                """
                INSERT INTO daily_out_closures (date, actor_role, status)
                VALUES (:date, :actor_role, 'active')
                ON CONFLICT (date)
                DO UPDATE SET
                  actor_role = EXCLUDED.actor_role,
                  status = 'active',
                  voided_at = NULL,
                  created_at = NOW()
                WHERE daily_out_closures.status = 'voided'
                RETURNING status
                """
            ),
            {"date": movement_date, "actor_role": actor_role},
        ).first()
        if claimed is None:
            raise RuntimeError(f"Ya existe una carga activa para {movement_date}.")

        # Validate stock for each item
        for it in items:
            code = str(it["product_code"]).strip()
            want = int(it["qty"])
            stock = conn.execute(
                text(
                    """
                    SELECT
                      COALESCE(SUM(CASE WHEN m.type = 'IN' THEN m.qty ELSE 0 END), 0) -
                      COALESCE(SUM(CASE WHEN m.type = 'OUT' THEN m.qty ELSE 0 END), 0) AS stock
                    FROM products p
                    LEFT JOIN movements m ON m.product_code = p.code
                    WHERE p.code = :code
                    GROUP BY p.code
                    """
                ),
                {"code": code},
            ).scalar_one_or_none()
            if stock is None:
                raise RuntimeError(f"Código no existe: {code}")
            if int(stock) < want:
                raise RuntimeError(f"Stock insuficiente para {code}. Disponible {int(stock)}; solicitado {want}.")

        # Insert movements
        conn.execute(
            text(
                """
                INSERT INTO movements (type, movement_date, product_code, qty, actor_role)
                VALUES ('OUT', :movement_date, :product_code, :qty, :actor_role)
                """
            ),
            [
                {
                    "movement_date": movement_date,
                    "product_code": str(it["product_code"]).strip(),
                    "qty": int(it["qty"]),
                    "actor_role": actor_role,
                }
                for it in items
            ],
        )


def list_inventory(*, engine: Engine, category: str | None = None, only_active: bool = True) -> list[StockRow]:
    params: dict[str, Any] = {}
    where = []
    if only_active:
        where.append("p.active = TRUE")
    if category and category != "Todas":
        where.append("p.category = :category")
        params["category"] = category
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
    SELECT
      p.code,
      p.name,
      p.category,
      COALESCE(SUM(CASE WHEN m.type = 'IN' THEN m.qty ELSE 0 END), 0) -
      COALESCE(SUM(CASE WHEN m.type = 'OUT' THEN m.qty ELSE 0 END), 0) AS stock
    FROM products p
    LEFT JOIN movements m ON m.product_code = p.code
    {where_sql}
    GROUP BY p.code, p.name, p.category
    ORDER BY p.category, p.name
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [
        StockRow(code=str(r["code"]), name=str(r["name"]), category=str(r["category"]), stock=int(r["stock"]))
        for r in rows
    ]


def list_low_stock(*, engine: Engine, threshold: int = 2, category: str | None = None) -> list[StockRow]:
    params: dict[str, Any] = {"threshold": threshold}
    where = ["p.active = TRUE"]
    if category and category != "Todas":
        where.append("p.category = :category")
        params["category"] = category

    sql = f"""
    SELECT
      p.code,
      p.name,
      p.category,
      COALESCE(SUM(CASE WHEN m.type = 'IN' THEN m.qty ELSE 0 END), 0) -
      COALESCE(SUM(CASE WHEN m.type = 'OUT' THEN m.qty ELSE 0 END), 0) AS stock
    FROM products p
    LEFT JOIN movements m ON m.product_code = p.code
    WHERE {' AND '.join(where)}
    GROUP BY p.code, p.name, p.category
    HAVING (
      COALESCE(SUM(CASE WHEN m.type = 'IN' THEN m.qty ELSE 0 END), 0) -
      COALESCE(SUM(CASE WHEN m.type = 'OUT' THEN m.qty ELSE 0 END), 0)
    ) < :threshold
    ORDER BY stock ASC, p.category, p.name
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [
        StockRow(code=str(r["code"]), name=str(r["name"]), category=str(r["category"]), stock=int(r["stock"]))
        for r in rows
    ]

