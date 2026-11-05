# SENTINEL prototype notes

## 0.1.0 · 2026-11-02

- Added a loopback React policy/trace explorer and FastAPI gateway backed by a local PostgreSQL container.
- Added tenant-scoped document search and customer reads, exact-action approval, a single-use short-lived capability, idempotent transactional update and approved restoration path.
- Added per-tenant hash-linked audit verification, bounded request input, rate limiting and synthetic malicious retrieval fixture.
- Added 220 documented scenario rows, with attack-family labels and two development holdout families. They are not comparative model benchmark results.
- Added live regression scripts and a GitHub Actions CI workflow. Cloud deployment, OIDC production authentication, object storage, recovery, and model-provider trials remain blocked/unverified.
