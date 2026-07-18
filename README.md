# Fantomex

Fantomex is a minimal, self-hosted experiment and run tracking platform with an AI-first workflow via MCP. It provides a lightweight FastAPI backend, a simple web UI, and a local-first development setup backed by SQLite and Alembic migrations.

## Features

- **Project management**: create, update, list, and delete projects
- **Run tracking**: start runs, update status, and browse run history
- **Metrics logging**: record scalar metrics and metric batches for a run
- **Artifacts**: attach files or external artifact URIs to runs
- **Notes**: add notes to runs for review and collaboration
- **Comparison and summaries**: compare runs and summarize metrics across a project
- **Web UI**: browse projects and runs in a browser-based dashboard
- **MCP server**: interact with Fantomex through Model Context Protocol tools
- **Local-first dev experience**: SQLite by default, with Alembic migrations for schema changes

## Tech stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic v2
- MCP
- Uvicorn
- Jinja2

## Quick start

### 1) Create a virtual environment and install dependencies

```bash
uv venv
uv pip install -e ".[dev]"
```

### 2) Run database migrations

```bash
uv run alembic upgrade head
```

### 3) Start the app

```bash
uv run python -m fantomex.server
```

Or use the dev helper script:

```bash
./start_dev.sh
```

## Configuration

Fantomex is designed to work out of the box with a local SQLite database. Database settings and artifact storage are handled through the app configuration.

Typical defaults include:

- **Database**: SQLite at `./fantomex.db`
- **Artifacts**: stored on disk under a configured artifact root

If you change configuration values, make sure the database URL and artifact path point to writable locations.

## API overview

### Projects

- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `PATCH /api/projects/{project_id}`
- `DELETE /api/projects/{project_id}`

### Runs

- `POST /api/projects/{project_id}/runs`
- `GET /api/projects/{project_id}/runs`
- `GET /runs/{run_id}`
- `PATCH /runs/{run_id}`
- `DELETE /runs/{run_id}`

### Metrics

- `POST /runs/{run_id}/metrics`
- `GET /runs/{run_id}/metrics`

### Artifacts

- `POST /runs/{run_id}/artifacts`
- `POST /runs/{run_id}/artifacts/upload`
- `GET /runs/{run_id}/artifacts`

### Notes

- `POST /runs/{run_id}/notes`
- `GET /runs/{run_id}/notes`

### Comparison and summaries

- `POST /api/runs/compare`
- `GET /api/runs/summarize`

### Health check

- `GET /health`

## MCP tools

Fantomex exposes an MCP server for agent-friendly workflows such as:

- creating projects
- starting runs
- logging metrics
- uploading artifacts
- adding notes
- comparing runs
- summarizing project activity

This makes it easy to integrate Fantomex into AI-assisted research, experimentation, and evaluation loops.

## Development

### Linting

```bash
uv run ruff check .
```

### Tests

```bash
uv run pytest
```

## Project layout

- `fantomex/api.py` — FastAPI application setup
- `fantomex/routers/` — HTTP routes for projects, runs, artifacts, notes, comparisons, and UI
- `fantomex/mcp.py` — MCP server and tool definitions
- `alembic/` — database migration environment and revisions
- `start_dev.sh` — convenience script to run migrations and launch the app

## Roadmap ideas

If you want to expand Fantomex further, useful next steps could include:

- richer dashboards and filtering
- experiment tags and metadata search
- run grouping and comparison views
- better artifact browsing and previews
- authentication and multi-user support
- import/export tooling
- cloud storage backends for artifacts

## License

No license has been specified yet.
