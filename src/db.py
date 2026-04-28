from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import load_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = load_settings()
    # Neon requires SSL; most DATABASE_URL already includes sslmode=require
    # but we keep it as-is and let SQLAlchemy pass it through.
    return create_engine(settings.database_url, pool_pre_ping=True)

