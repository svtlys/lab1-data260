"""
database connection and session setup.
"""

from collections.abc import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# build the database URL safely from the environment settings
database_url = URL.create(
    drivername="mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
)


# create the engine that manages communication with MySQL
engine = create_engine(
    database_url,
    pool_pre_ping=True,
)


# create database sessions for individual API requests
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """base class for all SQLAlchemy database models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """provide one database session and close it after the request."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()