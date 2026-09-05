"""Contract Lab — study 010 review app. Entry point.

Run:  uv run uvicorn main:app --port 8300   (from this directory)
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

import api  # noqa: F401 (router)
from api import router as api_router
from db import Base, engine
from pages import router as pages_router

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Contract Lab", version="0.1.0")
app.include_router(api_router)
app.include_router(pages_router)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
