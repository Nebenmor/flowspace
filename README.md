# Flowspace

Flowspace is a real-time collaborative task management platform for teams. Organizations spin up workspaces, assign and track tasks together, and see changes as they happen — no refreshing, no waiting. A production-grade API handles the heavy lifting (multi-tenant data isolation, live sync, background jobs, resilient webhook delivery) behind a clean, fast dashboard built for daily use.

**[Demo page](http://localhost:8000/demo) · [Swagger UI](http://localhost:8000/docs) · [Postman Collection](./docs/collab-tasks-api.postman_collection.json)**

---

## What's inside

This is a monorepo with two apps:

```
flowspace/
├── backend/     # FastAPI + PostgreSQL + Redis + Celery — the REST + WebSocket API
├── frontend/    # React + Vite dashboard that consumes the API
└── docs/        # Postman collection, etc.
```

Each app can be run and developed independently, but they're designed to work together: the frontend's dev server proxies API and WebSocket calls straight through to the backend, and in production the two are typically deployed as separate services that talk over HTTPS/WSS.

---

## Architecture highlights

- **Multi-tenant data isolation** — every query is scoped to an organization and workspace; no cross-tenant data leakage by design
- **Real-time sync** — WebSocket rooms per workspace broadcast task changes and presence instantly to all connected clients
- **Live dashboard** — the React frontend reflects task, presence, and notification changes as they happen, no manual refresh needed
- **Async throughout** — FastAPI + SQLAlchemy async + asyncpg; no blocking I/O on the main thread
- **Background job processing** — Celery handles email delivery, webhook dispatch, and scheduled reminders without blocking API responses
- **Resilient webhook delivery** — exponential backoff retry (1 min → 5 min → 30 min → 2 hr → 8 hr) with delivery logging and HMAC-SHA256 signature verification
- **Performant search** — PostgreSQL `tsvector` full-text search with GIN index and auto-update trigger; no Elasticsearch dependency
- **Layered caching** — Redis caches hot task list queries with workspace-scoped invalidation on every write
- **Rate limiting** — per-user request limits enforced at middleware level before any route handler runs; fails open if Redis is unavailable
- **Audit trail** — every task change is recorded with actor, timestamp, old value, and new value

---

## Tech stack

### Backend

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.133 |
| Database | PostgreSQL 15 (async via `asyncpg`) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Cache | Redis 7 |
| Task queue | Celery 5.6 + Redis broker |
| Real-time | WebSockets (native FastAPI) |
| Email | Resend API |
| Auth | JWT — `python-jose` |
| Validation | Pydantic v2 |
| Python | 3.13 |

### Frontend

| Layer | Technology |
|---|---|
| Framework | React 19 |
| Build tool | Vite 8 |
| Routing | React Router 7 |
| Data fetching / cache | TanStack Query 5 |
| HTTP client | Axios |
| Styling | Tailwind CSS 4 |
| Charts | Recharts |
| Icons | Lucide |

---

## Quick start

### Option A — Docker (backend only, recommended for the API)

Run the entire backend stack with one command. No local Python, PostgreSQL, or Redis installation needed.

```bash
git clone https://github.com/Nebenmor/flowspace.git
cd flowspace/backend
cp .env.example .env   # add your RESEND_API_KEY
docker-compose up --build
```

Services started:
- `api` — FastAPI at `http://localhost:8000`
- `db` — PostgreSQL at port `5432`
- `redis` — Redis at port `6379`
- `worker` — Celery worker
- `beat` — Celery Beat scheduler

Migrations run automatically on startup.

Then, in a separate terminal, start the frontend against it (see below).

### Option B — Manual setup

**Prerequisites:** Python 3.13, Node.js 18+, PostgreSQL, Redis

**1. Backend**

```bash
git clone https://github.com/Nebenmor/flowspace.git
cd flowspace/backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # fill in your credentials
docker-compose up -d redis      # or run Redis however you prefer

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Start background workers** (two separate terminals):

```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
celery -A app.workers.celery_app beat --loglevel=info
```

**2. Frontend**

```bash
cd flowspace/frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies `/api` and `/ws` requests to `http://localhost:8000` (configured in `vite.config.js`), so there's nothing extra to configure for local development — just make sure the backend is running first.

Open `http://localhost:5173`, register an account, and you're in.

---

## Backend environment variables

Copy `backend/.env.example` to `backend/.env` and fill in the values below.

| Variable | Description |
|---|---|
| `APP_NAME` | Application display name |
| `APP_VERSION` | API version string |
| `DEBUG` | `True` in development, `False` in production |
| `SECRET_KEY` | JWT signing secret — change in production |
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (default: 7) |
| `BASE_URL` | Public URL of the API (used in emails and links) |
| `RESEND_API_KEY` | API key from [resend.com](https://resend.com) |
| `EMAIL_FROM` | Sender address for transactional emails |
| `REDIS_URL` | Redis connection URL (e.g. `redis://localhost:6379/0`) |

### Frontend configuration

The frontend has no required environment variables for local development — `vite.config.js` proxies `/api` and `/ws` to `http://localhost:8000`. For a production build served separately from the API, put a reverse proxy (Nginx, Vercel rewrites, etc.) in front of the static build that forwards `/api` and `/ws` to your deployed backend, since the app calls the API using relative paths (`/api/v1/...`).

---

## Frontend overview

The frontend is a single-page dashboard with:

- **Auth** — login and registration screens backed by JWT access/refresh tokens (`AuthContext`)
- **Org & workspace switcher** — pick the active organization and workspace from the sidebar; the whole app scopes to that selection (`WorkspaceContext`)
- **Dashboard** — greeting, task summary stats, recent tasks, and a notifications panel
- **Tasks** — filterable task list, create/edit tasks, inline status changes, and a task detail modal
- **Analytics** — charts for task summary, completions over time, team productivity, and time-to-completion, powered by Recharts
- **Live updates** — a `useWebSocket` hook connects to the workspace's WebSocket room and invalidates the relevant TanStack Query caches whenever a `task.*` event arrives, so the UI updates without polling

### Frontend structure

```
frontend/
├── src/
│   ├── api/            # Axios wrappers per resource (auth, tasks, workspaces, ...)
│   ├── components/      # Sidebar, Layout, TaskCard, TaskDetailModal, TaskFilters, NotificationsPanel
│   ├── context/          # AuthContext, WorkspaceContext
│   ├── hooks/            # useWebSocket
│   ├── pages/            # Login, Register, Dashboard, Tasks, Analytics
│   ├── utils/            # taskDates helpers (overdue calculations, etc.)
│   ├── App.jsx           # Route definitions and providers
│   └── main.jsx          # Entry point
├── vite.config.js        # Dev server + /api and /ws proxy config
└── package.json
```

---

## API reference

All routes are versioned under `/api/v1`. Full interactive documentation at `/docs`.

| Resource | Base path |
|---|---|
| Auth | `/api/v1/auth` |
| Organizations | `/api/v1/organizations` |
| Workspaces | `/api/v1/organizations/{org_slug}/workspaces` |
| Members | `/api/v1/organizations/{org_slug}/workspaces/{workspace_slug}/members` |
| Tasks | `/api/v1/organizations/{org_slug}/workspaces/{workspace_slug}/tasks` |
| Subtasks | `.../tasks/{task_id}/subtasks` |
| Dependencies | `.../tasks/{task_id}/dependencies` |
| Labels | `.../workspaces/{workspace_slug}/labels` |
| Custom fields | `.../workspaces/{workspace_slug}/custom-fields` |
| Activities | `.../tasks/{task_id}/activity` |
| Invitations | `/api/v1/organizations/{org_slug}/invitations` |
| Notifications | `/api/v1/notifications` |
| Webhooks | `/api/v1/organizations/{org_slug}/webhooks` |
| Analytics | `.../workspaces/{workspace_slug}/analytics` |

### Task filtering and search

The task list endpoint supports rich filtering via query parameters:

```
GET /api/v1/.../tasks?status=in_progress&priority=high&assignee_id=...&is_overdue=true&search=pipeline&page=1&page_size=20
```

Search uses PostgreSQL full-text search (`tsvector`) — stemming-aware, GIN-indexed, and significantly faster than `ILIKE` at scale. Results are cached in Redis for 60 seconds and automatically invalidated on any write to the workspace.

### Analytics endpoints

```
GET .../analytics/tasks-summary          # total, completed, in-progress, todo, in-review, and overdue counts + completion rate
GET .../analytics/completed-over-time    # tasks completed per day (default: last 30 days, 7-365 configurable)
GET .../analytics/team-productivity      # completed vs open tasks per member
GET .../analytics/time-to-completion     # avg hours/days from creation to completion by priority
```

These same endpoints power the charts on the frontend's Analytics page.

---

## WebSocket events

Connect: `ws://localhost:8000/ws/{org_slug}/{workspace_slug}?token=<access_token>`

The frontend does this for you automatically via the `useWebSocket` hook once an organization and workspace are selected, connecting through Vite's dev proxy in development.

| Event | Direction | Payload |
|---|---|---|
| `user.joined` | server → client | `{ user_id }` |
| `user.left` | server → client | `{ user_id }` |
| `presence.sync` | server → client | `{ online_users: [...] }` |
| `presence.update` | client → server | `{ viewing }` — what the client is currently looking at |
| `presence.updated` | server → client | `{ user_id, viewing }` |
| `task.created` | server → client | `{ task_id, title, created_by, status, priority }` |
| `task.updated` | server → client | `{ task_id, changes, updated_by }` |
| `task.deleted` | server → client | `{ task_id, deleted_by }` |
| `ping` / `pong` | client ↔ server | heartbeat |

Every message is wrapped as `{ "event": ..., "data": ..., "timestamp": ... }`.

---

## Webhook system

Webhooks are org-scoped and fire on configurable events. Every delivery is logged with status and response details. Failed deliveries retry automatically on an exponential backoff schedule: 1 min → 5 min → 30 min → 2 hr → 8 hr.

**Supported events:** `task.created` · `task.updated` · `task.completed` · `task.deleted`

Each request is signed with `HMAC-SHA256`. Verify on your end:

```python
import hmac, hashlib

def verify_signature(secret: str, payload: str, signature: str) -> bool:
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## Rate limiting

All endpoints are rate-limited at **60 requests per minute per user**. Authenticated requests are bucketed by JWT token; unauthenticated requests by IP.

When the limit is exceeded:

```
HTTP 429 Too Many Requests
Retry-After: 47

{ "detail": "Rate limit exceeded. Too many requests.", "retry_after": 47 }
```

---

## Background jobs

| Task | Schedule | Description |
|---|---|---|
| `deliver_webhook_task` | On demand | HTTP delivery of a single webhook event |
| `retry_failed_webhooks` | Every 5 minutes | Requeues failed deliveries due for retry |
| `send_task_assigned_email` | On demand | Email notification on task assignment |
| `send_invitation_email` | On demand | Invitation email to new org members |
| `send_due_date_reminders` | Daily at 08:00 UTC | Emails users about tasks due within 24 hours |

---

## Database migrations

Run these from `backend/`:

```bash
alembic upgrade head                              # apply all pending migrations
alembic revision --autogenerate -m "description" # generate migration from model changes
alembic downgrade -1                              # roll back one step
alembic history                                   # view migration history
```

---

## Project structure

```
flowspace/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # Route handlers (one file per resource)
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings loaded from .env
│   │   │   ├── dependencies.py  # FastAPI DI — DB session, current user
│   │   │   ├── exceptions.py    # Global exception handlers
│   │   │   ├── middleware.py    # Rate limiting middleware
│   │   │   ├── redis.py         # Redis client singleton
│   │   │   └── security.py      # JWT and password hashing
│   │   ├── db/
│   │   │   ├── models/          # SQLAlchemy ORM models
│   │   │   ├── migrations/      # Alembic migration scripts
│   │   │   └── session.py       # Async session factory
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic layer
│   │   │   ├── task_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── cache_service.py
│   │   │   ├── webhook_service.py
│   │   │   └── notification_service.py
│   │   ├── static/
│   │   │   └── demo.html        # Project demo page served at /demo
│   │   ├── websockets/
│   │   │   └── manager.py       # WebSocket connection and presence manager
│   │   ├── workers/
│   │   │   ├── celery_app.py    # Celery app + beat schedule
│   │   │   ├── email_tasks.py   # Email delivery tasks
│   │   │   └── webhook_tasks.py # Webhook dispatch and retry
│   │   └── main.py              # App entry point and router registration
│   ├── tests/                   # pytest suite (auth, tasks, webhooks)
│   ├── docker-compose.yml       # api + db + redis + worker + beat
│   ├── Dockerfile
│   ├── render.yaml               # Render.com deployment blueprint
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios wrappers per resource
│   │   ├── components/          # Sidebar, Layout, TaskCard, TaskDetailModal, ...
│   │   ├── context/              # AuthContext, WorkspaceContext
│   │   ├── hooks/                # useWebSocket
│   │   ├── pages/                # Login, Register, Dashboard, Tasks, Analytics
│   │   └── App.jsx
│   ├── vite.config.js
│   └── package.json
│
└── docs/
    └── collab-tasks-api.postman_collection.json
```

---

## Health check

```
GET /health
→ { "status": "ok", "app": "Real-Time Collaborative Task Management API" }
```

---

## Testing

The backend test suite covers the three most critical flows: authentication, task management, and webhook delivery.

```bash
cd backend

# Create the test database (first time only)
psql -U postgres -c "CREATE DATABASE collab_tasks_test;"

# Make sure Redis is running
docker-compose up -d redis

# Run all tests
pytest -v
```

**Coverage:** 35 tests across 3 files — `test_auth.py`, `test_tasks.py`, `test_webhooks.py`

| Suite | Tests | What it covers |
|---|---|---|
| Auth | 12 | Register, login, token refresh, protected routes |
| Tasks | 14 | CRUD, filters, search, assignment email trigger, soft delete |
| Webhooks | 9 | CRUD, signature verification, delivery trigger, retry backoff |

The frontend doesn't currently have an automated test suite — see `npm run lint` for static checks in the meantime.

---

## Deployment

- **Backend** — a `render.yaml` blueprint is included for one-click deployment to [Render](https://render.com) (web service + managed Redis + managed Postgres). For other hosts, build with the provided `Dockerfile`, run `alembic upgrade head` on startup, and provide the environment variables listed above.
- **Frontend** — build a static bundle with `npm run build` (outputs to `frontend/dist/`) and deploy it to any static host (Vercel, Netlify, Render static site, etc.). Point that host's rewrite/proxy rules at your deployed backend for `/api` and `/ws`, since the app doesn't currently read an API base URL from environment variables.

---

## License

MIT