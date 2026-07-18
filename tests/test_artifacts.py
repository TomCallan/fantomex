import pytest


@pytest.fixture
def project(client):
    return client.post("/api/projects", json={"name": "artifact-tests"}).json()


@pytest.fixture
def run(project, client):
    return client.post(f"/api/projects/{project['id']}/runs", json={"name": "run-1"}).json()


def test_create_artifact(run, client):
    r = client.post(
        f"/api/runs/{run['id']}/artifacts",
        json={"name": "trades.csv", "type": "csv", "uri": "/tmp/trades.csv"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "trades.csv"
    assert data["type"] == "csv"


def test_list_artifacts(run, client):
    client.post(
        f"/api/runs/{run['id']}/artifacts",
        json={"name": "a.csv", "type": "csv", "uri": "/tmp/a.csv"},
    )
    client.post(
        f"/api/runs/{run['id']}/artifacts",
        json={"name": "b.json", "type": "json", "uri": "/tmp/b.json"},
    )
    r = client.get(f"/api/runs/{run['id']}/artifacts")
    assert len(r.json()) == 2


def test_upload_artifact(run, client, tmp_path):
    f = tmp_path / "report.txt"
    f.write_text("hello world")
    with f.open("rb") as fh:
        r = client.post(
            f"/api/runs/{run['id']}/artifacts/upload",
            params={"type": "log"},
            files={"file": ("report.txt", fh, "text/plain")},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "report.txt"
    assert data["type"] == "log"
    assert data["size_bytes"] == 11
