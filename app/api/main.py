"""FastAPI application entry point.

Exposes health, research, article, draft, publishing, OAuth and (optional)
Telegram-webhook endpoints. Admin/publishing routes require an API key; OAuth
callbacks validate signed state. CORS is restricted.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import core, drafts, oauth, telegram_webhook
from app.config import get_settings

logging.basicConfig(level=get_settings().log_level)

app = FastAPI(
    title="AEVRIX Content Intelligence Engine",
    version=__version__,
    description="Portable AI content research, drafting, approval and publishing.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core.router)
app.include_router(drafts.router)
app.include_router(oauth.router)
app.include_router(telegram_webhook.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("aevrix.api").exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"name": "AEVRIX Content Intelligence Engine", "version": __version__,
            "docs": "/docs"}
