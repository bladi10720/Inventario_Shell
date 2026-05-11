from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine


_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match((slug or "").strip()))


def lookup_pin(*, engine: Engine, pin: str) -> tuple[str, str, bool] | None:
    """Returns (role_slug, display_name, is_admin) if PIN matches an active DB credential."""
    p = (pin or "").strip()
    if not p:
        return None
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT r.slug, r.display_name, r.is_admin
                FROM role_pins rp
                JOIN roles r ON r.id = rp.role_id
                WHERE rp.pin = :pin AND rp.active AND r.active
                """
            ),
            {"pin": p},
        ).mappings().first()
    if not row:
        return None
    return (str(row["slug"]), str(row["display_name"]), bool(row["is_admin"]))


@dataclass(frozen=True)
class RoleRow:
    id: int
    slug: str
    display_name: str
    is_admin: bool
    active: bool


def list_roles(*, engine: Engine, include_inactive: bool = False) -> list[RoleRow]:
    where = "" if include_inactive else "WHERE r.active = TRUE"
    sql = f"""
    SELECT r.id, r.slug, r.display_name, r.is_admin, r.active
    FROM roles r
    {where}
    ORDER BY r.display_name
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
    return [
        RoleRow(
            id=int(r["id"]),
            slug=str(r["slug"]),
            display_name=str(r["display_name"]),
            is_admin=bool(r["is_admin"]),
            active=bool(r["active"]),
        )
        for r in rows
    ]


def insert_role(*, engine: Engine, slug: str, display_name: str, is_admin: bool) -> int:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO roles (slug, display_name, is_admin, active)
                VALUES (:slug, :display_name, :is_admin, TRUE)
                RETURNING id
                """
            ),
            {"slug": slug.strip(), "display_name": display_name.strip(), "is_admin": is_admin},
        ).first()
    assert row is not None
    return int(row[0])


def update_role(
    *,
    engine: Engine,
    role_id: int,
    display_name: str,
    is_admin: bool,
    active: bool,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE roles
                SET display_name = :display_name,
                    is_admin = :is_admin,
                    active = :active
                WHERE id = :id
                """
            ),
            {
                "id": role_id,
                "display_name": display_name.strip(),
                "is_admin": is_admin,
                "active": active,
            },
        )


@dataclass(frozen=True)
class PinRow:
    id: int
    role_id: int
    pin: str
    label: str | None
    active: bool


def list_pins_for_role(*, engine: Engine, role_id: int) -> list[PinRow]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, role_id, pin, label, active
                FROM role_pins
                WHERE role_id = :role_id
                ORDER BY active DESC, id
                """
            ),
            {"role_id": role_id},
        ).mappings().all()
    return [
        PinRow(
            id=int(r["id"]),
            role_id=int(r["role_id"]),
            pin=str(r["pin"]),
            label=str(r["label"]) if r["label"] is not None else None,
            active=bool(r["active"]),
        )
        for r in rows
    ]


def insert_pin(*, engine: Engine, role_id: int, pin: str, label: str | None) -> None:
    p = (pin or "").strip()
    if not p:
        raise ValueError("PIN vacío.")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO role_pins (role_id, pin, label, active)
                VALUES (:role_id, :pin, :label, TRUE)
                """
            ),
            {"role_id": role_id, "pin": p, "label": (label or "").strip() or None},
        )


def set_pin_active(*, engine: Engine, pin_id: int, active: bool) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE role_pins SET active = :active WHERE id = :id"),
            {"id": pin_id, "active": active},
        )
