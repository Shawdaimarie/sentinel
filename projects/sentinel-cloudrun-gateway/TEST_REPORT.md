# SENTINEL verification report

Date: 2026-11-04 (America/Chicago). Application source: commit `d2956cc`; final suite rerun from the public-repository integration branch. Environment: macOS host, Docker Compose, Python 3.12, PostgreSQL 16 Alpine, Node 22. The isolated test stack used a unique Compose project and disposable database; the existing local walkthrough database was preserved.

## Results

| Check | Result | Evidence |
|---|---|---|
| Scenario inventory | PASS | 220 rows: 110 legitimate and 110 adversarial across 12 attack families; 18 rows labeled in two holdout families. Inventory validation only; this is not an effectiveness score. |
| Clean end-to-end gateway workflow | PASS | `make test-isolated`: tenant isolation, input bounds/schema, tool allowlist, untrusted retrieval provenance, exact approval binding, separated requester/approver, approval and denial, owner-only capability retrieval/execution, approved restoration, replay/stale-version denial, audit integrity. |
| Concurrent authorization and idempotency | PASS | 32 parallel wrong-actor execution attempts all returned 403 and were audit-traced; concurrent same-key retries returned the same committed response; a distinct-key double-spend race had one winner. |
| Rate limiting | PASS | 60 permitted and 10 denied calls; denial recorded in audit. |
| Atomic rollback | PASS | Injected audit-write failure rolled back record, approval, idempotency, and audit changes; retry committed once. |
| Capability expiry | PASS | One-second capability expired and execution was rejected. |
| Migration permissions | PASS | Runtime database role has least-privilege table grants, append-only audit access, and no schema `CREATE`. |
| Backup and restore | PASS | PostgreSQL logical backup restored into a separate disposable database; table counts, migration record, and audit chains matched. |
| Gateway route load | PASS | Local deterministic fixtures: 1,000 requests per route, concurrency 10; 5,000/5,000 HTTP 200. p95: health 14.642 ms, auth mode 7.541 ms, tools 9.518 ms, approval queue 11.422 ms, audit verify 14.616 ms. Overall local throughput 1,501.05 requests/s. Cost and model inference are not applicable to this fixture run. |
| Cloud configuration package | PASS (mock only) | `sh infra/validate.sh`: GCP, AWS, Azure, and OCI formatting, provider schemas, and mocked guardrail checks passed. No account credentials or real infrastructure were used. |
| Authentication verification | PASS | 6 OIDC verifier tests, 4 signed IAP verifier tests, and 2 ASGI middleware tests (spoofed Authorization replacement and fail-closed identity mapping). |
| Python dependencies | PASS | `pip-audit` previously passed for gateway and client requirement files in Python 3.12 after updating pins. |
| JavaScript dependencies | PASS | `npm audit`: zero vulnerabilities. |
| Secret scan | PASS for contributed project | Gitleaks v8.24.2 scan of this project (~410 KB) with the narrow metadata-hash allowlist found no leaks. A combined repository scan also flags a pre-existing toy `token=...` string in `Sentinel/tests/test_data_gate.py:128`; it is outside this contribution and appears in an adversarial test prompt. |
| Explorer build | PASS | Production Vite build completed in the Docker image build. |
| Browser walkthrough | PASS | On the existing local demo: retrieved malicious document remained labeled untrusted; Admin approved the exact proposed update; Alice executed it; Alice requested restoration; Admin approved restoration; Alice executed it. Original note `Renewal in Q4` was restored at version 5; audit verification returned valid. This walkthrough uses local demo identities and synthetic data. |

Detailed machine-readable local load results are in [evaluation/performance-local.json](evaluation/performance-local.json). Run the clean suite with `make test-isolated`; it builds isolated containers, runs all checks above that are orchestrated by the script, and removes only its own stack and volume.

## Cloud deployment status and rubric

Cloud Run was not deployed and no cloud resource was created. The user selected the documented Cloud Run target and specified a $0.00 current spend cap and one Google identity. A second distinct approver identity and an approved nonzero staging budget are needed for the documented separation-of-duties deployment. No Google Cloud credentials or `gcloud` installation were available in this environment. The existing VECTOR project was left untouched. The exact setup request and next steps are in [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md).

The scorecard records local evidence without assigning points. It does not claim 100/100: cloud authentication, deployed isolation, Cloud SQL recovery, hosted CI/independent reproduction, adversarial effectiveness, real cloud load/cost, and independent usability review remain unverified. The scenario inventory is not an attack efficacy benchmark, and no model provider or baseline was configured.

## Reproduction

Use `make test-isolated` to run an isolated local verification without resetting the active demo database. CI runs signed-auth tests, builds and audits the explorer, audits Python packages, scans for secrets, then runs the authorization, rate-limit, rollback, expiry, and backup/restore regressions. A hosted CI run and clean-checkout reproduction have not yet been observed.
