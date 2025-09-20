import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Resolve an absolute path for the default SQLite DB to avoid CWD-dependent files
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_DB_PATH}"

# Allow override via DATABASE_URL; otherwise use the absolute sqlite path
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

# For SQLite, need check_same_thread False for FastAPI multi-threaded access
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
