import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator

# Get database URL from environment variable, default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./due_diligence.db")

# Create SQLAlchemy engine
# For SQLite, we need to set check_same_thread to False to allow multiple threads
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    # Enable JSON support for PostgreSQL
    json_serializer=lambda obj: str(obj) if isinstance(obj, (set, frozenset)) else obj,
)

# SessionLocal factory will create individual database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from models to create tables
from .models import Base

def create_db_and_tables() -> None:
    """Create all tables in the database. Should be called once at application startup."""
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator:
    """FastAPI dependency that provides a database session for each request.
    
    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 