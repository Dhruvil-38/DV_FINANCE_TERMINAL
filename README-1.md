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

# 2. Configure the JWT signing secret (required — there is no built-in default)
export DV_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
# ...or, for a throwaway run with a random per-process secret:
# export DV_ALLOW_EPHEMERAL_JWT_SECRET=1

# 3. Start the API — creates dv_platform.db and seeds demo data on first run
cd api
uvicorn main:app --reload --port 8000

# 4. In a second terminal, serve the frontend
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

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                          # runs API/tests
pytest --cov=API --cov-report=term-missing      # with a coverage report
```

Tests run against an in-memory SQLite database (`DATABASE_URL` is overridden in
`API/tests/conftest.py`), so they never touch `dv_platform.db` or the `uploads/` directory.

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
- Pydantic validates and coerces every request body before it touches the database;
  enum-like fields (statuses, tiers, categories, direction) are `Literal`-constrained
  and every free-text field is length-capped
- JWT signing secret is read from `DV_JWT_SECRET` with **no fallback** — the app
  refuses to start without one
- CORS allow-list comes from `DV_ALLOWED_ORIGINS` (defaults to the local dev
  frontend); `"*"` is rejected outright since credentials are allowed
- Interactive docs (`/docs`, `/redoc`, `/openapi.json`) are off unless
  `DV_EXPOSE_DOCS=1`
- Uploads are extension-allow-listed, size-capped (20 MB), and written under a
  random server-generated name, so a client-supplied filename can never traverse
  out of `api/uploads/` or overwrite an existing file
- Failed logins are throttled per IP + email (`DV_LOGIN_MAX_ATTEMPTS`,
  `DV_LOGIN_WINDOW_SECONDS`) — per-process, so put a shared limiter in front when
  running multiple workers
- All server-supplied values are HTML-escaped before being rendered in the SPA
- CSV exports neutralise spreadsheet formula injection
- Demo accounts are only seeded on the default local SQLite database (override
  with `DV_SEED_DEMO_DATA`)

### Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DV_JWT_SECRET` | yes | — | JWT signing key, min 32 chars |
| `DV_ALLOW_EPHEMERAL_JWT_SECRET` | no | off | Dev-only: random per-process secret |
| `DV_ALLOWED_ORIGINS` | no | `http://localhost:5500,http://127.0.0.1:5500` | Comma-separated CORS allow-list |
| `DV_EXPOSE_DOCS` | no | off | Serve `/docs`, `/redoc`, `/openapi.json` |
| `DV_LOGIN_MAX_ATTEMPTS` / `DV_LOGIN_WINDOW_SECONDS` | no | `10` / `300` | Failed-login throttle |
| `DV_SEED_DEMO_DATA` | no | on for default SQLite DB | Seed demo users/content |
| `DATABASE_URL` | no | `sqlite:///./dv_platform.db` | SQLAlchemy DSN |

**Still to do before a real production deploy:**
- Serve everything over HTTPS only
- Swap SQLite for Postgres/MySQL for concurrent production traffic (`DATABASE_URL` env var — no code changes needed, SQLAlchemy handles it)
- Move the JWT out of `localStorage` and into an `httpOnly` cookie to reduce XSS blast radius
- Move the login throttle to a shared store (Redis) or an edge/WAF rule once more than one worker is running
- Add refresh-token rotation if you want sessions longer than 8 hours without re-prompting for a password
- Put a real virus/content-type scan in front of `/api/documents/upload` (the extension allow-list is not a content check)
- `python-jose` transitively pulls `ecdsa`, which has an unfixed Minerva timing
  advisory (PYSEC-2026-1325). Not exploitable here — tokens are signed with HS256,
  so no ECDSA/ECDH code path runs — but switching to `PyJWT` would drop the
  dependency entirely
- Remove the demo-account autofill buttons from the login screen — the passwords are hardcoded in `index.html`

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
