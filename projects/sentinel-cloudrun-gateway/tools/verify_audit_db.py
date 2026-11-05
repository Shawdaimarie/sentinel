"""Check per-tenant audit hash chains on a database without calling the HTTP API."""
import hashlib
import hmac
import json
import os

import psycopg

url = os.environ["DATABASE_URL"]
with psycopg.connect(url) as connection:
    rows = connection.execute("SELECT event_id,ts,actor,tenant_id,action,resource,decision,detail,prev_hash,event_hash FROM audit_events ORDER BY tenant_id,seq").fetchall()
heads = {}
for row in rows:
    event_id, ts, actor, tenant, action, resource, decision, detail, previous, digest = row
    expected_previous = heads.get(tenant, "0" * 64)
    canonical = json.dumps([event_id, ts.isoformat(), actor, tenant, action, resource, decision, detail, previous], sort_keys=True, separators=(",", ":"))
    if previous != expected_previous or not hmac.compare_digest(hashlib.sha256(canonical.encode()).hexdigest(), digest):
        raise SystemExit(f"FAIL: audit hash chain for tenant {tenant} at event {event_id}")
    heads[tenant] = digest
print(f"PASS: {len(rows)} audit events verified across {len(heads)} tenant chains")
