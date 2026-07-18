from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Any

import httpx


class FantomexClientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, detail: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class ResultPipeline:
    def __init__(self, value: Any):
        self.value = value

    def pipe(self, transform, *args, **kwargs) -> ResultPipeline:
        return ResultPipeline(transform(self.value, *args, **kwargs))

    def unwrap(self) -> Any:
        return self.value


class Pipeable:
    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, pipe: bool = False, **kwargs):
            result = fn(*args, **kwargs)
            return ResultPipeline(result) if pipe else result

        return wrapper


pipeable = Pipeable()


class FantomexClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout: float = 30,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout, transport=transport)

    def _parse_payload(self, response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return {}

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if isinstance(payload, (dict, list)):
            return payload
        return {"value": payload}

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise FantomexClientError(f"Request failed for {method} {path}: {exc}") from exc

        payload = self._parse_payload(response)
        if response.is_error:
            raise FantomexClientError(
                f"HTTP {response.status_code} for {method} {path}",
                status_code=response.status_code,
                detail=payload,
            )

        return payload

    @pipeable
    def create_project(
        self,
        name: str,
        description: str | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict:
        payload = {"name": name}
        if description is not None:
            payload["description"] = description
        if tags is not None:
            payload["tags"] = tags
        if meta is not None:
            payload["meta"] = meta
        return self._request("POST", "/api/projects", json=payload)

    @pipeable
    def list_projects(self) -> list[dict]:
        return self._request("GET", "/api/projects")

    @pipeable
    def start_run(
        self,
        project_id: str,
        name: str | None = None,
        params: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if params is not None:
            payload["params"] = params
        if tags is not None:
            payload["tags"] = tags
        if meta is not None:
            payload["meta"] = meta
        return self._request("POST", f"/api/projects/{project_id}/runs", json=payload)

    @pipeable
    def list_runs(
        self,
        project_id: str,
        status: str | None = None,
        tag: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        params = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if tag is not None:
            params["tag"] = tag
        return self._request("GET", f"/api/projects/{project_id}/runs", params=params)

    @pipeable
    def get_run(self, run_id: str) -> dict:
        return self._request("GET", f"/api/runs/{run_id}")

    @pipeable
    def update_run(
        self,
        run_id: str,
        status: str | None = None,
        params: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {}
        if status is not None:
            payload["status"] = status
        if params is not None:
            payload["params"] = params
        if tags is not None:
            payload["tags"] = tags
        if meta is not None:
            payload["meta"] = meta
        return self._request("PATCH", f"/api/runs/{run_id}", json=payload)

    @pipeable
    def log_metric(
        self,
        run_id: str,
        key: str,
        value: float,
        step: int | None = None,
        timestamp: datetime | None = None,
    ) -> list[dict]:
        metrics = [{"key": key, "value": value}]
        if step is not None:
            metrics[0]["step"] = step
        if timestamp is not None:
            metrics[0]["timestamp"] = timestamp.isoformat()
        return self._request("POST", f"/api/runs/{run_id}/metrics", json={"metrics": metrics})

    @pipeable
    def log_metrics(self, run_id: str, metrics: list[dict]) -> list[dict]:
        return self._request("POST", f"/api/runs/{run_id}/metrics", json={"metrics": metrics})

    @pipeable
    def get_metrics(
        self,
        run_id: str,
        key: str | None = None,
        timeseries: bool | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if key is not None:
            params["key"] = key
        if timeseries is not None:
            params["timeseries"] = "true" if timeseries else "false"
        return self._request("GET", f"/api/runs/{run_id}/metrics", params=params)

    @pipeable
    def log_artifact(
        self,
        run_id: str,
        name: str,
        type: str,
        uri: str,
        size_bytes: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"name": name, "type": type, "uri": uri}
        if size_bytes is not None:
            payload["size_bytes"] = size_bytes
        if meta is not None:
            payload["meta"] = meta
        return self._request("POST", f"/api/runs/{run_id}/artifacts", json=payload)

    @pipeable
    def list_artifacts(self, run_id: str) -> list[dict]:
        return self._request("GET", f"/api/runs/{run_id}/artifacts")

    @pipeable
    def upload_artifact(self, run_id: str, path: str, type: str = "file") -> dict:
        with open(path, "rb") as file_handle:
            return self._request(
                "POST",
                f"/api/runs/{run_id}/artifacts/upload",
                params={"type": type},
                files={"file": file_handle},
            )

    @pipeable
    def add_note(self, run_id: str, content: str) -> dict:
        return self._request("POST", f"/api/runs/{run_id}/notes", json={"content": content})

    @pipeable
    def list_notes(self, run_id: str) -> list[dict]:
        return self._request("GET", f"/api/runs/{run_id}/notes")

    @pipeable
    def compare_runs(self, run_ids: list[str]) -> dict:
        return self._request("POST", "/api/runs/compare", json={"run_ids": run_ids})

    @pipeable
    def summarize_runs(
        self,
        project_id: str,
        status: str | None = None,
        tag: str | None = None,
        metric_keys: list[str] | None = None,
    ) -> dict:
        params: dict[str, Any] = {"project_id": project_id}
        if status is not None:
            params["status"] = status
        if tag is not None:
            params["tag"] = tag
        if metric_keys is not None:
            params["metric_keys"] = metric_keys
        return self._request("GET", "/api/runs/summarize", params=params)

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
