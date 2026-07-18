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
- `GET /api/runs/{run_id}`
- `PATCH /api/runs/{run_id}`
- `DELETE /api/runs/{run_id}`

### Metrics

- `POST /api/runs/{run_id}/metrics`
- `GET /api/runs/{run_id}/metrics`

### Artifacts

- `POST /api/runs/{run_id}/artifacts`
- `POST /api/runs/{run_id}/artifacts/upload`
- `GET /api/runs/{run_id}/artifacts`

### Notes

- `POST /api/runs/{run_id}/notes`
- `GET /api/runs/{run_id}/notes`

### Comparison and summaries

- `POST /api/runs/compare`
- `GET /api/runs/summarize`

### Health check

- `GET /health`

## MCP usage guide

Fantomex includes an MCP server for agentic workflows. The MCP interface is useful when another tool or assistant wants to manage experiments without talking to the HTTP API directly.

### Available tools

- `create_project`
- `start_run`
- `log_metric`
- `log_artifact`
- `list_runs`
- `get_run`
- `add_note`
- `update_run`
- `get_metrics`
- `compare_runs`
- `summarize_runs`

### When to use MCP

Use MCP when you want to:

- create a project and immediately start tracking runs
- record metrics from an AI workflow or evaluation loop
- attach generated artifacts or model outputs
- retrieve a full run record for analysis
- compare several runs side by side
- summarize project-level activity programmatically

### Example MCP workflow

1. **Create a project** with `create_project`
2. **Start a run** with `start_run`
3. **Log metrics** during execution with `log_metric`
4. **Upload or register artifacts** with `log_artifact`
5. **Add notes** with `add_note`
6. **Update the run** to `completed` or `failed`
7. **Compare runs** or **summarize** a project when the experiment finishes

### Example tool inputs

#### Create a project

```json
{
  "name": "baseline-evals",
  "description": "Baseline evaluation set",
  "tags": ["evals", "baseline"],
  "meta": {"owner": "research"}
}
```

#### Start a run

```json
{
  "project_id": "proj_123",
  "name": "run-001",
  "params": {"model": "gpt-4.1", "temperature": 0.2},
  "tags": ["candidate-a"],
  "meta": {"dataset": "v1"}
}
```

#### Log a metric

```json
{
  "run_id": "run_123",
  "key": "accuracy",
  "value": 0.92,
  "step": null
}
```

#### Add a note

```json
{
  "run_id": "run_123",
  "content": "Promising result, but latency needs review."
}
```

### Example MCP responses

Tools return JSON text content. For example, `create_project` returns a project object, `start_run` returns a run object, and `log_metric` returns a metric object.

Example response shape:

```json
{
  "id": "run_123",
  "project_id": "proj_123",
  "status": "running"
}
```

## HTTP API examples

### Create a project

Request:

```bash
curl -X POST http://localhost:8000/api/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "baseline-evals",
    "description": "Baseline evaluation set",
    "tags": ["evals", "baseline"],
    "meta": {"owner": "research"}
  }'
```

Response:

```json
{
  "id": "proj_123",
  "name": "baseline-evals",
  "description": "Baseline evaluation set",
  "tags": ["evals", "baseline"],
  "meta": {"owner": "research"},
  "created_at": "2026-07-18T20:00:00Z"
}
```

### Start a run

Request:

```bash
curl -X POST http://localhost:8000/api/projects/proj_123/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "run-001",
    "params": {"model": "gpt-4.1", "temperature": 0.2},
    "tags": ["candidate-a"],
    "meta": {"dataset": "v1"}
  }'
```

Response:

```json
{
  "id": "run_123",
  "project_id": "proj_123",
  "name": "run-001",
  "status": "running",
  "params": {"model": "gpt-4.1", "temperature": 0.2},
  "tags": ["candidate-a"],
  "meta": {"dataset": "v1"}
}
```

### Log metrics

Request:

```bash
curl -X POST http://localhost:8000/api/runs/run_123/metrics \
  -H 'Content-Type: application/json' \
  -d '{
    "metrics": [
      {"key": "accuracy", "value": 0.92, "step": null},
      {"key": "loss", "value": 0.18, "step": 1}
    ]
  }'
```

Response:

```json
[
  {
    "id": "metric_1",
    "run_id": "run_123",
    "key": "accuracy",
    "value": 0.92,
    "step": null,
    "timestamp": "2026-07-18T20:01:00Z"
  },
  {
    "id": "metric_2",
    "run_id": "run_123",
    "key": "loss",
    "value": 0.18,
    "step": 1,
    "timestamp": "2026-07-18T20:01:00Z"
  }
]
```

### Update a run

Request:

```bash
curl -X PATCH http://localhost:8000/api/runs/run_123 \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "completed"
  }'
```

Response:

```json
{
  "id": "run_123",
  "status": "completed",
  "end_time": "2026-07-18T20:10:00Z"
}
```

### Compare runs

Request:

```bash
curl -X POST http://localhost:8000/api/runs/compare \
  -H 'Content-Type: application/json' \
  -d '{
    "run_ids": ["run_123", "run_456"]
  }'
```

Response:

```json
{
  "runs": [
    {
      "run": {
        "id": "run_123",
        "status": "completed"
      },
      "metrics": {
        "accuracy": [
          {"id": "metric_1", "value": 0.92}
        ]
      }
    }
  ],
  "metric_summary": {
    "accuracy": {
      "min": 0.91,
      "max": 0.92,
      "mean": 0.915,
      "std": 0.007,
      "values": [0.92, 0.91]
    }
  }
}
```

### Summarize a project

Request:

```bash
curl 'http://localhost:8000/api/runs/summarize?project_id=proj_123&status=completed&metric_keys=accuracy'
```

Response:

```json
{
  "total_runs": 8,
  "by_status": {
    "completed": 6,
    "failed": 2
  },
  "by_tag": {
    "candidate-a": 4,
    "candidate-b": 4
  },
  "metric_stats": {
    "accuracy": {
      "min": 0.88,
      "max": 0.93,
      "mean": 0.91,
      "std": 0.02,
      "last": 0.92
    }
  }
}
```

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
