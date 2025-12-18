import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=True,              # Show SQL logs (optional)
    pool_size=5,            # Connection pool size
    max_overflow=10,        # Extra connections
    future=True             # SQLAlchemy 2.0 mode
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

def get_db():
    """
    Create a database session.
    Yields:
    Session: The database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()