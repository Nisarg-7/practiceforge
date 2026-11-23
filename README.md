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