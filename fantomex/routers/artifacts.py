from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from fantomex.config import get_settings
from fantomex.db import get_db
from fantomex.models import Artifact, Run
from fantomex.schemas import ArtifactCreate, ArtifactResponse

router = APIRouter(prefix="/api/runs", tags=["artifacts"])
settings = get_settings()


def _artifact_path(run_id: str, filename: str) -> Path:
    directory = settings.artifact_root / run_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory / filename


@router.post("/{run_id}/artifacts", response_model=ArtifactResponse)
def create_artifact(run_id: str, data: ArtifactCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    artifact = Artifact(run_id=run_id, **data.model_dump(exclude_unset=True))
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.post("/{run_id}/artifacts/upload", response_model=ArtifactResponse)
def upload_artifact(
    run_id: str,
    file: UploadFile,
    type: str = "file",
    db: Session = Depends(get_db),
):
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
    db.refresh(artifact)
    return artifact


@router.get("/{run_id}/artifacts", response_model=list[ArtifactResponse])
def list_artifacts(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return (
        db.query(Artifact)
        .filter(Artifact.run_id == run_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
