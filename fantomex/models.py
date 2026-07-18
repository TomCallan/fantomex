import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fantomex.db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


def make_uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    runs: Mapped[list["Run"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="runs")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    step: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="metrics")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="artifacts")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=make_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="notes")
