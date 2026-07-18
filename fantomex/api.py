from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fantomex.config import get_settings
from fantomex.db import Base, engine
from fantomex.routers import artifacts, comparison, notes, projects, runs, ui

settings = get_settings()

app = FastAPI(title="Fantomex", version="0.1.0")
app.mount("/static", StaticFiles(directory="fantomex/static"), name="static")
app.include_router(projects.router)
app.include_router(comparison.router)
app.include_router(artifacts.router)
app.include_router(notes.router)
app.include_router(runs.router)
app.include_router(ui.router)


@app.on_event("startup")
def on_startup():
    # Ensure tables exist for fresh SQLite dev runs. Alembic remains the
    # source of truth for schema migrations; this is just a convenience.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
