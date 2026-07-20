import io
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from fantomex.config import get_settings, verify_api_key
from fantomex.db import get_db
from fantomex.models import Artifact, Run
from fantomex.schemas import ArtifactCreate, ArtifactResponse

router = APIRouter(prefix="/api/runs", tags=["artifacts"])
settings = get_settings()


def _get_s3_client():
    try:
        import boto3
    except ImportError:
        raise ImportError("The 'boto3' package is required for S3 object storage. Run: pip install boto3")

    kwargs = {}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_access_key_id and settings.s3_secret_access_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key_id
        kwargs["aws_secret_access_key"] = settings.s3_secret_access_key
    if settings.s3_region:
        kwargs["region_name"] = settings.s3_region
    return boto3.client("s3", **kwargs)


def _artifact_path(run_id: str, filename: str) -> Path:
    directory = settings.artifact_root / run_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory / filename


@router.post("/{run_id}/artifacts", response_model=ArtifactResponse, dependencies=[Depends(verify_api_key)])
def create_artifact(run_id: str, data: ArtifactCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    artifact = Artifact(run_id=run_id, **data.model_dump(exclude_unset=True))
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.post("/{run_id}/artifacts/upload", response_model=ArtifactResponse, dependencies=[Depends(verify_api_key)])
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

    if settings.s3_bucket:
        try:
            s3 = _get_s3_client()
        except ImportError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        s3_key = f"{run_id}/{file.filename}"
        contents = file.file.read()
        s3.upload_fileobj(io.BytesIO(contents), settings.s3_bucket, s3_key)
        uri = f"s3://{settings.s3_bucket}/{s3_key}"
        size_bytes = len(contents)
    else:
        dest = _artifact_path(run_id, file.filename)
        with dest.open("wb") as f:
            f.write(file.file.read())
        uri = str(dest)
        size_bytes = dest.stat().st_size

    artifact = Artifact(
        run_id=run_id,
        name=file.filename,
        type=type,
        uri=uri,
        size_bytes=size_bytes,
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


@router.get("/{run_id}/artifacts/download/{filename}")
def download_artifact(run_id: str, filename: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact = (
        db.query(Artifact)
        .filter(Artifact.run_id == run_id, Artifact.name == filename)
        .first()
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if artifact.uri.startswith("s3://"):
        try:
            s3 = _get_s3_client()
        except ImportError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        bucket, key = artifact.uri[5:].split("/", 1)
        try:
            s3_obj = s3.get_object(Bucket=bucket, Key=key)
            return StreamingResponse(
                s3_obj["Body"],
                media_type=s3_obj.get("ContentType", "application/octet-stream")
            )
        except Exception:
            raise HTTPException(status_code=404, detail="S3 file not found")
    else:
        path = Path(artifact.uri)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact file not found on disk")
        return FileResponse(path)
