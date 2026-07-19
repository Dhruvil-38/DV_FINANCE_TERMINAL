# DV Finance Platform

A role-based client & firm portal for a trading/research firm — terminal-style dashboard,
market module, news, analytics, client management, tasks, and document sharing.

- **Backend:** FastAPI + SQLAlchemy (SQLite by default, swap to Postgres for production) + JWT auth + Pandas/NumPy analytics
- **Frontend:** Vanilla JS SPA — no framework, no build step, no external chart library

## Project structure

```
dv-platform/
├── requirements.txt
├── api/
│   ├── main.py               # app entrypoint, mounts all routers
│   ├── database.py           # SQLAlchemy engine/session
│   ├── models.py             # ORM models
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── auth.py                # password hashing, JWT, role guards
│   ├── seed.py                 # creates tables + demo data (idempotent)
│   └── routers/
│       ├── auth_router.py        # login, /me
│       ├── dashboard_router.py   # summary cards, notifications, activity feed
│       ├── market_router.py      # watchlist + trade calls
│       ├── news_router.py        # market / company / firm news
│       ├── analytics_router.py   # win rate, accuracy, monthly & sector perf, engagement
│       ├── clients_router.py     # client profiles (firm-only)
│       ├── research_router.py    # research notes
│       ├── tasks_router.py       # task management (firm-only)
│       ├── documents_router.py   # document metadata + real file upload
│       └── reports_router.py     # CSV export
└── frontend/
    ├── index.html             # login screen + app shell (8 modules)
    ├── styles.css              # design system
    └── app.js                   # auth, routing, rendering, lightweight charts
```

## Run it locally

```bash
# 1. Install backend dependencies
pip install -r requirements.txt

# 2. Start the API — creates dv_platform.db and seeds demo data on first run
cd api
uvicorn main:app --reload --port 8000

# 3. In a second terminal, serve the frontend
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500`. The frontend auto-detects the local dev setup and points
at `http://localhost:8000/api` — see `API_BASE` at the top of `app.js` if you deploy the
two halves elsewhere (adjust it, or put both behind one reverse-proxy origin with `/api`
forwarded to the backend, which is the recommended production setup).

## Demo accounts (seeded automatically)

| Role | Email | Password |
|---|---|---|
| Admin | admin@dvfinance.in | Admin@123 |
| Analyst | analyst@dvfinance.in | Analyst@123 |
| Staff | staff@dvfinance.in | Staff@123 |
| Client | client@dvfinance.in | Client@123 |

The login screen has one-click buttons that autofill these for you.

## Roles & permissions

| Module | Admin | Analyst | Staff | Client |
|---|:---:|:---:|:---:|:---:|
| Dashboard | ✅ | ✅ | ✅ | ✅ (own portfolio view) |
| Market — view | ✅ | ✅ | ✅ | ✅ |
| Market — create/edit calls & watchlist | ✅ | ✅ | ❌ | ❌ |
| News — view | ✅ | ✅ | ✅ | ✅ |
| News — publish | ✅ | ✅ | ✅ | ❌ |
| Analytics — win rate / accuracy / monthly / sector / call history | ✅ | ✅ | ✅ | ✅ |
| Analytics — client engagement | ✅ | ✅ | ✅ | ❌ |
| Clients | ✅ | ✅ | ✅ | ❌ |
| Research notes — view | ✅ | ✅ | ✅ | own notes only |
| Research notes — create | ✅ | ✅ | ✅ | ❌ |
| Tasks | ✅ | ✅ | ✅ | ❌ |
| Documents — view | ✅ | ✅ | ✅ | own + General only |
| Documents — upload | ✅ | ✅ | ✅ | ❌ |
| Reports export | ✅ | ✅ | ✅ | calls & performance only |

Every one of these is enforced **server-side** (`require_role(...)` dependencies in each
router) — the frontend hiding UI elements is a convenience, not the security boundary.

## Security notes — what's already in place, and what to change before going live

**Already implemented:**
- Passwords hashed with bcrypt (never stored or logged in plaintext)
- Stateless JWT auth (8-hour expiry), verified on every protected request
- Role-based access control enforced at the API layer, not just hidden in the UI
- Parameterized queries throughout via SQLAlchemy ORM (no raw SQL string building)
- Pydantic validates and coerces every request body before it touches the database

**Before a real production deploy:**
- Move `SECRET_KEY` (in `auth.py`) out of source and into an environment variable / secrets manager — the checked-in value is a dev default only
- Set `CORSMiddleware(allow_origins=[...])` to your actual frontend origin(s) instead of `"*"`
- Serve everything over HTTPS only
- Swap SQLite for Postgres/MySQL for concurrent production traffic (`DATABASE_URL` env var — no code changes needed, SQLAlchemy handles it)
- Consider moving the JWT out of `localStorage` and into an `httpOnly` cookie to reduce XSS blast radius
- Add rate limiting on `/api/auth/login` to slow down credential-stuffing attempts
- Add refresh-token rotation if you want sessions longer than 8 hours without re-prompting for a password
- Put a real virus/file-type scan in front of `/api/documents/upload` before accepting arbitrary files in production

## Data — what's real vs. seeded

Everything is stored in a real SQLite database (`api/dv_platform.db`), not in-memory —
so it persists across restarts and is a genuine starting point for real data integration.
The **seed script** (`api/seed.py`) only fabricates demo content (clients, trade calls,
news, tasks) the first time the database is empty, so you can safely delete
`dv_platform.db` to reset to a fresh demo state, or start entering real data immediately
and never touch the seed again.

## Extending this

- **Live prices:** replace the static `last_price` / `day_change_pct` fields in
  `WatchlistItem` with a scheduled job or websocket feed from your market data provider.
- **Real broker execution:** the `TradeCall` model and `/api/market/calls` endpoints
  are research-call tracking, not order routing — wire a separate execution service
  if you need actual order placement.
- **Notifications:** currently polled on dashboard load; swap for websockets/SSE if you
  want push-style delivery.
