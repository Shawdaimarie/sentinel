# Local operator and reviewer guide

## Start the demonstration

From the project root, run `docker compose up --build -d`, then open [http://localhost:5173](http://localhost:5173). Wait until the top-right status reads **GATEWAY HEALTHY**. The OpenAPI explorer is available at [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs).

## Walk through an authorized action

1. Select Alice · Tenant A and run a task for `c-100` with a proposed note. The trace shows search, read, and a pending update request.
2. Inspect the retrieved `doc-evil` text. Its response is marked untrusted and asks for a different customer update without approval.
3. In the approval queue, inspect the exact proposed customer, note, record version and action digest. Switch to Admin · Tenant A and approve or deny.
4. Switch back to Alice and execute once. A new approval is required for the separately captured prior note.
5. Request restoration, approve it as Admin, and execute as Alice to reverse the change through the same gateway.
6. Click **Verify audit chain** to see tenant-scoped events and integrity verification. For API-level idempotency and replay/race checks, run `python3 tests/smoke.py`.

The browser identity selector is a local fixture selector, not a login system. Do not enter real records, credentials, or production tokens.

## Shutdown and test reset

`docker compose down` stops containers and removes the ephemeral Compose database container. It does not affect other local PostgreSQL instances. The tests exercise only synthetic records. `SENTINEL_CAPABILITY_TTL_SECONDS=1 docker compose up -d` is an expiry-test setting; return to normal with `docker compose down` then `docker compose up -d`.

## Incident and rollback notes

If the gateway is unhealthy, protected actions fail because no execution endpoint is available. Inspect `docker compose logs gateway db`; fix the underlying configuration and recreate the gateway. The local database has no persistent volume, backup, or restore path. For this prototype, shutdown is the recovery action. Production requires documented backup/restore, migration rollback and previous-revision Cloud Run rollback checks before deployment.
