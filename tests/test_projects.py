def test_create_project(client):
    r = client.post("/api/projects", json={"name": "backtests"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "backtests"
    assert "id" in data


def test_create_project_duplicate(client):
    client.post("/api/projects", json={"name": "backtests"})
    r = client.post("/api/projects", json={"name": "backtests"})
    assert r.status_code == 409


def test_list_projects(client):
    client.post("/api/projects", json={"name": "p1"})
    client.post("/api/projects", json={"name": "p2"})
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_project(client):
    created = client.post("/api/projects", json={"name": "p1"}).json()
    r = client.get(f"/api/projects/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "p1"


def test_get_project_not_found(client):
    r = client.get("/api/projects/does-not-exist")
    assert r.status_code == 404


def test_delete_project(client):
    created = client.post("/api/projects", json={"name": "p1"}).json()
    r = client.delete(f"/api/projects/{created['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/projects/{created['id']}").status_code == 404
