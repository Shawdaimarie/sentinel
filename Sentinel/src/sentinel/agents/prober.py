"""Prober agent.

Probes critical controls — currently HTTP endpoints — and records their
observed state against thresholds declared in policy. Probing on a schedule
is the difference between a control that was validated once and a control
that is known to hold now.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from sentinel.agents.base import Agent
from sentinel.http import make_client
from sentinel.models import ProbeResult


class Prober(Agent):
    name = "prober"

    def __init__(self, *args: Any, timeout: float = 10.0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = make_client(timeout)
        self.register("http.head", self._head)
        self.register("http.get", self._get)

    def _head(self, target: str, _: dict[str, Any]) -> httpx.Response:
        return self._client.head(target)

    def _get(self, target: str, _: dict[str, Any]) -> httpx.Response:
        return self._client.get(target)

    def probe(self, url: str) -> ProbeResult:
        thresholds = self.policy.thresholds(self.name)
        max_latency = float(thresholds.get("max_latency_ms", 2000))
        expected = set(thresholds.get("expected_status", [200]))

        started = time.perf_counter()
        try:
            record, response = self.act("http.head", url)
        except httpx.HTTPError as exc:
            return ProbeResult(
                target=url,
                status_code=None,
                latency_ms=None,
                healthy=False,
                detail=f"request failed: {exc.__class__.__name__}",
                audit_sequence=0,
            )
        latency = (time.perf_counter() - started) * 1000

        healthy = response.status_code in expected and latency <= max_latency
        detail = (
            "within thresholds"
            if healthy
            else f"status {response.status_code} or latency {latency:.0f}ms outside policy"
        )
        return ProbeResult(
            target=url,
            status_code=response.status_code,
            latency_ms=round(latency, 1),
            healthy=healthy,
            detail=detail,
            audit_sequence=record.sequence,
        )

    def close(self) -> None:
        self._client.close()
