import pytest


@pytest.fixture
def project(client):
    r = client.post("/api/projects", json={"name": "backtests"})
    return r.json()


def test_start_run(project, client):
    r = client.post(
        f"/api/projects/{project['id']}/runs",
        json={"name": "run-1", "params": {"strategy": "momentum", "window": 20}},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "running"
    assert data["project_id"] == project["id"]
    assert data["params"]["strategy"] == "momentum"


def test_start_run_missing_project(client):
    r = client.post("/api/projects/nonexistent/runs", json={"name": "run-1"})
    assert r.status_code == 404


def test_list_runs(project, client):
    client.post(f"/api/projects/{project['id']}/runs", json={"name": "a"})
    client.post(f"/api/projects/{project['id']}/runs", json={"name": "b"})
    r = client.get(f"/api/projects/{project['id']}/runs")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_run(project, client):
    run = client.post(f"/api/projects/{project['id']}/runs", json={"name": "r"}).json()
    r = client.get(f"/api/runs/{run['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == run["id"]


def test_update_run_status(project, client):
    run = client.post(f"/api/projects/{project['id']}/runs", json={"name": "r"}).json()
    r = client.patch(f"/api/runs/{run['id']}", json={"status": "completed"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["end_time"] is not None


def test_log_metrics(project, client):
    run = client.post(f"/api/projects/{project['id']}/runs", json={"name": "r"}).json()
    r = client.post(
        f"/api/runs/{run['id']}/metrics",
        json={"metrics": [{"key": "sharpe", "value": 1.5}, {"key": "equity", "value": 1000, "step": 1}]},
    )
    assert r.status_code == 201
    assert len(r.json()) == 2

    r = client.get(f"/api/runs/{run['id']}/metrics?timeseries=true")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["key"] == "equity"

    r = client.get(f"/api/runs/{run['id']}/metrics?timeseries=false")
    assert len(r.json()) == 1
    assert r.json()[0]["key"] == "sharpe"


def test_log_metrics_run_not_found(client):
    r = client.post("/api/runs/nonexistent/metrics", json={"metrics": [{"key": "x", "value": 1}]})
    assert r.status_code == 404
