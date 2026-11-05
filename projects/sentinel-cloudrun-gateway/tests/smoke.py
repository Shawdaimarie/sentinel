"""Live local gateway invariants; run against docker compose up."""
import json
import http.client
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

BASE = os.getenv("SENTINEL_BASE_URL", "http://127.0.0.1:8080")


def request(path, token="demo-alice", body=None, headers=None, method=None):
    h = {"Authorization": "Bearer " + token, **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    if data:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def expect(status, path, **kwargs):
    actual, body = request(path, **kwargs)
    assert actual == status, (path, actual, body)
    return body


def chunked_oversize():
    target = urlsplit(BASE)
    conn = http.client.HTTPConnection(target.hostname, target.port or 80, timeout=5)
    conn.putrequest("POST", "/v1/tool-calls")
    conn.putheader("Authorization", "Bearer demo-alice")
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Transfer-Encoding", "chunked")
    conn.endheaders()
    payload = b"x" * 40000
    conn.send(f"{len(payload):X}\r\n".encode() + payload + b"\r\n0\r\n\r\n")
    response = conn.getresponse()
    body = json.loads(response.read())
    conn.close()
    return response.status, body


def main():
    expect(200, "/health")
    # Tenant isolation: Bob cannot read Alice's customer, with no cross-tenant leak.
    expect(404, "/v1/tool-calls", token="demo-bob", body={"tool":"customer.read","arguments":{"customer_id":"c-100"}})
    # Unknown tools and schema extension fail closed.
    expect(403, "/v1/tool-calls", body={"tool":"customer.delete","arguments":{}})
    expect(422, "/v1/tool-calls", body={"tool":"customer.read","arguments":{"customer_id":"c-100","tenant_id":"tenant-a"}})
    assert chunked_oversize()[0] == 413
    # Retrieved malicious text is returned as untrusted; it grants no authorization.
    d = expect(200, "/v1/tool-calls", body={"tool":"document.search","arguments":{"query":"OVERRIDE"}})
    assert d["documents"] and all(x["untrusted"] for x in d["documents"])
    # Complete exact-action request -> separate admin approval -> owner execution.
    admin_request = expect(200, "/v1/tool-calls", token="demo-admin", body={"tool":"customer.update_note","arguments":{"customer_id":"c-100","new_note":"self approval must fail"}})
    expect(403, f"/v1/approvals/{admin_request['approval_id']}/decision", token="demo-admin", body={"decision":"approve"})
    original = expect(200, "/v1/tool-calls", body={"tool":"customer.read","arguments":{"customer_id":"c-100"}})["note"]
    task = expect(200, "/v1/demo/agent-task", body={"customer_id":"c-100","new_note":"approved smoke change"})
    approval_id = task["update_request"]["approval_id"]
    action = expect(200, "/v1/approvals", token="demo-admin")["approvals"]
    assert next(a for a in action if a["approval_id"] == approval_id)["action"]["new_note"] == "approved smoke change"
    approval = expect(200, f"/v1/approvals/{approval_id}/decision", token="demo-admin", body={"decision":"approve"})
    assert "capability" not in approval
    cap = expect(200, f"/v1/approvals/{approval_id}/capability", body={})["capability"]
    expect(403, f"/v1/approvals/{approval_id}/capability", token="demo-admin", body={})
    headers = {"X-Sentinel-Capability": cap, "Idempotency-Key":"smoke-once"}
    result = expect(200, f"/v1/approvals/{approval_id}/execute", headers=headers, method="POST", body={"arguments":{"customer_id":"c-101","new_note":"substituted after approval"}})
    assert result["note"] == "approved smoke change"
    retry = expect(200, f"/v1/approvals/{approval_id}/execute", headers=headers, method="POST")
    assert retry == result
    # Explicit human denial produces no capability and cannot be executed.
    denied_request = expect(200, "/v1/tool-calls", body={"tool":"customer.update_note","arguments":{"customer_id":"c-100","new_note":"must remain denied"}})
    denied_id = denied_request["approval_id"]
    expect(200, f"/v1/approvals/{denied_id}/decision", token="demo-admin", body={"decision":"deny"})
    denied_rows = expect(200, "/v1/approvals", token="demo-admin")["approvals"]
    assert next(a for a in denied_rows if a["approval_id"] == denied_id)["state"] == "denied"
    expect(403, f"/v1/approvals/{denied_id}/execute", headers={"X-Sentinel-Capability":"","Idempotency-Key":"denied-no-capability"}, method="POST")
    # Reversal is a new exact action and requires a new approval.
    restore_request = expect(200, "/v1/tool-calls", body={"tool":"customer.update_note","arguments":{"customer_id":"c-100","new_note":original}})
    restore_id = restore_request["approval_id"]
    expect(200, f"/v1/approvals/{restore_id}/decision", token="demo-admin", body={"decision":"approve"})
    restore_cap = expect(200, f"/v1/approvals/{restore_id}/capability", body={})["capability"]
    restored = expect(200, f"/v1/approvals/{restore_id}/execute", headers={"X-Sentinel-Capability":restore_cap,"Idempotency-Key":"smoke-restore"}, method="POST")
    assert restored["note"] == original
    expect(403, f"/v1/approvals/{approval_id}/execute", headers={"X-Sentinel-Capability":cap,"Idempotency-Key":"smoke-replay"}, method="POST")
    expect(403, f"/v1/approvals/{approval_id}/execute", token="demo-admin", headers={"X-Sentinel-Capability":cap,"Idempotency-Key":"wrong-actor"}, method="POST")
    def concurrent_wrong_actor(index):
        return request(f"/v1/approvals/{approval_id}/execute", token="demo-admin", headers={"X-Sentinel-Capability":cap,"Idempotency-Key":f"wrong-actor-{index}"}, method="POST")
    denial_count = 32  # Exceeds the configured DB pool size; each denial must free its lock before auditing.
    with ThreadPoolExecutor(max_workers=denial_count) as pool:
        denied_race = list(pool.map(concurrent_wrong_actor, range(denial_count)))
    assert [status for status, _ in denied_race] == [403] * denial_count, denied_race
    denial_events = expect(200, "/v1/audit/events")["events"]
    assert sum(e["action"] == "approval.execute" and e["resource"] == approval_id and e["decision"] == "deny" for e in denial_events) >= denial_count
    # Same approved capability submitted concurrently with distinct keys has one winner.
    raced = expect(200, "/v1/demo/agent-task", body={"customer_id":"c-100","new_note":"race smoke change"})
    race_id = raced["update_request"]["approval_id"]
    expect(200, f"/v1/approvals/{race_id}/decision", token="demo-admin", body={"decision":"approve"})
    race_cap = expect(200, f"/v1/approvals/{race_id}/capability", body={})["capability"]
    def race(key):
        return request(f"/v1/approvals/{race_id}/execute", headers={"X-Sentinel-Capability":race_cap,"Idempotency-Key":key}, method="POST")
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(race, ["race-a", "race-b"]))
    assert sorted(x[0] for x in outcomes) == [200, 403], outcomes
    # Same-key concurrent retries must both receive exactly the committed response.
    same = expect(200, "/v1/demo/agent-task", body={"customer_id":"c-100","new_note":"same key concurrent"})
    same_id = same["update_request"]["approval_id"]
    expect(200, f"/v1/approvals/{same_id}/decision", token="demo-admin", body={"decision":"approve"})
    same_cap = expect(200, f"/v1/approvals/{same_id}/capability", body={})["capability"]
    def same_retry(_):
        return request(f"/v1/approvals/{same_id}/execute", headers={"X-Sentinel-Capability":same_cap,"Idempotency-Key":"same-key"}, method="POST")
    with ThreadPoolExecutor(max_workers=2) as pool:
        same_outcomes = list(pool.map(same_retry, [1, 2]))
    assert [x[0] for x in same_outcomes] == [200, 200], same_outcomes
    assert same_outcomes[0][1] == same_outcomes[1][1], same_outcomes
    # An approved action becomes stale if another approved change updates the row first.
    stale_task = expect(200, "/v1/demo/agent-task", body={"customer_id":"c-100","new_note":"stale approval"})
    stale_id = stale_task["update_request"]["approval_id"]
    fresh_task = expect(200, "/v1/demo/agent-task", body={"customer_id":"c-100","new_note":"fresh approval wins"})
    fresh_id = fresh_task["update_request"]["approval_id"]
    expect(200, f"/v1/approvals/{fresh_id}/decision", token="demo-admin", body={"decision":"approve"})
    fresh_cap = expect(200, f"/v1/approvals/{fresh_id}/capability", body={})["capability"]
    expect(200, f"/v1/approvals/{fresh_id}/execute", headers={"X-Sentinel-Capability":fresh_cap,"Idempotency-Key":"fresh-version"}, method="POST")
    expect(200, f"/v1/approvals/{stale_id}/decision", token="demo-admin", body={"decision":"approve"})
    stale_cap = expect(200, f"/v1/approvals/{stale_id}/capability", body={})["capability"]
    expect(409, f"/v1/approvals/{stale_id}/execute", headers={"X-Sentinel-Capability":stale_cap,"Idempotency-Key":"stale-version"}, method="POST")
    tenant_a_audit = expect(200, "/v1/audit/verify")
    tenant_b_audit = expect(200, "/v1/audit/verify", token="demo-bob")
    assert tenant_a_audit["valid"] and tenant_b_audit["valid"]
    events_b = expect(200, "/v1/audit/events", token="demo-bob")
    assert all("Ada Lovelace" not in json.dumps(e) for e in events_b["events"])
    assert any(e["decision"] == "deny" for e in expect(200, "/v1/audit/events")["events"])
    assert any(e["action"] == "gateway.security_event" for e in expect(200, "/v1/audit/events")["events"])
    print("PASS: health, bounds/schema, allowlist, tenant isolation, untrusted retrieval, approval binding, idempotency (serial and concurrent), approved reversal, replay denial, double-spend race, stale-version denial, tenant-scoped audit, denied-decision trace, integrity verification")


if __name__ == "__main__":
    main()
