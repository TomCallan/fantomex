from datetime import datetime
from typing import Any

import httpx


class FantomexClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=30)

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
        r = self.client.post("/api/projects", json=payload)
        r.raise_for_status()
        return r.json()

    def list_projects(self) -> list[dict]:
        r = self.client.get("/api/projects")
        r.raise_for_status()
        return r.json()

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
        r = self.client.post(f"/api/projects/{project_id}/runs", json=payload)
        r.raise_for_status()
        return r.json()

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
        r = self.client.get(f"/api/projects/{project_id}/runs", params=params)
        r.raise_for_status()
        return r.json()

    def get_run(self, run_id: str) -> dict:
        r = self.client.get(f"/api/runs/{run_id}")
        r.raise_for_status()
        return r.json()

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
        r = self.client.patch(f"/api/runs/{run_id}", json=payload)
        r.raise_for_status()
        return r.json()

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
        r = self.client.post(f"/api/runs/{run_id}/metrics", json={"metrics": metrics})
        r.raise_for_status()
        return r.json()

    def log_metrics(self, run_id: str, metrics: list[dict]) -> list[dict]:
        r = self.client.post(f"/api/runs/{run_id}/metrics", json={"metrics": metrics})
        r.raise_for_status()
        return r.json()

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
        r = self.client.get(f"/api/runs/{run_id}/metrics", params=params)
        r.raise_for_status()
        return r.json()

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
        r = self.client.post(f"/api/runs/{run_id}/artifacts", json=payload)
        r.raise_for_status()
        return r.json()

    def list_artifacts(self, run_id: str) -> list[dict]:
        r = self.client.get(f"/api/runs/{run_id}/artifacts")
        r.raise_for_status()
        return r.json()

    def upload_artifact(self, run_id: str, path: str, type: str = "file") -> dict:
        with open(path, "rb") as f:
            r = self.client.post(
                f"/api/runs/{run_id}/artifacts/upload",
                params={"type": type},
                files={"file": f},
            )
        r.raise_for_status()
        return r.json()

    def add_note(self, run_id: str, content: str) -> dict:
        r = self.client.post(f"/api/runs/{run_id}/notes", json={"content": content})
        r.raise_for_status()
        return r.json()

    def list_notes(self, run_id: str) -> list[dict]:
        r = self.client.get(f"/api/runs/{run_id}/notes")
        r.raise_for_status()
        return r.json()

    def compare_runs(self, run_ids: list[str]) -> dict:
        r = self.client.post("/api/runs/compare", json={"run_ids": run_ids})
        r.raise_for_status()
        return r.json()

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
        r = self.client.get("/api/runs/summarize", params=params)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
