# Fantomex

Minimal experiment/run tracking with:
- FastAPI HTTP API
- SQLite + Alembic migrations
- MCP server tools for agent workflows
- Lightweight in-repo Python client

## Quickstart (first-time users)

### Prerequisites

- Python 3.11+
- `pip`
- Optional: `uv` (commands below include non-`uv` alternatives)

### 1) Install dependencies

```bash
cd /home/runner/work/fantomex/fantomex
pip install fastapi uvicorn sqlalchemy alembic pydantic pydantic-settings mcp httpx jinja2 python-multipart
```

### 2) Configure environment (optional)

Fantomex reads these environment variables:

- `DATABASE_URL` (default: `sqlite:///./fantomex.db`)
- `ARTIFACT_ROOT` (default: `./artifacts`)
- `HOST` (default: `127.0.0.1`)
- `PORT` (default: `8000`)
- `LOG_LEVEL` (default: `info`)

Example:

```bash
export DATABASE_URL='sqlite:///./fantomex.db'
export ARTIFACT_ROOT='./artifacts'
export HOST='127.0.0.1'
export PORT='8000'
export LOG_LEVEL='info'
```

### 3) Run migrations

```bash
python -m alembic upgrade head
```

### 4) Start the API server

```bash
python -m fantomex.server
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Architecture at a glance

- `fantomex/api.py` — FastAPI app and router wiring
- `fantomex/routers/` — API endpoints (projects, runs, metrics, artifacts, notes, comparison)
- `fantomex/mcp.py` — MCP server tools exposed over stdio
- `fantomex/client.py` — lightweight REST client + result piping helpers
- `alembic/` — schema migrations
- `scripts/create_example_files.py` — local sample data generator

## MCP server usage

### What it is

`fantomex/mcp.py` exposes Fantomex operations as MCP tools (create project, start run, log metrics/artifacts, summarize runs, etc.).

### Start MCP server

```bash
cd /home/runner/work/fantomex/fantomex
python -m fantomex.mcp
```

The server uses stdio transport, so it should be launched by an MCP host (IDE plugin, MCP inspector, or agent runtime).

### End-to-end MCP example (with MCP Inspector)

In one shell, start API server:

```bash
cd /home/runner/work/fantomex/fantomex
python -m alembic upgrade head
python -m fantomex.server
```

In another shell, start inspector against Fantomex MCP server:

```bash
npx @modelcontextprotocol/inspector python -m fantomex.mcp
```

Then call tools in this order from the inspector UI:

1. `create_project`
```json
{"name":"demo-mcp-project","tags":["demo"]}
```
2. `start_run`
```json
{"project_id":"<project_id_from_step_1>","name":"demo-run"}
```
3. `log_metric`
```json
{"run_id":"<run_id_from_step_2>","key":"accuracy","value":0.93,"step":1}
```
4. `update_run`
```json
{"run_id":"<run_id_from_step_2>","status":"completed"}
```

### MCP troubleshooting

- **`Run not found` / `Project not found`**: verify IDs from previous tool outputs.
- **No data persisted**: check `DATABASE_URL` and make sure migrations ran.
- **MCP host cannot connect**: ensure host is launching `python -m fantomex.mcp` and not expecting HTTP transport.
- **SQLite permission errors**: point `DATABASE_URL`/`ARTIFACT_ROOT` to writable paths.

## Python REST client usage

Use the in-repo client directly after clone.

```python
from fantomex.client import FantomexClient

with FantomexClient(base_url="http://127.0.0.1:8000") as client:
    project = client.create_project(name="quickstart-project")
    run = client.start_run(project_id=project["id"], name="run-001")
    client.log_metric(run_id=run["id"], key="accuracy", value=0.91, step=1)
    client.update_run(run_id=run["id"], status="completed")
```

### Result piping (decorator-enabled pattern)

Client methods support `pipe=True` and return `ResultPipeline`:

```python
from fantomex.client import FantomexClient

with FantomexClient() as client:
    run_id = (
        client.create_project(name="pipe-demo", pipe=True)
        .pipe(lambda project: client.start_run(project_id=project["id"], name="pipe-run"))
        .pipe(lambda run: run["id"])
        .unwrap()
    )

    print(run_id)
```

### Error handling

Errors raise `FantomexClientError` with `status_code` and normalized `detail` payload.

## Generate example files for local testing

Script: `/home/runner/work/fantomex/fantomex/scripts/create_example_files.py`

Create defaults in `./example_data`:

```bash
cd /home/runner/work/fantomex/fantomex
python scripts/create_example_files.py
```

Custom location:

```bash
python scripts/create_example_files.py --output-dir ./tmp/example_data
```

Overwrite existing files:

```bash
python scripts/create_example_files.py --output-dir ./tmp/example_data --overwrite
```

Generated files are representative run/project/metric/note/artifact payloads for local demos.

## Hosting options (practical guidance)

| Option | Best for | Pros | Tradeoffs |
|---|---|---|---|
| Local VM / bare metal | Small internal teams | Lowest cost, full control, easy SQLite start | You own backups, patching, uptime |
| Docker on self-hosted server | Small/medium teams | Reproducible deploys, simple rollback | Still self-managed ops |
| Render | Small/medium managed deployments | Easy deploy from repo, managed runtime | Cost grows with sustained usage |
| Railway | Fast prototypes + small teams | Quick setup, simple DX | Fewer deep infra controls |
| Fly.io | Medium deployments needing regional placement | Flexible regions, container-native | More tuning/ops knowledge needed |

### Recommendation

- **Small deployment (single team):** start with Docker + one managed provider (Render or Railway).
- **Medium deployment:** use Fly.io or Docker on a managed VM, move DB to managed Postgres, keep artifacts on object storage.

## Development and tests

Run tests:

```bash
cd /home/runner/work/fantomex/fantomex
PYTHONPATH=/home/runner/work/fantomex/fantomex python -m pytest
```

Run lint (if `ruff` installed):

```bash
python -m ruff check fantomex tests scripts
```
