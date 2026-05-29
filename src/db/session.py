from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import settings


def get_engine():
    """Create a SQLAlchemy Engine from the configured PostgreSQL database URL."""

    return create_engine(settings.database_url, pool_pre_ping=True)


engine = get_engine()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Yield a database session for request-scoped usage."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

