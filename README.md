# Collab Tasks API

A collaborative task management backend built with **FastAPI**, **PostgreSQL**, and **Redis**. Supports multi-tenant organizations, real-time collaboration via WebSockets, background job processing with Celery, and outbound webhook delivery.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Background Workers](#background-workers)
- [API Overview](#api-overview)
- [Database Migrations](#database-migrations)
- [WebSocket Events](#websocket-events)
- [Webhooks](#webhooks)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.133 |
| Database | PostgreSQL (async via `asyncpg`) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Auth | JWT (access + refresh tokens via `python-jose`) |
| Task Queue | Celery 5.6 + Redis 7 |
| Real-time | WebSockets (native FastAPI) |
| Email | Resend API |
| Validation | Pydantic v2 |
| Python | 3.13 |

---

## Features

- **Multi-tenant** — Organizations with slug-based routing; workspaces nested under orgs
- **Task management** — Full CRUD, subtasks, task dependencies, priorities, statuses, due dates, archiving
- **Labels & Custom Fields** — Flexible metadata per workspace
- **Collaboration** — Comments, file attachments, activity feed per task
- **Real-time presence** — WebSocket rooms per workspace; user join/leave/presence sync
- **Notifications** — In-app notifications with read/unread state
- **Webhooks** — Org-scoped outbound webhooks with delivery history and automatic retry
- **Email** — Transactional emails (invitations, due-date reminders) via Celery workers
- **Invitations** — Token-based workspace invitations
- **Security** — Bcrypt password hashing (SHA-256 pre-hash to bypass 72-byte limit), hashed refresh token storage

---

## Project Structure

```
app/
├── api/v1/            # Route handlers (one file per resource)
│   ├── auth.py
│   ├── organizations.py
│   ├── workspaces.py
│   ├── tasks.py
│   ├── labels.py
│   ├── custom_fields.py
│   ├── activities.py
│   ├── invitations.py
│   ├── notifications.py
│   ├── webhooks.py
│   └── websockets.py
├── core/
│   ├── config.py      # Pydantic settings (loaded from .env)
│   ├── dependencies.py # FastAPI dependency injectors (DB session, current user)
│   ├── exceptions.py  # Global exception handlers
│   └── security.py    # JWT creation/decoding, password hashing
├── db/
│   ├── models/        # SQLAlchemy ORM models
│   ├── migrations/    # Alembic migration scripts
│   └── session.py     # Async session factory
├── schemas/           # Pydantic request/response schemas
├── services/          # Business logic layer
├── websockets/
│   └── manager.py     # WebSocket connection & presence manager
├── workers/
│   ├── celery_app.py  # Celery app + beat schedule
│   ├── email_tasks.py # Email delivery tasks
│   └── webhook_tasks.py # Webhook dispatch & retry tasks
└── main.py            # App entry point, router registration
```

---

## Getting Started

### Prerequisites

- Python 3.13
- PostgreSQL
- Redis (or run via Docker)

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd collab-task-BE

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your database, Redis, and Resend credentials
```

### 3. Start Redis

```bash
docker-compose up -d
```

This starts a Redis 7 container on port `6379` with AOF persistence.

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the API server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

---

## Environment Variables

| Variable | Description |
|---|---|
| `APP_NAME` | Application display name |
| `APP_VERSION` | API version string |
| `DEBUG` | Enable debug mode (`True` / `False`) |
| `SECRET_KEY` | JWT signing secret — **change in production** |
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (default: 7) |
| `BASE_URL` | Public base URL of the API (used in emails/links) |
| `RESEND_API_KEY` | API key from [resend.com](https://resend.com) |
| `EMAIL_FROM` | Sender address for transactional emails |
| `REDIS_URL` | Redis connection URL (e.g. `redis://localhost:6379/0`) |

---

## Running the App

### Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Health check

```
GET /health
→ { "status": "ok", "app": "Collab Tasks API" }
```

---

## Background Workers

### Start the Celery worker

```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

### Start the Celery beat scheduler

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

### Scheduled tasks

| Task | Schedule | Description |
|---|---|---|
| `retry_failed_webhooks` | Every 5 minutes | Retries webhook deliveries that previously failed |
| `send_due_date_reminders` | Daily at 08:00 UTC | Emails users about tasks due soon |

---

## API Overview

All routes are versioned under `/api/v1`.

| Resource | Base Path | Notes |
|---|---|---|
| Auth | `/api/v1/auth` | Register, login, token refresh, current user |
| Organizations | `/api/v1/organizations` | CRUD for orgs (slug-based) |
| Workspaces | `/api/v1/organizations/{org_slug}/workspaces` | |
| Tasks | `/api/v1/organizations/{org_slug}/workspaces/{workspace_slug}/tasks` | Includes subtasks, dependencies, filters |
| Labels | `/api/v1/organizations/{org_slug}/workspaces/{workspace_slug}/labels` | |
| Custom Fields | `/api/v1/organizations/{org_slug}/workspaces/{workspace_slug}/custom-fields` | |
| Activities | `/api/v1/organizations/{org_slug}/workspaces/{workspace_slug}/tasks/{task_id}/activities` | |
| Invitations | `/api/v1/invitations` | Token-based workspace invites |
| Notifications | `/api/v1/notifications` | Per-user; supports unread filtering |
| Webhooks | `/api/v1/organizations/{org_slug}/webhooks` | Includes delivery history |

Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc`.

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (after changing models)
alembic revision --autogenerate -m "describe your change"

# Roll back one step
alembic downgrade -1
```

---

## WebSocket Events

Connect to: `ws://localhost:8000/ws/{workspace_id}?token=<access_token>`

### Server → Client events

| Event | Payload | Description |
|---|---|---|
| `user.joined` | `{ user_id }` | A user connected to the workspace |
| `user.left` | `{ user_id }` | A user disconnected |
| `presence.sync` | `{ online_users: [...] }` | Full presence list sent on connect |

---

## Webhooks

Webhooks are scoped to an organization and fire on configurable events. Each delivery is logged with status and response details. Failed deliveries are automatically retried every 5 minutes by the Celery beat worker.

```
POST   /api/v1/organizations/{org_slug}/webhooks
GET    /api/v1/organizations/{org_slug}/webhooks
PATCH  /api/v1/organizations/{org_slug}/webhooks/{webhook_id}
DELETE /api/v1/organizations/{org_slug}/webhooks/{webhook_id}
GET    /api/v1/organizations/{org_slug}/webhooks/{webhook_id}/deliveries
```