import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env file
load_dotenv()

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Build database URL from environment variables."""
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    dbname = os.getenv("DB_NAME")

    if not all([user, password, host, port, dbname]):
        raise ValueError(
            "Database connection details are missing. Check your environment variables "
            "for DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, and DB_NAME."
        )

    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
    return _engine


def get_session():
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()
