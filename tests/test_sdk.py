import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from fantomex.api import app
from fantomex.client import FantomexClient, ActiveRun
from fantomex.models import Run, Project, Artifact, Note

class FakeFigure:
    def to_json(self):
        import json
        return json.dumps({
            "data": [{"x": [1, 2, 3], "y": [4, 5, 6]}],
            "layout": {"title": "Fake Plot"}
        })



def test_artifact_download_endpoint(client, tmp_path):
    # Create project and run
    proj_resp = client.post("/api/projects", json={"name": "test-proj"}).json()
    run_resp = client.post(f"/api/projects/{proj_resp['id']}/runs", json={"name": "test-run"}).json()
    
    # Upload a file
    f_path = tmp_path / "data.csv"
    f_path.write_text("a,b,c\n1,2,3\n4,5,6")
    
    with f_path.open("rb") as fh:
        upload_resp = client.post(
            f"/api/runs/{run_resp['id']}/artifacts/upload",
            params={"type": "csv"},
            files={"file": ("data.csv", fh, "text/csv")}
        )
    assert upload_resp.status_code == 200
    
    # Download the file
    download_resp = client.get(f"/api/runs/{run_resp['id']}/artifacts/download/data.csv")
    if download_resp.status_code != 200:
        print("Download failure body:", download_resp.json())
    assert download_resp.status_code == 200
    assert download_resp.text.replace("\r\n", "\n") == "a,b,c\n1,2,3\n4,5,6"


def test_sdk_context_manager_success(db):
    # Setup database override
    from fantomex.db import get_db
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    
    # Use TestClient directly
    tclient = TestClient(app)
    
    with FantomexClient(base_url="http://testserver") as fclient:
        fclient.client = tclient
        
        with fclient.run(
            project_name="my-sdk-project",
            run_name="success-run",
            params={"learning_rate": 0.01},
            tags=["trial-1"]
        ) as active_run:
            assert isinstance(active_run, ActiveRun)
            
            # Log metrics
            metrics = active_run.log({"loss": 0.25, "acc": 0.9}, step=1)
            assert len(metrics) == 2
            
            # Log plotly
            fig = FakeFigure()
            plotly_artifact = active_run.log_plotly(fig, name="loss_chart.plotly.json")
            assert plotly_artifact["name"] == "loss_chart.plotly.json"
            assert plotly_artifact["type"] == "plotly"
            
    # Verify DB states
    project = db.query(Project).filter(Project.name == "my-sdk-project").first()
    assert project is not None
    
    run = db.query(Run).filter(Run.project_id == project.id).first()
    assert run is not None
    assert run.name == "success-run"
    assert run.status == "completed"
    assert run.params == {"learning_rate": 0.01}
    assert run.tags == ["trial-1"]
    
    app.dependency_overrides.clear()


def test_sdk_context_manager_failure(db):
    from fantomex.db import get_db
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    
    # Use TestClient directly
    tclient = TestClient(app)
    
    with pytest.raises(ValueError, match="Something went wrong"):
        with FantomexClient(base_url="http://testserver") as fclient:
            fclient.client = tclient
            
            with fclient.run(
                project_name="my-sdk-project-fail",
                run_name="failure-run",
                params={"batch_size": 32}
            ) as active_run:
                # Trigger error
                raise ValueError("Something went wrong")
                
    # Verify DB states
    project = db.query(Project).filter(Project.name == "my-sdk-project-fail").first()
    assert project is not None
    
    run = db.query(Run).filter(Run.project_id == project.id).first()
    assert run is not None
    assert run.status == "failed"
    
    # Check that note is created containing the exception traceback
    note = db.query(Note).filter(Note.run_id == run.id).first()
    assert note is not None
    assert "ValueError: Something went wrong" in note.content
    
    app.dependency_overrides.clear()


def test_sdk_authentication(db):
    from fantomex.config import get_settings
    settings = get_settings()
    settings.enable_auth = True
    settings.api_key = "test-secret-key"
    
    from fantomex.db import get_db
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    
    tclient = TestClient(app)
    
    try:
        # Write request without API key should fail with 401
        resp = tclient.post("/api/projects", json={"name": "auth-test-fail"})
        assert resp.status_code == 401
        
        # Write request with incorrect API key should fail with 401
        resp = tclient.post(
            "/api/projects",
            json={"name": "auth-test-fail-2"},
            headers={"X-Fantomex-Api-Key": "wrong-key"}
        )
        assert resp.status_code == 401
        
        # Write request with correct API key should succeed
        resp = tclient.post(
            "/api/projects",
            json={"name": "auth-test-success"},
            headers={"X-Fantomex-Api-Key": "test-secret-key"}
        )
        assert resp.status_code == 201
        
        # Test FantomexClient init with api_key
        with FantomexClient(base_url="http://testserver", api_key="test-secret-key") as fclient:
            fclient.client = tclient
            proj = fclient.create_project(name="auth-sdk-success")
            assert proj["name"] == "auth-sdk-success"
            
    finally:
        # Revert settings changes
        settings.enable_auth = False
        settings.api_key = None
        app.dependency_overrides.clear()


