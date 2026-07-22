"""Database engine, session factory, and declarative base.

Provides the SQLAlchemy engine configured from ``DATABASE_URL`` environment
variable, a ``SessionLocal`` sessionmaker, the ``Base`` declarative base for
all ORM models, and the ``get_db`` FastAPI dependency.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/store_catalog",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


def get_db() -> Generator[SessionLocal, None, None]:
    """Yield a database session and ensure it closes after use.

    This is a FastAPI dependency that manages the lifecycle of each request's
    database session automatically.

    Yields:
        An open SQLAlchemy session bound to the application engine.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
