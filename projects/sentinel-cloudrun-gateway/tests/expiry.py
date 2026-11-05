"""Run with SENTINEL_CAPABILITY_TTL_SECONDS=1 docker compose up --force-recreate."""
import json
import os
import time
import urllib.error
import urllib.request

BASE = os.getenv("SENTINEL_BASE_URL", "http://127.0.0.1:8080")


def call(path, token, body=None, headers=None, method=None):
    h = {"Authorization": "Bearer " + token, **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    if data:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    status, task = call("/v1/demo/agent-task", "demo-alice", {"customer_id":"c-101","new_note":"expires"}, method="POST")
    assert status == 200, task
    aid = task["update_request"]["approval_id"]
    status, decision = call(f"/v1/approvals/{aid}/decision", "demo-admin", {"decision":"approve"}, method="POST")
    assert status == 200, decision
    status, cap = call(f"/v1/approvals/{aid}/capability", "demo-alice", {}, method="POST")
    assert status == 200, cap
    time.sleep(2)
    status, result = call(f"/v1/approvals/{aid}/execute", "demo-alice", headers={"X-Sentinel-Capability":cap["capability"],"Idempotency-Key":"expiry-check"}, method="POST")
    assert status == 403, (status, result)
    print("PASS: expired capability rejected")


if __name__ == "__main__":
    main()
