# SENTINEL project status

Updated: 2026-11-02 · Canonical blueprint: v1.1 (coordination project; unchanged here)

## Gates

- G0: **established for a bounded local synthetic prototype** after the competitive, technical, and evidence reviews were committed in `f03e453`, before application implementation.
- G1: **local vertical slice and clean isolated Compose reproduction author-verified; browser walkthrough reported by the coordinating project and repeated here**. Hosted CI and independent clean-checkout reproduction remain pending.
- G2: pending — preregistered, executable held-out effectiveness benchmark, security review, and independent clean reproduction. The 220-row scenario inventory is not itself a benchmark result.
- G3: pending — bounded staging, cost, backup/restore, and rollback evidence. Production identity and infrastructure remain unconfigured.
- G4/G5: not authorized or entered.

## Current deliverable

One-command local Compose startup for a synthetic document-search and customer-record workflow. FastAPI is the sole tool path to PostgreSQL; the explorer shows policy decisions, approvals, and audit traces. A deterministic fixture agent can request a reversible record-note change, which requires separate administrator approval and an owner-held, single-use capability to execute. The UI can restore the prior value through a new approval.

The demo uses local-only bearer fixtures, a local HMAC secret, and synthetic records. Audit events are hash-linked and verifiable, but a privileged database administrator could rewrite the full chain. See `THREAT_MODEL.md` and `DEPLOYMENT_STATUS.md` for boundaries.

## Out of scope and blockers

Production authentication, managed cloud database/object storage, public inference, paid model use, cloud deployment, publication, customer pilots, and market claims. No model provider credentials are configured. Commercial assumptions, including the $1M ARR arithmetic, are unvalidated. No external messages or publishing are authorized.

## Scorecard

| Category | Points possible | State | Evidence required |
|---|---:|---|---|
| Functionality | 20 | Evidence collected; no points awarded | Independent clean reproduction against rubric. |
| Reliability | 15 | Evidence collected locally; no points awarded | Independent reproduction and longer-run fault testing. |
| Security | 20 | Local invariants checked; no points awarded | Threat review, independent security assessment, production identity. |
| Performance | 10 | Not measured | Declared load/latency/cost benchmark. |
| Usability | 10 | Browser workflow demonstrated; no points awarded | Reviewer rubric and accessibility review. |
| Documentation/reproducibility | 15 | Local instructions present; no points awarded | Clean-checkout reproduction, CI confirmation, provenance. |
| Scalability | 10 | Not measured | Declared-load and capacity/cost model. |

No score is claimed until the blueprint's evidence rubric is met. See `SCORECARD.md` for each point condition, `TEST_REPORT.md` for local commands/results, and `PUBLISHING_DRAFTS.md` for unpublished platform copy.
