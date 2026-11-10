"""Small documented HTTP client; only communicates with the configured gateway."""
from typing import Any, Dict, Optional
import requests


class SentinelClient:
    def __init__(self, base_url: str, token: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.timeout = timeout

    def tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(self.base_url + "/v1/tool-calls", json={"tool": name, "arguments": arguments}, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def decide(self, approval_id: str, decision: str) -> Dict[str, Any]:
        r = requests.post(self.base_url + f"/v1/approvals/{approval_id}/decision", json={"decision": decision}, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def execute(self, approval_id: str, capability: str, idempotency_key: str) -> Dict[str, Any]:
        headers = {**self.headers, "X-Sentinel-Capability": capability, "Idempotency-Key": idempotency_key}
        r = requests.post(self.base_url + f"/v1/approvals/{approval_id}/execute", headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
