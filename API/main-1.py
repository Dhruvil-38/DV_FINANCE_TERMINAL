"""
DV Finance Platform — Backend API

Role-based (admin / analyst / staff / client) trading-firm platform backend.
JWT auth, SQLite persistence (swap DATABASE_URL for Postgres in production),
Pandas/NumPy-driven analytics.

Run:
    uvicorn main:app --reload --port 8000
"""

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import seed
from routers import (
    auth_router, dashboard_router, market_router, news_router,
    analytics_router,
)
from engagement import (
    clients_router, research_router, tasks_router,
    documents_router, reports_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("dvfinance")

DEFAULT_ALLOWED_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DV_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",")
    if origin.strip()
]
if "*" in ALLOWED_ORIGINS:
    raise RuntimeError(
        "DV_ALLOWED_ORIGINS must list explicit frontend origins; '*' would let any "
        "site issue credentialed cross-origin requests."
    )

EXPOSE_DOCS = os.environ.get("DV_EXPOSE_DOCS", "").lower() in ("1", "true", "yes")

app = FastAPI(
    title="DV Finance Platform API",
    description="Backend for the DV Finance client & firm portal.",
    version="1.0.0",
    docs_url="/docs" if EXPOSE_DOCS else None,
    redoc_url="/redoc" if EXPOSE_DOCS else None,
    openapi_url="/openapi.json" if EXPOSE_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def on_startup():
    try:
        seed.run()
    except Exception:
        # Starting up with an unusable database only defers the failure to the
        # first request, with no trace of the real cause.
        logger.exception("Database initialisation failed — refusing to start")
        raise


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The database is unavailable — please retry."},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Unexpected server error."},
    )


app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(market_router.router)
app.include_router(news_router.router)
app.include_router(analytics_router.router)
app.include_router(clients_router.router)
app.include_router(research_router.router)
app.include_router(tasks_router.router)
app.include_router(documents_router.router)
app.include_router(reports_router.router)


@app.get("/api/health")
def health_check():
    return {"status": "OK", "service": "dv-finance-platform-api"}
