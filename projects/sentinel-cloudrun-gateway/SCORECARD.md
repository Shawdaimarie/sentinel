# SENTINEL 100-point evidence scorecard

This scorecard applies the canonical blueprint v1.1 rubric. Each item is worth five points. The blueprint requires independent reproduction of every criterion before claiming 100/100. Local author-run evidence is recorded for transparency but is not scored yet. A pending item receives 0 until its acceptance condition and independent reproduction are both documented.

| Category / criterion | Pts | Acceptance evidence | Current evidence | State |
|---|---:|---|---|---|
| Functionality: tenant-scoped document search | 5 | Search only through gateway; tenant scope and untrusted provenance visible | Smoke and guided browser walkthrough | Reproduction pending |
| Functionality: tenant-scoped record read | 5 | Read through gateway; foreign record returns no data | Smoke and guided browser walkthrough | Reproduction pending |
| Functionality: reversible update | 5 | Update requires approval; restoration is a new approval | Smoke and guided browser walkthrough; c101 restored | Reproduction pending |
| Functionality: approval/denial trace | 5 | Admin approval and denial have auditable trace; denied action cannot execute | Approved in walkthrough; explicit denial test added | Rerun and reproduction pending |
| Reliability: recovery | 5 | Documented database backup restore and service recovery succeed | Local PostgreSQL logical restore to separate disposable DB; Cloud SQL recovery not exercised | Cloud evidence pending |
| Reliability: idempotency | 5 | Same-key retry returns the committed result under serial and concurrent retries | Clean isolated smoke: serial and concurrent same-key retries matched | Independent reproduction pending |
| Reliability: restore | 5 | Restoration is a separately approved action and restores original value | Clean isolated smoke and local browser walkthrough | Independent reproduction pending |
| Security: authorization | 5 | Production-authenticated identity, role separation, denied unauthenticated request, least privilege | Local fixture only; IAP not configured | Pending |
| Security: isolation | 5 | Cross-tenant access denied in deployed environment; DB route unavailable to callers | Local tenant test only | Pending |
| Security: adversarial checks | 5 | Attack families executed against target system with raw outcomes and no critical bypass | Concurrency, replay, tenant, denial, expiry, and rollback regressions passed; scenario inventory is not effectiveness evidence | Cloud and broad efficacy evidence pending |
| Security: dependency and secret controls | 5 | Clean dependency and secret scans for deployment revision | Local Python/npm audits and full-repo Gitleaks scan passed | Independent cloud revision pending |
| Performance: latency | 5 | Predeclared route mix, 10 concurrency, 1,000 requests per route; local target p95 ≤100 ms | 2026-11-04 local 5-route run: 1,000 each, concurrency 10; all p95 7.541–14.642 ms | Independent reproduction pending |
| Performance: throughput and cost | 5 | Throughput/errors recorded; provider cost measured or modeled with stated assumptions | Local throughput 1,501.05 req/s, no HTTP errors; cloud cost not measured | Cloud cost evidence pending |
| Usability: task completion | 5 | Independent reviewer completes all four workflows and reports friction | Local walkthrough and coordinating-project browser report | Full rubric pending |
| Usability: accessibility | 5 | Keyboard and WCAG-oriented review with findings resolved or disclosed | Local keyboard/contrast/control-size review documented; screen reader and 200% zoom checks remain | Independent review pending |
| Documentation: clean-environment reproduction | 5 | Independent clean checkout reproduces build and end-to-end suite | Isolated clean Compose reproduction passed locally; hosted/independent run pending | Independent reproduction pending |
| Documentation: API/operator docs | 5 | API and operator procedures allow another operator to run and diagnose | Local docs present | Independent check pending |
| Documentation: evidence provenance | 5 | Inputs, commit, environment, command, timestamps, and raw outputs traceable | Local evidence report and Git commits | Independent check pending |
| Scalability: declared-load test | 5 | Cloud Run bounded topology passes declared concurrent load with stable errors/latency | Not run | Pending |
| Scalability: capacity/cost model | 5 | Reproducible model matches configured quota, scaling, database, storage, and observed cost | Not modeled for configured project | Pending |
| **Total** | **100** | Every row independently reproduced; no release-blocking defects | **No score claimed** | **Not achieved** |

The scenario inventory is not an effectiveness benchmark. No row earns points merely because a test file exists. Cloud Run has not been deployed. Local author-run evidence is not an independent rubric score; therefore no points are awarded and 100/100 is not claimed. Update this table only after the corresponding command, environment, commit, result, and reviewer/reproduction status are recorded in `TEST_REPORT.md`.
