"""Database engine/session for Contract Lab."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

APP_DIR = Path(__file__).resolve().parent
STUDY_DIR = APP_DIR.parent.parent
DATA_DIR = STUDY_DIR / "data"

DEFAULT_URL = "postgresql+psycopg://contractlab:contractlab@localhost:5433/contractlab"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
