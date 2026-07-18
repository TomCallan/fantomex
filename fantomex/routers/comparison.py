import statistics
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fantomex.db import get_db
from fantomex.models import Metric, Run
from fantomex.schemas import CompareRequest, CompareResponse, SummaryResponse

router = APIRouter(prefix="/api", tags=["comparison"])


@router.post("/runs/compare", response_model=CompareResponse)
def compare_runs(data: CompareRequest, db: Session = Depends(get_db)):
    runs = db.query(Run).filter(Run.id.in_(data.run_ids)).all()
    if len(runs) != len(data.run_ids):
        raise HTTPException(status_code=404, detail="One or more runs not found")

    result = []
    metric_values: dict[str, list[float]] = defaultdict(list)

    for run in runs:
        metrics_by_key: dict[str, list[Metric]] = defaultdict(list)
        for metric in run.metrics:
            metrics_by_key[metric.key].append(metric)
            if metric.step is None:
                metric_values[metric.key].append(metric.value)

        result.append({"run": run, "metrics": dict(metrics_by_key)})

    metric_summary: dict[str, dict[str, Any]] = {}
    for key, values in metric_values.items():
        if not values:
            continue
        metric_summary[key] = {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "values": values,
        }

    return {"runs": result, "metric_summary": metric_summary}


@router.get("/runs/summarize", response_model=SummaryResponse)
def summarize_runs(
    project_id: str,
    status: str | None = None,
    tag: str | None = None,
    metric_keys: list[str] | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Run).filter(Run.project_id == project_id)
    if status:
        query = query.filter(Run.status == status)
    if tag:
        query = query.filter(Run.tags.contains([tag]))
    runs = query.all()

    by_status: dict[str, int] = defaultdict(int)
    by_tag: dict[str, int] = defaultdict(int)
    metric_values: dict[str, list[float]] = defaultdict(list)
    metric_last: dict[str, float] = {}

    for run in runs:
        by_status[run.status] += 1
        for t in run.tags or []:
            by_tag[t] += 1

    metric_query = db.query(Metric).join(Run).filter(Run.project_id == project_id)
    if status:
        metric_query = metric_query.filter(Run.status == status)
    if metric_keys:
        metric_query = metric_query.filter(Metric.key.in_(metric_keys))

    for metric in metric_query.all():
        if metric.step is None:
            metric_values[metric.key].append(metric.value)
        metric_last[metric.key] = metric.value

    metric_stats: dict[str, dict[str, Any]] = {}
    for key, values in metric_values.items():
        if not values:
            continue
        metric_stats[key] = {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "last": metric_last.get(key),
        }

    return {
        "total_runs": len(runs),
        "by_status": dict(by_status),
        "by_tag": dict(by_tag),
        "metric_stats": metric_stats,
    }
