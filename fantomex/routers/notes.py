from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fantomex.db import get_db
from fantomex.models import Note, Run
from fantomex.schemas import NoteCreate, NoteResponse

from fantomex.config import verify_api_key

router = APIRouter(prefix="/api/runs", tags=["notes"])


@router.post("/{run_id}/notes", response_model=NoteResponse, status_code=201, dependencies=[Depends(verify_api_key)])
def create_note(run_id: str, data: NoteCreate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    note = Note(run_id=run_id, content=data.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{run_id}/notes", response_model=list[NoteResponse])
def list_notes(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return db.query(Note).filter(Note.run_id == run_id).order_by(Note.created_at.desc()).all()
