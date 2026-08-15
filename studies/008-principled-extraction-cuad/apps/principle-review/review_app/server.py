from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from .service import Config, Service

STATIC = Path(__file__).parent / "static"


def create_app(config: Config) -> FastAPI:
    service = Service(config)
    service.sync_from_disk()
    app = FastAPI(title="principle-review", docs_url=None, redoc_url=None)
    app.state.service = service

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/state")
    def state() -> JSONResponse:
        return JSONResponse(service.state())

    @app.post("/api/reimport")
    def reimport() -> JSONResponse:
        return JSONResponse(service.sync_from_disk())

    @app.post("/api/review")
    def review(payload: dict[str, Any]) -> JSONResponse:
        try:
            return JSONResponse(service.save_review(payload))
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/draft")
    def draft(payload: dict[str, Any]) -> JSONResponse:
        return JSONResponse(service.save_draft(payload))

    @app.post("/api/export")
    def export(payload: dict[str, Any] | None = None) -> JSONResponse:
        return JSONResponse(service.export((payload or {}).get("path")))

    @app.get("/api/history/{record_id}")
    def history(record_id: str) -> JSONResponse:
        return JSONResponse({"history": service.history(record_id)})

    return app
