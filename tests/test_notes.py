import pytest


@pytest.fixture
def project(client):
    return client.post("/api/projects", json={"name": "note-tests"}).json()


@pytest.fixture
def run(project, client):
    return client.post(f"/api/projects/{project['id']}/runs", json={"name": "run-1"}).json()


def test_add_note(run, client):
    r = client.post(f"/api/runs/{run['id']}/notes", json={"content": "Changed window to 20"})
    assert r.status_code == 201
    assert r.json()["content"] == "Changed window to 20"


def test_list_notes(run, client):
    client.post(f"/api/runs/{run['id']}/notes", json={"content": "note 1"})
    client.post(f"/api/runs/{run['id']}/notes", json={"content": "note 2"})
    r = client.get(f"/api/runs/{run['id']}/notes")
    assert len(r.json()) == 2
