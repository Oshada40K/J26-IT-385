# SHARED FILE - controlled by the group leader.
# SQLAlchemy setup. The engine is created lazily by SQLAlchemy: no connection
# is opened until a session actually runs a query, so the API starts even if
# PostgreSQL is not available.

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL


def _with_psycopg2_driver(url: str) -> str:
    # SQLAlchemy 2.1+ maps "postgresql://" to the psycopg (v3) driver by default.
    # This project uses psycopg2-binary, so select that driver explicitly.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


engine = create_engine(_with_psycopg2_driver(DATABASE_URL), pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
