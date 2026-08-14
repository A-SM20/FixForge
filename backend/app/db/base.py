"""SQLAlchemy declarative base.

Single base class for all ORM models. Keeps model registration
in one place so Alembic's autogenerate can discover all tables.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass
