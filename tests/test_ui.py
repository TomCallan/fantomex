import pytest


@pytest.fixture
def project(client):
    r = client.post("/api/projects", json={"name": "ui-tests", "description": "UI route tests"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def run(project, client):
    r = client.post(
        f"/api/projects/{project['id']}/runs",
        json={"name": "run-1", "params": {"lr": 0.01}},
    )
    assert r.status_code == 201
    return r.json()


def test_project_list_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Projects" in r.text


def test_canonical_run_list_page(project, client):
    r = client.get(f"/p/{project['name']}")
    assert r.status_code == 200
    assert project["name"] in r.text


def test_canonical_run_detail_page(project, run, client):
    r = client.get(f"/p/{project['name']}/r/{run['id']}")
    assert r.status_code == 200
    assert run["name"] in r.text
    assert "lr" in r.text


def test_canonical_run_detail_page_with_timeseries_metrics(project, run, client):
    # This regression test catches the undefined `none` name in ui.py.
    r = client.post(
        f"/api/runs/{run['id']}/metrics",
        json={
            "metrics": [
                {"key": "accuracy", "value": 0.9},
                {"key": "loss", "value": 0.5, "step": 1},
                {"key": "loss", "value": 0.4, "step": 2},
            ]
        },
    )
    assert r.status_code == 201

    r = client.get(f"/p/{project['name']}/r/{run['id']}")
    assert r.status_code == 200
    assert "loss" in r.text


def test_legacy_project_redirect(project, client):
    r = client.get(f"/{project['name']}", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == f"/p/{project['name']}"


def test_legacy_run_redirect(project, run, client):
    r = client.get(f"/{project['name']}/{run['id']}", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == f"/p/{project['name']}/r/{run['name']}"


def test_old_api_style_run_redirect(project, run, client):
    r = client.get(f"/runs/{run['id']}", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == f"/p/{project['name']}/r/{run['name']}"


def test_old_api_style_run_list_redirect(project, client):
    r = client.get(f"/projects/{project['id']}/runs", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == f"/p/{project['name']}"
