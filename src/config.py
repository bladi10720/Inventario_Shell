from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    pin_admin: str
    pin_operador: str


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    pin_admin = os.getenv("PIN_ADMIN", "").strip()
    pin_operador = os.getenv("PIN_OPERADOR", "").strip()

    if not database_url:
        raise RuntimeError("Missing required env var: DATABASE_URL")
    if not pin_admin:
        raise RuntimeError("Missing required env var: PIN_ADMIN")
    if not pin_operador:
        raise RuntimeError("Missing required env var: PIN_OPERADOR")

    return Settings(
        database_url=database_url,
        pin_admin=pin_admin,
        pin_operador=pin_operador,
    )

