# SENTINEL local prototype

Local synthetic authorization gateway and trace explorer for document search and customer-record operations. All three tool operations pass through FastAPI; agents receive no database credential or direct tool route. The web app runs on `http://localhost:5173` and the gateway on `http://127.0.0.1:8080`.

## Run locally

Requirements: Docker with Compose. From the repository root, one command starts the database, gateway, and explorer:

```sh
docker compose up --build -d
```

Equivalent shortcut: `make demo`. `make test` runs the local regression scripts, including rate/replay/race/isolation/restoration/expiry checks; it resets only this project's disposable synthetic Compose database before and after the checks. The GitHub Actions workflow runs explorer build, dependency/secret scans and the same gateway checks on push and pull request.

Open `http://localhost:5173`. Demo identities: `demo-alice` (tenant A), `demo-admin` (tenant A approver), `demo-bob` (tenant B). To complete a workflow, run as Alice, approve the exact note change as Admin, switch back to Alice, execute once. The displayed document-search result labeled `untrusted` is deliberately malicious. Run `python3 tests/smoke.py` for live invariants, `python3 tests/rate_limit.py` for per-actor throttling, or `python3 tests/expiry.py` with a one-second TTL test configuration for expiration. Stop services with `docker compose down`; no host-mounted database volume is used.

## Security boundary and limitations

Local bearer tokens are demo fixtures and must never be used in deployment. The capability HMAC secret is demo-only. The container publishes only the gateway on loopback; PostgreSQL is not host-published and has no credentials supplied to an agent/client. Production needs OIDC/JWT verification, managed secrets, private networking, restricted Cloud Run identities, PostgreSQL managed service, object storage, rate limits, deployment hardening, backup/restore and rollback evidence. Hash-linked audit events detect row edits/reordering relative to the retained chain, but a privileged attacker able to rewrite all rows can recompute it. This is not tamper-proof storage or a security certification.

## Evaluation and docs

- `COMPETITIVE_REVIEW.md`, `TECHNICAL_REVIEW.md`, `EVIDENCE_REGISTER.md`: prerequisite reviews and G0 scope.
- `PROJECT_STATUS.md`, `TEST_REPORT.md`, `DEPLOYMENT_STATUS.md`: gate state, local checks, and production blockers.
- `SCORECARD.md`: the 20 five-point conditions required for a verified 100/100.
- `PUBLISHING_DRAFTS.md`: factual platform copy prepared for later review; nothing has been published.
- `evaluation/scenarios.jsonl`: 220 synthetic scenario rows; holdout attack families are labeled.
- `evaluation/README.md`: comparison and reporting protocol. No model performance result is claimed yet.
- `client/sentinel_client.py`: documented gateway-only HTTP client methods.
- `THREAT_MODEL.md`, `OPERATOR_GUIDE.md`, `DEPLOYMENT_STATUS.md`: security boundary and operational/release status.
- OpenAPI is served at `/docs`; health check at `/health`.
