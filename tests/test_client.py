import httpx
import pytest

from fantomex.client import FantomexClient, FantomexClientError, ResultPipeline


@pytest.fixture
def transport():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/projects" and request.method == "POST":
            return httpx.Response(201, json={"id": "proj_123", "name": "demo"})
        if request.url.path == "/api/projects" and request.method == "GET":
            return httpx.Response(200, json=[{"id": "proj_123"}, {"id": "proj_456"}])
        if request.url.path == "/api/runs/missing":
            return httpx.Response(404, json={"detail": "Run not found"})
        if request.url.path == "/health":
            return httpx.Response(200, text="ok")
        return httpx.Response(500, json={"detail": "unexpected"})

    return httpx.MockTransport(handler)


def test_client_pipeable_results(transport):
    client = FantomexClient(base_url="http://testserver", transport=transport)

    result = client.create_project(name="demo", pipe=True)
    assert isinstance(result, ResultPipeline)

    project_name = result.pipe(lambda payload: payload["name"]).unwrap()
    assert project_name == "demo"


def test_client_error_contains_status_and_payload(transport):
    client = FantomexClient(base_url="http://testserver", transport=transport)

    with pytest.raises(FantomexClientError) as exc:
        client.get_run("missing")

    assert exc.value.status_code == 404
    assert exc.value.detail == {"detail": "Run not found"}


def test_request_normalizes_non_json_payload(transport):
    client = FantomexClient(base_url="http://testserver", transport=transport)

    payload = client._request("GET", "/health")

    assert payload == {"raw": "ok"}
