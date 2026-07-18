from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from fantomex.db import get_db
from fantomex.models import Metric, Project, Run
from fantomex.schemas import (
    MetricBatchCreate,
    MetricResponse,
    RunCreate,
    RunResponse,
    RunSummary,
    RunUpdate,
)

router = APIRouter(prefix="/api", tags=["runs"])


def _run_not_found():
    raise HTTPException(status_code=404, detail="Run not found")


@router.post("/projects/{project_id}/runs", response_model=RunResponse, status_code=201)
def start_run(project_id: str, data: RunCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    run = Run(project_id=project_id, status="running", **data.model_dump(exclude_unset=True))
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/projects/{project_id}/runs", response_model=list[RunSummary])
def list_runs(
    project_id: str,
    status: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Run).filter(Run.project_id == project_id)
    if status:
        query = query.filter(Run.status == status)
    if tag:
        query = query.filter(Run.tags.contains([tag]))
    return query.order_by(Run.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        _run_not_found()
    return run


@router.patch("/runs/{run_id}", response_model=RunResponse)
def update_run(run_id: str, data: RunUpdate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        _run_not_found()
    updates = data.model_dump(exclude_unset=True)
    if updates.get("status") in {"completed", "failed", "aborted"}:
        updates["end_time"] = datetime.now(UTC)
    for key, value in updates.items():
        setattr(run, key, value)
    db.commit()
    db.refresh(run)
    return run


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        _run_not_found()
    db.delete(run)
    db.commit()
    return None


@router.post("/runs/{run_id}/metrics", response_model=list[MetricResponse], status_code=201)
def log_metrics(run_id: str, data: MetricBatchCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        _run_not_found()
    metrics = []
    for m in data.metrics:
        metric = Metric(run_id=run_id, **m.model_dump(exclude_unset=True))
        metrics.append(metric)
        db.add(metric)
    db.commit()
    for metric in metrics:
        db.refresh(metric)
    return metrics


@router.get("/runs/{run_id}/metrics", response_model=list[MetricResponse])
def get_metrics(
    run_id: str,
    key: str | None = Query(None),
    timeseries: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        _run_not_found()
    query = db.query(Metric).filter(Metric.run_id == run_id)
    if key:
        query = query.filter(Metric.key == key)
    if timeseries is True:
        query = query.filter(Metric.step.is_not(None))
    elif timeseries is False:
        query = query.filter(Metric.step.is_(None))
    return query.order_by(Metric.key, Metric.step, Metric.timestamp).all()
