from collections import defaultdict

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from fantomex.config import get_settings
from fantomex.db import get_db
from fantomex.models import Artifact, Metric, Project, Run

router = APIRouter(tags=["ui"])
# Disable Jinja2 template caching to avoid a cache-key unhashability issue on Python 3.14.
env = Environment(loader=FileSystemLoader("fantomex/templates"), cache_size=0)
templates = Jinja2Templates(env=env)
settings = get_settings()


def _canonical_project_url(project: Project) -> str:
    return f"/p/{project.name}"


def _canonical_run_url(project: Project, run: Run) -> str:
    run_segment = run.name or run.id
    return f"/p/{project.name}/r/{run_segment}"


@router.get("/", response_class=HTMLResponse)
def project_list(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return templates.TemplateResponse(request, "projects.html", {"projects": projects})


@router.post("/projects", response_class=RedirectResponse)
def create_project_ui(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
):
    existing = db.query(Project).filter(Project.name == name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Project already exists")
    project = Project(name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return RedirectResponse(url="/", status_code=303)


# Backward-compatible redirect: old project/run list path -> canonical /p/ URL
@router.get("/projects/{project_id}/runs", response_class=RedirectResponse)
def run_list_redirect(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return RedirectResponse(url=_canonical_project_url(project), status_code=301)


@router.get("/runs/compare", response_class=HTMLResponse)
def compare_runs(
    request: Request,
    ids: str,
    db: Session = Depends(get_db),
):
    run_ids = [r.strip() for r in ids.split(",") if r.strip()]
    runs = db.query(Run).filter(Run.id.in_(run_ids)).all()
    if len(runs) != len(run_ids):
        raise HTTPException(status_code=404, detail="One or more runs not found")

    # Gather common param keys.
    param_keys = set()
    for run in runs:
        param_keys.update(run.params or {})
    param_keys = sorted(param_keys)

    # Gather scalar metrics.
    metric_keys = set()
    run_metrics: dict[str, dict[str, float]] = defaultdict(dict)
    for run in runs:
        for metric in run.metrics:
            if metric.step is None:
                run_metrics[run.id][metric.key] = metric.value
                metric_keys.add(metric.key)
    metric_keys = sorted(metric_keys)

    return templates.TemplateResponse(
        request,
        "compare.html",
        {
            "runs": runs,
            "param_keys": param_keys,
            "metric_keys": metric_keys,
            "run_metrics": run_metrics,
        },
    )


# Backward-compatible redirect: old run detail path -> canonical /p/ URL
@router.get("/runs/{run_id}", response_class=RedirectResponse)
def run_detail_redirect(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RedirectResponse(url=_canonical_run_url(run.project, run), status_code=301)


# ---------------------------------------------------------------------------
# UI actions: redirect back to Referer so namespace is preserved, otherwise
# fall back to the canonical URL for the run.
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/runs", response_class=RedirectResponse)
def start_run_ui(
    request: Request,
    project_id: str,
    name: str | None = Form(None),
    params_json: str | None = Form(None),
    tags: str | None = Form(None),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    import json

    params = json.loads(params_json) if params_json else None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    run = Run(project_id=project_id, name=name, params=params, tags=tag_list, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return RedirectResponse(
        url=request.headers.get("referer", _canonical_project_url(project)),
        status_code=303,
    )


@router.post("/runs/{run_id}/status", response_class=RedirectResponse)
def update_run_status_ui(
    request: Request,
    run_id: str,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = status
    if status in {"completed", "failed", "aborted"}:
        from datetime import UTC, datetime
        run.end_time = datetime.now(UTC)
    db.commit()
    return RedirectResponse(
        url=request.headers.get("referer", _canonical_run_url(run.project, run)),
        status_code=303,
    )


@router.post("/runs/{run_id}/metrics", response_class=RedirectResponse)
def log_metric_ui(
    request: Request,
    run_id: str,
    key: str = Form(...),
    value: float = Form(...),
    step: int | None = Form(None),
    db: Session = Depends(get_db),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    metric = Metric(run_id=run_id, key=key, value=value, step=step)
    db.add(metric)
    db.commit()
    return RedirectResponse(
        url=request.headers.get("referer", _canonical_run_url(run.project, run)),
        status_code=303,
    )


@router.post("/runs/{run_id}/notes", response_class=RedirectResponse)
def add_note_ui(
    request: Request,
    run_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    from fantomex.models import Note

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    note = Note(run_id=run_id, content=content)
    db.add(note)
    db.commit()
    return RedirectResponse(
        url=request.headers.get("referer", _canonical_run_url(run.project, run)),
        status_code=303,
    )


@router.post("/runs/{run_id}/artifacts/upload", response_class=RedirectResponse)
def upload_artifact_ui(
    request: Request,
    run_id: str,
    file: UploadFile,
    type: str = Form("file"),
    db: Session = Depends(get_db),
):
    from fantomex.routers.artifacts import _artifact_path

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    dest = _artifact_path(run_id, file.filename)
    with dest.open("wb") as f:
        f.write(file.file.read())

    artifact = Artifact(
        run_id=run_id,
        name=file.filename,
        type=type,
        uri=str(dest),
        size_bytes=dest.stat().st_size,
    )
    db.add(artifact)
    db.commit()
    return RedirectResponse(
        url=request.headers.get("referer", _canonical_run_url(run.project, run)),
        status_code=303,
    )


# ---------------------------------------------------------------------------
# Canonical UI routes: /p/{project} and /p/{project}/r/{run}
# ---------------------------------------------------------------------------


def _render_run_list(
    request: Request,
    project: Project,
    status: str | None,
    tag: str | None,
    sort: str,
    db: Session,
):
    query = db.query(Run).filter(Run.project_id == project.id)
    if status:
        query = query.filter(Run.status == status)
    if tag:
        query = query.filter(Run.tags.contains([tag]))

    if sort == "created_at":
        query = query.order_by(Run.created_at.desc())
    elif sort == "name":
        query = query.order_by(Run.name)
    elif sort == "status":
        query = query.order_by(Run.status)

    runs = query.all()

    # Collect scalar metrics for preview columns.
    run_ids = [r.id for r in runs]
    preview_metrics: dict[str, dict[str, float]] = defaultdict(dict)
    if run_ids:
        for metric in (
            db.query(Metric)
            .filter(Metric.run_id.in_(run_ids), Metric.step.is_(None))
            .all()
        ):
            preview_metrics[metric.run_id][metric.key] = metric.value

    # Collect tags for filter dropdown.
    tags = set()
    for r in runs:
        for t in r.tags or []:
            tags.add(t)

    return templates.TemplateResponse(
        request,
        "runs.html",
        {
            "project": project,
            "runs": runs,
            "status": status,
            "tag": tag,
            "sort": sort,
            "tags": sorted(tags),
            "preview_metrics": preview_metrics,
        },
    )


def _render_run_detail(
    request: Request,
    project: Project,
    run: Run,
    db: Session,
):
    metrics_by_key: dict[str, list[Metric]] = defaultdict(list)
    scalar_metrics: dict[str, float] = {}
    for metric in run.metrics:
        metrics_by_key[metric.key].append(metric)
        if metric.step is None:
            scalar_metrics[metric.key] = metric.value

    time_series = {k: v for k, v in metrics_by_key.items() if any(m.step is not None for m in v)}

    return templates.TemplateResponse(
        request,
        "run_detail.html",
        {
            "project": project,
            "run": run,
            "scalar_metrics": scalar_metrics,
            "time_series": time_series,
            "artifacts": run.artifacts,
            "notes": run.notes,
        },
    )


@router.get("/p/{project_name}", response_class=HTMLResponse)
def canonical_run_list(
    request: Request,
    project_name: str,
    status: str | None = None,
    tag: str | None = None,
    sort: str = "created_at",
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        (Project.name == project_name) | (Project.id == project_name)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _render_run_list(request, project, status, tag, sort, db)


@router.get("/p/{project_name}/r/{run_name_or_id}", response_class=HTMLResponse)
def canonical_run_detail(
    request: Request,
    project_name: str,
    run_name_or_id: str,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        (Project.name == project_name) | (Project.id == project_name)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run = db.query(Run).filter(
        Run.project_id == project.id,
        (Run.name == run_name_or_id) | (Run.id == run_name_or_id)
    ).order_by(Run.created_at.desc()).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return _render_run_detail(request, project, run, db)


# ---------------------------------------------------------------------------
# Legacy name-based URL redirects (kept for backward compatibility)
# ---------------------------------------------------------------------------


@router.get("/{project_name}", response_class=RedirectResponse)
def legacy_run_list_redirect(
    project_name: str,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        (Project.name == project_name) | (Project.id == project_name)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return RedirectResponse(url=_canonical_project_url(project), status_code=301)


@router.get("/{project_name}/{run_name_or_id}", response_class=RedirectResponse)
def legacy_run_detail_redirect(
    project_name: str,
    run_name_or_id: str,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        (Project.name == project_name) | (Project.id == project_name)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run = db.query(Run).filter(
        Run.project_id == project.id,
        (Run.name == run_name_or_id) | (Run.id == run_name_or_id)
    ).order_by(Run.created_at.desc()).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RedirectResponse(url=_canonical_run_url(project, run), status_code=301)
