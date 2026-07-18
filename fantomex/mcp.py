import json
from datetime import UTC, datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from fantomex.db import SessionLocal
from fantomex.models import Artifact, Metric, Note, Project, Run
from fantomex.routers.comparison import compare_runs as compare_runs_endpoint
from fantomex.routers.comparison import summarize_runs as summarize_runs_endpoint
from fantomex.schemas import (
    ArtifactResponse,
    MetricResponse,
    NoteResponse,
    ProjectResponse,
    RunResponse,
)

app = Server("fantomex")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db() -> Session:
    return SessionLocal()


def _run_or_raise(db: Session, run_id: str) -> Run:
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise ValueError(f"Run not found: {run_id}")
    return run


def _project_or_raise(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project not found: {project_id}")
    return project


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

class CreateProjectInput(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    tags: list[str] | None = None
    meta: dict | None = None


class StartRunInput(BaseModel):
    project_id: str
    name: str | None = None
    params: dict | None = None
    tags: list[str] | None = None
    meta: dict | None = None


class LogMetricInput(BaseModel):
    run_id: str
    key: str
    value: float
    step: int | None = None
    timestamp: str | None = None


class LogArtifactInput(BaseModel):
    run_id: str
    name: str
    type: str
    uri: str
    size_bytes: int | None = None
    meta: dict | None = None


class ListRunsInput(BaseModel):
    project_id: str
    status: str | None = None
    tags: list[str] | None = None
    limit: int = 100
    offset: int = 0


class GetRunInput(BaseModel):
    run_id: str


class AddNoteInput(BaseModel):
    run_id: str
    content: str


class UpdateRunInput(BaseModel):
    run_id: str
    status: str | None = None
    params: dict | None = None
    tags: list[str] | None = None
    meta: dict | None = None


class GetMetricsInput(BaseModel):
    run_id: str
    key: str | None = None
    timeseries: bool | None = None


class CompareRunsInput(BaseModel):
    run_ids: list[str] = Field(..., min_length=2)


class SummarizeRunsInput(BaseModel):
    project_id: str
    status: str | None = None
    tags: list[str] | None = None
    metric_keys: list[str] | None = None


TOOLS = [
    Tool(
        name="create_project",
        description="Create a new project to group runs.",
        inputSchema=CreateProjectInput.model_json_schema(),
    ),
    Tool(
        name="start_run",
        description="Start a new run inside a project.",
        inputSchema=StartRunInput.model_json_schema(),
    ),
    Tool(
        name="log_metric",
        description="Log a scalar or time-series metric for a run.",
        inputSchema=LogMetricInput.model_json_schema(),
    ),
    Tool(
        name="log_artifact",
        description="Register an artifact file for a run.",
        inputSchema=LogArtifactInput.model_json_schema(),
    ),
    Tool(
        name="list_runs",
        description="List runs for a project with optional filters.",
        inputSchema=ListRunsInput.model_json_schema(),
    ),
    Tool(
        name="get_run",
        description="Get full run details including metrics, artifacts, and notes.",
        inputSchema=GetRunInput.model_json_schema(),
    ),
    Tool(
        name="add_note",
        description="Add a markdown note to a run.",
        inputSchema=AddNoteInput.model_json_schema(),
    ),
    Tool(
        name="update_run",
        description="Update a run's status, params, tags, or metadata.",
        inputSchema=UpdateRunInput.model_json_schema(),
    ),
    Tool(
        name="get_metrics",
        description="Get metrics for a run, optionally filtered by key or time-series flag.",
        inputSchema=GetMetricsInput.model_json_schema(),
    ),
    Tool(
        name="compare_runs",
        description="Compare multiple runs side-by-side with metric statistics.",
        inputSchema=CompareRunsInput.model_json_schema(),
    ),
    Tool(
        name="summarize_runs",
        description="Summarize runs for a project, including status/tag breakdowns and metric stats.",
        inputSchema=SummarizeRunsInput.model_json_schema(),
    ),
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    db = _db()
    try:
        if name == "create_project":
            data = CreateProjectInput(**arguments)
            if db.query(Project).filter(Project.name == data.name).first():
                raise ValueError(f"Project '{data.name}' already exists")
            project = Project(**data.model_dump(exclude_unset=True))
            db.add(project)
            db.commit()
            db.refresh(project)
            return [TextContent(type="text", text=ProjectResponse.model_validate(project).model_dump_json())]

        if name == "start_run":
            data = StartRunInput(**arguments)
            _project_or_raise(db, data.project_id)
            run = Run(
                project_id=data.project_id,
                status="running",
                **data.model_dump(exclude={"project_id"}, exclude_unset=True),
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return [TextContent(type="text", text=RunResponse.model_validate(run).model_dump_json())]

        if name == "log_metric":
            data = LogMetricInput(**arguments)
            _run_or_raise(db, data.run_id)
            ts = datetime.fromisoformat(data.timestamp) if data.timestamp else datetime.now(UTC)
            metric = Metric(run_id=data.run_id, key=data.key, value=data.value, step=data.step, timestamp=ts)
            db.add(metric)
            db.commit()
            db.refresh(metric)
            return [TextContent(type="text", text=MetricResponse.model_validate(metric).model_dump_json())]

        if name == "log_artifact":
            data = LogArtifactInput(**arguments)
            _run_or_raise(db, data.run_id)
            artifact = Artifact(**data.model_dump(exclude_unset=True))
            db.add(artifact)
            db.commit()
            db.refresh(artifact)
            return [TextContent(type="text", text=ArtifactResponse.model_validate(artifact).model_dump_json())]

        if name == "list_runs":
            data = ListRunsInput(**arguments)
            _project_or_raise(db, data.project_id)
            query = db.query(Run).filter(Run.project_id == data.project_id)
            if data.status:
                query = query.filter(Run.status == data.status)
            if data.tags:
                for tag in data.tags:
                    query = query.filter(Run.tags.contains([tag]))
            runs = query.order_by(Run.created_at.desc()).offset(data.offset).limit(data.limit).all()
            payload = {
                "runs": [RunResponse.model_validate(r).model_dump() for r in runs],
                "total": query.count(),
            }
            return [TextContent(type="text", text=str(payload))]

        if name == "get_run":
            data = GetRunInput(**arguments)
            run = _run_or_raise(db, data.run_id)
            payload = RunResponse.model_validate(run).model_dump()
            payload["metrics"] = [MetricResponse.model_validate(m).model_dump() for m in run.metrics]
            payload["artifacts"] = [ArtifactResponse.model_validate(a).model_dump() for a in run.artifacts]
            payload["notes"] = [NoteResponse.model_validate(n).model_dump() for n in run.notes]
            return [TextContent(type="text", text=str(payload))]

        if name == "add_note":
            data = AddNoteInput(**arguments)
            _run_or_raise(db, data.run_id)
            note = Note(run_id=data.run_id, content=data.content)
            db.add(note)
            db.commit()
            db.refresh(note)
            return [TextContent(type="text", text=NoteResponse.model_validate(note).model_dump_json())]

        if name == "update_run":
            data = UpdateRunInput(**arguments)
            run = _run_or_raise(db, data.run_id)
            updates = data.model_dump(exclude_unset=True)
            if updates.get("status") in {"completed", "failed", "aborted"}:
                updates["end_time"] = datetime.now(UTC)
            for key, value in updates.items():
                setattr(run, key, value)
            db.commit()
            db.refresh(run)
            return [TextContent(type="text", text=RunResponse.model_validate(run).model_dump_json())]

        if name == "get_metrics":
            data = GetMetricsInput(**arguments)
            _run_or_raise(db, data.run_id)
            query = db.query(Metric).filter(Metric.run_id == data.run_id)
            if data.key:
                query = query.filter(Metric.key == data.key)
            if data.timeseries is True:
                query = query.filter(Metric.step.is_not(None))
            elif data.timeseries is False:
                query = query.filter(Metric.step.is_(None))
            metrics = query.order_by(Metric.key, Metric.step, Metric.timestamp).all()
            metric_list = [MetricResponse.model_validate(m).model_dump() for m in metrics]
            return [TextContent(type="text", text=str({"metrics": metric_list}))]

        if name == "compare_runs":
            data = CompareRunsInput(**arguments)
            raw = compare_runs_endpoint(data, db)
            runs = []
            for item in raw["runs"]:
                run_payload = RunResponse.model_validate(item["run"]).model_dump()
                run_payload["metrics"] = {
                    k: [MetricResponse.model_validate(m).model_dump() for m in v]
                    for k, v in item["metrics"].items()
                }
                runs.append(run_payload)
            result = {"runs": runs, "metric_summary": raw["metric_summary"]}
            return [TextContent(type="text", text=json.dumps(result, default=str))]

        if name == "summarize_runs":
            data = SummarizeRunsInput(**arguments)
            result = summarize_runs_endpoint(
                project_id=data.project_id,
                status=data.status,
                tag=data.tags[0] if data.tags else None,
                metric_keys=data.metric_keys,
                db=db,
            )
            return [TextContent(type="text", text=json.dumps(result, default=str))]

        raise ValueError(f"Unknown tool: {name}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
