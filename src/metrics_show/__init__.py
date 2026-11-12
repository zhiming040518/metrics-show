"""Small client for a compatible, self-hosted metrics endpoint."""

import os
from collections.abc import Iterator, Sequence
from typing import Literal
from uuid import UUID, uuid4

import httpx

from .models import Batch, Event, Metric

__all__ = ["Batch", "Event", "Metric", "MetricsClient"]


class MetricsClient:
    def __init__(
        self, url: str | None = None, token: str | None = None, *, transport=None
    ):
        endpoint = url or os.getenv("METRICS_SHOW_URL")
        credential = token or os.getenv("METRICS_SHOW_TOKEN")
        if not endpoint or not credential:
            raise ValueError(
                "Set METRICS_SHOW_URL and METRICS_SHOW_TOKEN, or pass both to the client"
            )
        target = httpx.URL(endpoint)
        if (
            target.scheme not in {"http", "https"}
            or not target.host
            or target.userinfo
            or target.query
            or target.fragment
        ):
            raise ValueError(
                "Use an HTTP(S) service URL without credentials, a query, or a fragment"
            )
        self._http = httpx.Client(
            base_url=str(target).rstrip("/") + "/api/v1/",
            headers={"Authorization": f"Bearer {credential}"},
            timeout=10,
            follow_redirects=False,
            transport=transport,
        )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._http.close()

    def _request(self, method, path, **kwargs):
        response = self._http.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    def create_run(
        self,
        project: str,
        name: str,
        *,
        run_id: UUID | None = None,
        config: dict | None = None,
    ) -> UUID:
        run_id = run_id or uuid4()
        self._request(
            "POST",
            "runs",
            json={
                "id": str(run_id),
                "project": project,
                "name": name,
                "config": config or {},
                "controllable": False,
            },
        )
        return run_id

    def define_metric(self, run_id: UUID, metric: Metric) -> None:
        self._request(
            "PUT", f"runs/{run_id}/metrics", json=metric.model_dump(mode="json")
        )

    def submit(self, run_id: UUID, events: Sequence[Event]) -> None:
        batch = Batch(events=list(events))
        self._request(
            "POST", f"runs/{run_id}/events", json=batch.model_dump(mode="json")
        )

    def finish(
        self,
        run_id: UUID,
        status: Literal["completed", "failed", "stopped"] = "completed",
    ) -> None:
        self._request("POST", f"runs/{run_id}/heartbeat", json={"status": status})

    def iter_events(self, run_id: UUID, *, page_size: int = 500) -> Iterator[Event]:
        if not 1 <= page_size <= 10000:
            raise ValueError("page_size must be between 1 and 10000")
        cursor = 0
        while True:
            page = self._request(
                "GET",
                f"runs/{run_id}/events",
                params={"after": cursor, "limit": page_size},
            )
            yield from (Event.model_validate(event) for event in page["events"])
            if not page["has_more"]:
                return
            if page["next"] <= cursor:
                raise ValueError("The server did not advance the event cursor")
            cursor = page["next"]
