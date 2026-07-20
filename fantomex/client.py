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
        api_key: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        headers = {}
        if api_key:
            headers["X-Fantomex-Api-Key"] = api_key
        self.client = httpx.Client(
            base_url=self.base_url, timeout=timeout, transport=transport, headers=headers
        )

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
        if self.api_key:
            headers = kwargs.get("headers", {})
            headers["X-Fantomex-Api-Key"] = self.api_key
            kwargs["headers"] = headers
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

    def get_or_create_project(self, name: str) -> dict:
        projects = self.list_projects()
        for p in projects:
            if p["name"] == name:
                return p
        return self.create_project(name=name)

    import contextlib
    @contextlib.contextmanager
    def run(
        self,
        project_name: str,
        run_name: str | None = None,
        params: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ):
        project = self.get_or_create_project(project_name)
        run_data = self.start_run(
            project_id=project["id"],
            name=run_name,
            params=params,
            tags=tags,
            meta=meta,
        )
        active_run = ActiveRun(self, project["id"], run_data["id"], run_data)
        try:
            yield active_run
            self.update_run(run_data["id"], status="completed")
        except Exception as exc:
            self.update_run(run_data["id"], status="failed")
            import traceback
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            self.add_note(run_data["id"], f"Run failed with error:\n{tb}")
            raise exc


class ActiveRun:
    def __init__(self, client: FantomexClient, project_id: str, run_id: str, run_data: dict):
        self.client = client
        self.project_id = project_id
        self.run_id = run_id
        self.run_data = run_data

    def log(self, metrics: dict[str, float], step: int | None = None) -> list[dict]:
        payload = []
        for k, v in metrics.items():
            item = {"key": k, "value": float(v)}
            if step is not None:
                item["step"] = step
            payload.append(item)
        return self.client.log_metrics(self.run_id, payload)

    def log_file(self, path: str, type: str = "file") -> dict:
        return self.client.upload_artifact(self.run_id, path, type=type)

    def log_plotly(self, fig, name: str) -> dict:
        import os
        import tempfile
        import json

        if not name.endswith(".plotly.json"):
            name = name.split(".")[0] + ".plotly.json"

        fig_json = None
        if hasattr(fig, "to_json"):
            fig_json = fig.to_json()
        elif isinstance(fig, dict):
            fig_json = json.dumps(fig)
        else:
            try:
                import plotly.io as pio
                fig_json = pio.to_json(fig)
            except (ImportError, ModuleNotFoundError) as exc:
                raise ImportError(
                    "Plotly is not installed. To log plotly figures, install plotly or pass a dictionary/object with a 'to_json' method."
                ) from exc

        temp_dir = tempfile.mkdtemp()
        dest_path = os.path.join(temp_dir, name)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(fig_json)

        try:
            result = self.client.upload_artifact(self.run_id, dest_path, type="plotly")
        finally:
            try:
                os.remove(dest_path)
                os.rmdir(temp_dir)
            except Exception:
                pass
        return result


