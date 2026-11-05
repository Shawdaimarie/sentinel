"""Inject an audit-write failure and prove protected execution rolls back atomically."""
import json
import os
import subprocess
import urllib.error
import urllib.request
import uuid

BASE = os.getenv("SENTINEL_BASE_URL", "http://127.0.0.1:8080")
TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION sentinel_test_fail_execute_audit() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.action = 'customer.update_note.execute' THEN
    RAISE EXCEPTION 'injected audit persistence failure';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER sentinel_test_fail_execute_audit
BEFORE INSERT ON audit_events
FOR EACH ROW EXECUTE FUNCTION sentinel_test_fail_execute_audit();
"""
DROP_SQL = "DROP TRIGGER IF EXISTS sentinel_test_fail_execute_audit ON audit_events; DROP FUNCTION IF EXISTS sentinel_test_fail_execute_audit();"


def call(path, token="demo-alice", body=None, headers=None, method=None):
    request_headers = {"Authorization": "Bearer " + token, **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = raw
        return error.code, result


def sql(statement):
    subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", "sentinel", "-d", "sentinel", "-c", statement],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def expect(status, path, **kwargs):
    actual, result = call(path, **kwargs)
    assert actual == status, (path, actual, result)
    return result


def main():
    target = "c-101"
    before = expect(200, "/v1/tool-calls", body={"tool": "customer.read", "arguments": {"customer_id": target}})
    new_note = "rollback injection " + uuid.uuid4().hex[:8]
    proposal = expect(200, "/v1/tool-calls", body={"tool": "customer.update_note", "arguments": {"customer_id": target, "new_note": new_note}})
    approval_id = proposal["approval_id"]
    expect(200, f"/v1/approvals/{approval_id}/decision", token="demo-admin", body={"decision": "approve"})
    capability = expect(200, f"/v1/approvals/{approval_id}/capability", token="demo-alice", body={})["capability"]
    key = "rollback-" + uuid.uuid4().hex
    sql(TRIGGER_SQL)
    failed_status, _ = call(
        f"/v1/approvals/{approval_id}/execute",
        headers={"X-Sentinel-Capability": capability, "Idempotency-Key": key},
        method="POST",
    )
    assert failed_status == 500, failed_status
    sql(DROP_SQL)

    after_failure = expect(200, "/v1/tool-calls", body={"tool": "customer.read", "arguments": {"customer_id": target}})
    approvals = expect(200, "/v1/approvals", token="demo-admin")["approvals"]
    row = next(item for item in approvals if item["approval_id"] == approval_id)
    assert after_failure["note"] == before["note"] and after_failure["version"] == before["version"], after_failure
    assert row["state"] == "approved", row

    restored_operation = expect(
        200,
        f"/v1/approvals/{approval_id}/execute",
        headers={"X-Sentinel-Capability": capability, "Idempotency-Key": key},
        method="POST",
    )
    assert restored_operation["note"] == new_note
    assert expect(200, "/v1/audit/verify")["valid"]
    print("PASS: injected audit-write failure rolled back record, approval, idempotency, and audit; retry committed once")


if __name__ == "__main__":
    main()
