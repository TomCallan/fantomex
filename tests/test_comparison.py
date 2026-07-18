import pytest


@pytest.fixture
def project(client):
    return client.post("/api/projects", json={"name": "comparison-tests"}).json()


@pytest.fixture
def runs(project, client):
    runs = []
    for i in range(3):
        r = client.post(
            f"/api/projects/{project['id']}/runs",
            json={"name": f"run-{i}", "params": {"window": 10 + i}, "tags": ["v1"]},
        ).json()
        client.post(
            f"/api/runs/{r['id']}/metrics",
            json={
                "metrics": [
                    {"key": "sharpe", "value": 1.0 + i * 0.1},
                    {"key": "equity", "value": 1000 + i, "step": 1},
                ]
            },
        )
        client.patch(f"/api/runs/{r['id']}", json={"status": "completed"})
        runs.append(r)
    return runs


def test_compare_runs(runs, client):
    ids = [r["id"] for r in runs[:2]]
    r = client.post("/api/runs/compare", json={"run_ids": ids})
    assert r.status_code == 200
    data = r.json()
    assert len(data["runs"]) == 2
    assert "sharpe" in data["metric_summary"]
    assert len(data["metric_summary"]["sharpe"]["values"]) == 2


def test_summarize_runs(runs, project, client):
    r = client.get(f"/api/runs/summarize?project_id={project['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["total_runs"] == 3
    assert data["by_status"]["completed"] == 3
    assert "v1" in data["by_tag"]
    assert "sharpe" in data["metric_stats"]
