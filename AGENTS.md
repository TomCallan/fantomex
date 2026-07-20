# Fantomex — Agent Guide

This file is a reference for AI coding agents working on the Fantomex project. It assumes no prior knowledge of the codebase.

## 1. Project overview

Fantomex is a minimal, self-hosted experiment and run tracking platform. It is roughly comparable to a lightweight self-hosted Weights & Biases / MLflow alternative.

What it provides:

- **Projects** that group **Runs**.
- Each run can store scalar/time-series **Metrics**, file **Artifacts**, markdown **Notes**, parameters, tags, and free-form metadata.
- A **FastAPI REST API** for programmatic logging and querying.
- A **server-rendered HTML dashboard** with metric charts, artifact previews, and run comparison.
- An **MCP (Model Context Protocol) server** that exposes Fantomex operations as tools over stdio.
- An **in-repo Python client** (`FantomexClient`) with a high-level `run(...)` context manager.

### Name

**Fantomex** is a stylized shortening of **phantom experiment** — a tracker that stays in the background like a phantom while your experiments run. It is also read as an acronym:

> **F**ast **A**utomated **N**ote-taking & **T**elemetry for **O**ptimization, **M**etrics, and **EX**periments.

### Scope

Fantomex is intentionally a **minimal, single-node experiment tracker** for individuals and small teams. It is not a multi-tenant SaaS, model registry, or distributed training platform.

**In scope:**

- Organize work into **Projects** and **Runs**.
- Log scalar and time-series **Metrics**, file **Artifacts**, markdown **Notes**, parameters, tags, and free-form metadata.
- Query and compare runs via a JSON REST API and a server-rendered HTML dashboard.
- Provide an in-repo Python client and an MCP server for easy integration.
- Run self-hosted on a single machine or container with SQLite, with an escape hatch to PostgreSQL/MySQL and S3-compatible object storage.

**Intentionally out of scope (for now):**

- Multi-user accounts, RBAC, audit logging, or SSO.
- Multi-tenancy, public share links, or hosted SaaS operation.
- Model registry, dataset versioning, full lineage tracking, or distributed-training coordination.
- Hyperparameter search, run scheduling/queuing, or metric alerting.
- Real-time collaboration, comments threads beyond per-run notes, or advanced dashboard customization.

Technology stack:

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy 2.0 (ORM)
- Alembic (schema migrations)
- Pydantic 2 + pydantic-settings
- SQLite by default (PostgreSQL/MySQL supported via `DATABASE_URL`)
- Jinja2 templates + HTMX, Chart.js, Plotly.js (loaded from CDNs)
- MCP Python SDK
- httpx (client)
- pytest, pytest-asyncio, ruff (development)

## 2. Repository layout

```text
.
├── alembic/                  # Alembic migrations
│   ├── env.py                # Migration environment; reads DATABASE_URL
│   └── versions/             # Revision scripts
├── fantomex/                 # Main application package
│   ├── api.py                # FastAPI app, router wiring, health endpoint
│   ├── server.py             # CLI entry point: python -m fantomex.server
│   ├── config.py             # Pydantic settings + API key verification
│   ├── db.py                 # SQLAlchemy engine/session/base + get_db dependency
│   ├── models.py             # ORM models: Project, Run, Metric, Artifact, Note
│   ├── schemas.py            # Pydantic request/response models
│   ├── client.py             # FantomexClient, ResultPipeline, ActiveRun
│   ├── mcp.py                # MCP server tools over stdio
│   ├── routers/              # API/UI route modules
│   │   ├── projects.py
│   │   ├── runs.py
│   │   ├── artifacts.py
│   │   ├── notes.py
│   │   ├── comparison.py
│   │   └── ui.py             # Dashboard HTML routes
│   ├── templates/            # Jinja2 templates
│   └── static/               # CSS / static assets
├── scripts/                  # Helper scripts
│   └── create_example_files.py
├── tests/                    # pytest suite
├── pyproject.toml            # Project metadata, dependencies, tool config
├── uv.lock                   # uv lockfile
├── alembic.ini               # Alembic configuration
├── Dockerfile                # Container image
├── docker-compose.yml        # Local Docker deployment
└── start_dev.sh              # uv-based local dev startup script
```

## 3. Configuration and environment

Configuration is handled by `fantomex.config.Settings` (pydantic-settings). It reads a `.env` file if present and all `FANTOMEX_*`-style environment variables.

Key settings (with defaults):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./fantomex.db` | SQLAlchemy database URL |
| `ARTIFACT_ROOT` | `./artifacts` | Local artifact storage directory |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `info` | Uvicorn log level |
| `FANTOMEX_API_KEY` | none | Enables API-key auth when set |
| `S3_BUCKET` | none | Switch artifact storage to S3/R2 |
| `S3_ENDPOINT_URL` | none | Custom S3 endpoint (R2/MinIO) |
| `S3_ACCESS_KEY_ID` | none | S3 access key |
| `S3_SECRET_ACCESS_KEY` | none | S3 secret key |
| `S3_REGION` | none | S3 region |

Notes:

- The settings singleton is created at import time and ensures `ARTIFACT_ROOT` exists.
- `boto3` is **not** a project dependency. If S3 storage is enabled, the artifacts router raises `ImportError` unless `boto3` is installed separately.

## 4. Data model

Defined in `fantomex/models.py`:

- **Project** (`projects`): `id` (UUID string), `name` (unique), `description`, `tags` (JSON list), `meta` (JSON dict), `created_at`.
- **Run** (`runs`): belongs to a project; `status` defaults to `running`; supports `params`, `tags`, `meta`, `start_time`, `end_time`.
- **Metric** (`metrics`): belongs to a run; `key`, `value` (float), optional `step`, `timestamp`.
- **Artifact** (`artifacts`): belongs to a run; `name`, `type`, `uri`, `size_bytes`, `meta`.
- **Note** (`notes`): belongs to a run; `content`, `created_at`.

Relationships use SQLAlchemy 2.0 mapped-column style with `cascade="all, delete-orphan"`, so deleting a project deletes its runs and child records.

## 5. Running the application

### Install dependencies

Using `uv` (recommended in this repo):

```bash
uv sync
```

Using `pip`:

```bash
pip install -e ".[dev]"
```

### Run migrations

```bash
python -m alembic upgrade head
```

### Start the API server

```bash
python -m fantomex.server
```

Optional CLI flags:

```bash
python -m fantomex.server --auth --api-key my-secret-key
```

The server prints whether auth is enabled on startup.

### Start the MCP server

The MCP server uses stdio transport and should be launched by an MCP host:

```bash
python -m fantomex.mcp
```

### Using the provided dev script

```bash
./start_dev.sh      # uv run alembic upgrade head && uv run python -m fantomex.server
```

### Docker

```bash
docker compose up --build
```

The Dockerfile runs `alembic upgrade head` before starting the server and stores SQLite/artifacts in a persistent volume.

## 6. API and UI surface

### REST API

All JSON API routes are under `/api`:

- `POST/GET /api/projects` — create/list projects
- `GET/PATCH/DELETE /api/projects/{project_id}` — read/update/delete project
- `POST /api/projects/{project_id}/runs` — start a run
- `GET /api/projects/{project_id}/runs` — list runs with `status`, `tag`, `limit`, `offset`
- `GET /api/runs/{run_id}` — run details
- `PATCH/DELETE /api/runs/{run_id}` — update/delete run
- `POST /api/runs/{run_id}/metrics` — log a batch of metrics
- `GET /api/runs/{run_id}/metrics` — get metrics with optional `key`/`timeseries` filters
- `POST /api/runs/{run_id}/artifacts` — register an artifact by URI
- `POST /api/runs/{run_id}/artifacts/upload` — upload a file artifact
- `GET /api/runs/{run_id}/artifacts` — list artifacts
- `GET /api/runs/{run_id}/artifacts/download/{filename}` — download artifact
- `POST /api/runs/{run_id}/notes` — add a note
- `GET /api/runs/{run_id}/notes` — list notes
- `POST /api/runs/compare` — compare runs side-by-side
- `GET /api/runs/summarize` — project run summary + metric stats
- `GET /health` — health check

Write/delete endpoints require the `X-Fantomex-Api-Key` header when auth is enabled. Read endpoints are always public.

### Dashboard UI

The UI is served by `fantomex/routers/ui.py`. Canonical dashboard URLs use an explicit `/p/` prefix so project and run routes are not greedy:

- `/` — project list
- `/p/{project_name}` — run list for a project
- `/p/{project_name}/r/{run_name_or_id}` — run detail
- `/runs/compare?ids=...` — compare runs side-by-side

Legacy name-based URLs (`/{project_name}` and `/{project_name}/{run_name_or_id}`) and old `/projects/{id}/runs` and `/runs/{id}` paths return `301` redirects to the canonical `/p/` URLs for backward compatibility.

Templates live in `fantomex/templates/` and use Jinja2. Static files are served from `/static`.

### Python client

The in-repo client in `fantomex/client.py` mirrors the REST API. Basic usage:

```python
from fantomex.client import FantomexClient

with FantomexClient(base_url="http://127.0.0.1:8000") as client:
    project = client.create_project(name="demo")
    run = client.start_run(project_id=project["id"], name="run-1")
    client.log_metric(run_id=run["id"], key="accuracy", value=0.91, step=1)
    client.update_run(run_id=run["id"], status="completed")
```

High-level tracking context manager:

```python
with FantomexClient() as client:
    with client.run(project_name="demo", run_name="training", params={"lr": 0.01}) as run:
        run.log({"loss": 0.45}, step=1)
        run.log_file("predictions.csv", type="data")
```

## 7. Code organization conventions

- **Python version**: 3.11+. Code uses union syntax (`str | None`) and other 3.11+ features.
- **Router modules**: keep one concern per file under `fantomex/routers/`.
- **Models vs schemas**: DB models live in `models.py`; request/response DTOs live in `schemas.py`.
- **Dependencies**: FastAPI endpoints receive `db: Session = Depends(get_db)`. Auth is injected via `Depends(verify_api_key)` on mutating routes.
- **Client decorators**: `@pipeable` lets client methods return `ResultPipeline` when called with `pipe=True`.
- **Datetime helpers**: `now_utc()` in `models.py` uses `datetime.now(UTC)`.
- **Imports**: the project currently has some unsorted imports; ruff `I001` is part of the selected rule set.

## 8. Code style and linting

Configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

Run linting:

```bash
python -m ruff check fantomex tests scripts
```

As of the current checkout, `ruff check` reports ~87 violations (mostly `W293` blank-line whitespace, plus unsorted imports, a few long lines, and one undefined name). The majority are auto-fixable with `ruff check --fix`.

## 9. Testing strategy

Tests use **pytest** with `asyncio_mode = "auto"`.

- `tests/conftest.py` sets up a per-function SQLite database at `sqlite:///./test.db` and overrides FastAPI's `get_db` dependency with a `TestingSessionLocal` session.
- The `client` fixture returns a FastAPI `TestClient` wired to the test database.
- Tests are organized by domain: `test_projects.py`, `test_runs.py`, `test_artifacts.py`, `test_notes.py`, `test_comparison.py`, `test_client.py`, `test_sdk.py`, `test_ui.py`, `test_create_example_files_script.py`.

Run the suite:

```bash
python -m pytest
```

On the current checkout all 37 tests pass.

## 10. Deployment and operations

### Local development

1. Install dependencies.
2. Run `python -m alembic upgrade head`.
3. Run `python -m fantomex.server`.
4. Visit `http://127.0.0.1:8000/` (or the machine's LAN IP) for the dashboard.

By default the server binds to `0.0.0.0`, making it reachable from other devices on the network. Set `HOST=127.0.0.1` to restrict it to localhost.

### Docker

The provided `Dockerfile` and `docker-compose.yml` are suitable for single-node deployments. They:

- Build the package from `pyproject.toml`.
- Persist SQLite and local artifacts in a Docker volume (`/app/data`).
- Run migrations on container startup.
- Bind to `0.0.0.0:8000`.

### Production considerations

- Move from SQLite to a managed PostgreSQL database via `DATABASE_URL`.
- Move local artifact storage to S3/R2-compatible object storage via `S3_*` variables (requires installing `boto3`).
- Enable API-key auth with `FANTOMEX_API_KEY` or the `--auth` flag.
- Put the service behind a reverse proxy / load balancer that terminates TLS.
- The codebase does not include rate limiting, audit logging, or RBAC out of the box.

## 11. Security considerations

- **Authentication is off by default**. The server is open to all clients unless `FANTOMEX_API_KEY` or `--auth` is provided.
- The API key is stored and compared in plain text (`settings.api_key`). There is no hashing or key rotation mechanism.
- **Read endpoints are unauthenticated**. Only POST/PATCH/DELETE routes require the key when auth is enabled.
- **S3 credentials** are read from environment variables and passed directly to `boto3`. Do not commit them.
- **Artifact upload paths** are computed as `ARTIFACT_ROOT / run_id / filename`. The uploaded filename is used as-is, so path-sanitization is the caller's responsibility.
- **SQLite**: `check_same_thread=False` is set to work with FastAPI's dependency model.
- No CORS, CSP, rate limiting, or HTTPS handling is implemented in the application itself.

## 12. Known issues and quirks

- `fantomex/api.py` uses the deprecated `@app.on_event("startup")` decorator. FastAPI recommends lifespan event handlers instead.
- The UI template `run_detail.html` loads third-party JS libraries from public CDNs. Offline environments will need vendored copies.
- The test suite emits a Starlette/httpx deprecation warning about `TestClient`.
- Default binding is `0.0.0.0`. When running on an untrusted network, enable `FANTOMEX_API_KEY` or put the service behind a reverse proxy that handles TLS and access control.
