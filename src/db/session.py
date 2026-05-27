from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import settings


def get_engine():
    """Create a SQLAlchemy Engine from the configured database URL."""

    url = settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = get_engine()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Yield a database session for request-scoped usage."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

