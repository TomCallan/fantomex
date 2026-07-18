from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Project

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    description: str | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    tags: list[str] | None
    meta: dict[str, Any] | None
    created_at: datetime


# Run

class RunCreate(BaseModel):
    name: str | None = Field(None, max_length=255)
    params: dict[str, Any] | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None


class RunUpdate(BaseModel):
    status: str | None = Field(None, pattern="^(running|completed|failed|aborted)$")
    name: str | None = Field(None, max_length=255)
    params: dict[str, Any] | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str | None
    status: str
    tags: list[str] | None
    start_time: datetime
    end_time: datetime | None
    created_at: datetime
    updated_at: datetime


class RunResponse(RunSummary):
    params: dict[str, Any] | None
    meta: dict[str, Any] | None


# Metric

class MetricCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: float
    step: int | None = None
    timestamp: datetime | None = None


class MetricBatchCreate(BaseModel):
    metrics: list[MetricCreate]


class MetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    key: str
    value: float
    step: int | None
    timestamp: datetime


# Artifact

class ArtifactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=64)
    uri: str
    size_bytes: int | None = None
    meta: dict[str, Any] | None = None


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    name: str
    type: str
    uri: str
    size_bytes: int | None
    meta: dict[str, Any] | None
    created_at: datetime


# Note

class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    content: str
    created_at: datetime


# Comparison / summary

class CompareRequest(BaseModel):
    run_ids: list[str] = Field(..., min_length=2)


class RunComparison(BaseModel):
    run: RunResponse
    metrics: dict[str, list[MetricResponse]]


class CompareResponse(BaseModel):
    runs: list[RunComparison]
    metric_summary: dict[str, dict[str, Any]]


class SummarizeRequest(BaseModel):
    project_id: str
    status: str | None = None
    tags: list[str] | None = None
    metric_keys: list[str] | None = None


class SummaryResponse(BaseModel):
    total_runs: int
    by_status: dict[str, int]
    by_tag: dict[str, int]
    metric_stats: dict[str, dict[str, Any]]
