# PracticeForge

A personal coding-practice and code-review platform (a mini LeetCode) with a
**deterministic sandboxed judge** and an **AI layer that only explains, never grades**.

Built as a full-stack portfolio project: React, FastAPI, PostgreSQL, Redis,
Docker-based sandboxing, WebSockets.

> Status: in development (started 23 Nov 2026, target completion 31 Dec 2026).

## Docs

- [Requirements and user stories](docs/01-requirements.md)
- [Workflow diagrams](docs/02-workflow.md)
- [ER diagram](docs/03-er-diagram.md)
- [API contract](docs/04-api-contract.md)

## Repo layout

| Folder | Purpose |
|---|---|
| `frontend/` | React app (Monaco editor, dashboards) |
| `backend/` | FastAPI API, models, auth, migrations |
| `worker/` | Separate queue-consumer service that runs submissions |
| `sandbox/` | Dockerfile for the locked-down Python runner image |
| `docs/` | Design documents |

Setup instructions will be added as the project grows.


## Quick start (local, Phase 1)

Requires Docker Desktop, Python 3.12 and Git (developed on WSL2 Ubuntu).

```bash
cp .env.example .env            # then set POSTGRES_PASSWORD, DATABASE_URL and JWT_SECRET_KEY
docker compose up -d            # PostgreSQL on localhost:5433
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head            # create the tables
python -m app.scripts.create_admin you@example.com
uvicorn app.main:app --reload   # API docs at http://localhost:8000/docs
pytest -v
```