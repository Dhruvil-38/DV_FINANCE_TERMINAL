"""
DV Finance Platform — Backend API

Role-based (admin / analyst / staff / client) trading-firm platform backend.
JWT auth, SQLite persistence (swap DATABASE_URL for Postgres in production),
Pandas/NumPy-driven analytics.

Run:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import seed
from routers import (
    auth_router, dashboard_router, market_router, news_router,
    analytics_router, clients_router, research_router, tasks_router,
    documents_router, reports_router,
)

app = FastAPI(
    title="DV Finance Platform API",
    description="Backend for the DV Finance client & firm portal.",
    version="1.0.0",
)

# Tighten allow_origins to your actual frontend origin(s) before production deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    seed.run()


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
