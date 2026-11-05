# SENTINEL technical review

Date: 2026-11-02 · Blueprint: shared v1.1 · Status: reviewed for bounded local synthetic prototype only

## Proposed scope and architecture

React/TypeScript trace and policy explorer; FastAPI gateway; Python client and adapter contract; synthetic document search, customer-record read, reversible customer-record update; PostgreSQL schema for production-shaped records and approvals; append-only hash-linked audit records; evaluation JSONL artifacts locally at first. Local filesystem artifacts are not object-storage verification. PostgreSQL is required for concurrency claims; SQLite/in-memory mode cannot establish production race safety. Container and Cloud Run/IaC/CI assets are design scope, but deployment and cloud costs remain unverified.

Flow: authenticate actor from trusted gateway configuration (local signed development token only); derive tenant from verified identity, never tool arguments; validate a strict versioned argument schema; normalize canonical arguments; check tool and resource policy; create approval for sensitive update; bind one-time capability to actor, tenant, action, resource, canonical argument digest, expiration, nonce, and approval id; execute and consume in one PostgreSQL transaction with unique idempotency key and row lock; emit audit event in same transaction. Document search returns clearly untrusted content. No retrieved content may alter principal, tenant, policy, or approval state.

## Policy-engine assessment

OPA/Rego and Cedar are established candidates. OPA's agent tool-calling docs explicitly describe harness/PEP, OPA/PDP, tool/parameter policy, dynamic bundles, and decision logs. Cedar evaluates principal/action/resource/context. Use a fixed minimal rule boundary for the prototype only. Future administration should reuse OPA through an adapter unless measured fit shows a concrete limitation; do not clone either project without a specific justified upstream change. The gateway still owns identity, approval lifecycle, transactionality, capability consumption and tool isolation.

## Threat model and trust boundaries

Assets: synthetic customer fields, tool execution authority, approval decisions, tenant boundaries, capability tokens, audit sequence/integrity, evaluation artifacts and secrets.

Adversaries: malicious or compromised document author; prompt injection influencing an agent; authenticated tenant user attempting cross-tenant access; replaying/substituting an approval/capability; concurrent requests racing approval or update; malformed or oversized tool arguments; compromised downstream agent code attempting direct access.

Trust boundaries: untrusted user/request → authentication boundary → gateway/PDP → approval store and transactional executor → synthetic records; retrieved document → model (untrusted) → tool request; gateway → database; service → secrets/model provider; benchmark runner → result artifacts.

Controls in prototype: fixture-backed identity; tenant derived from the token; deny-by-default tool allowlist; strict schemas, 32 KiB declared body limit, max argument count/name length, bounded identifier syntax and field lengths; tenant ownership check; 60 calls per actor/minute; update only the note field; record version bound into the capability digest and compared at execution; expiring single-use capability with unique nonce; transaction/row lock/idempotency; no agent database credential or alternate tool route; tenant-scoped audit hash chain and decision events. Invalid credentials cannot be attributed to a verified actor and are not written to this application audit chain. Retrieved content is labeled untrusted.

Assumptions and limits: gateway and host kernel, database administrator, signing secret, trusted identity issuer, and operator are not compromised; local developer token is not production authentication. Hash chains detect edits only relative to a retained trusted head/checkpoint; an attacker able to rewrite the entire database and checkpoint can recompute hashes. Audit log is append-only by application convention/DB role, not tamper-proof. No claim of resistance to host/root compromise, malicious authorized operators, model exfiltration through allowed outputs, denial of service, or unknown software defects. Network route elimination is asserted only for the documented deployment topology and must be evidenced by infrastructure review/tenant tests before release.

## Isolation, testing, and operations

Production identity: workload-specific service accounts with minimum database/object-store access; secrets through managed secret integration; no long-lived model or database credentials in agent clients. Cloud Run service identity uses ADC for Google APIs; private service communication and Cloud SQL auth/network controls must be designed and verified against deployed configuration. Production database separate per environment, tenant keys on all rows, composite tenant/resource constraints and transaction checks. Evaluation objects in private object storage with retention/access policy; local fixture artifacts are explicitly non-production.

Meaningful tests: schema rejection, identity spoofing, tenant enumeration/cross-tenant denial, allowlist denial, malicious retrieved instruction cannot trigger out-of-scope update, approval argument/resource substitution, expiration, replay, concurrent double-use, stale record version, idempotent retry, audit-chain tamper detection, rollback after failure, health/readiness. CI clean checkout and pinned dependencies. Recovery: managed DB backups, documented restore exercise, health checks, migration rollback approach, previous image rollback. Capacity and $50/month project design require actual provider/account configuration and workload assumptions; not a quote or spend authorization.

Failure modes: DB unavailable means fail closed for protected tools; approval service unavailable means update denied; audit transaction failure means side effect rolls back; model unavailable/429/timeouts recorded as failed/aborted, not security pass; object storage unavailable blocks benchmark publication but need not block local authorization; policy config invalid rejects startup. Rate limits, request/body/tool timeouts, concurrency ceilings and bounded evaluation jobs required. No public inference until explicit budget/quota and abuse limits are checked.

## Evaluation and reproducibility

No neural network is trained. Model adapters are inference-only. Deterministic fixtures are the initial reproducible benchmark. For hosted models record provider, exact model/version if exposed, API parameters, prompt/tool definitions, date, region where available, trial seeds/IDs, latency/cost fields, failures and availability. Hosted outputs may change without notice; exact replay cannot be promised. Avoid data leakage: generate synthetic scenarios; split attack families/templates before prompt tuning; freeze holdout; no held-out tuning; publish scenario IDs and hashes with sensitive attack text stored in owned artifacts. Repeat stochastic trials and calculate confidence intervals; compare paired tasks and separate model behavior from gateway latency. Report denominators and exclusions.

## Acceptance rubric and gates

Blueprint scoring target: Functionality 20 (four workflows ×5); Reliability 15; Security 20; Performance 10; Usability 10; Documentation/reproducibility 15; Scalability 10. This review defines conditions; all remain pending until evidence is recorded with command/environment/raw result/revision/reviewer.

| Criterion | Project-specific evidence required |
|---|---|
| Functionality | Search, read, reversible update, approve/deny trace each demonstrated via gateway client/UI. |
| Reliability | Idempotent retry, concurrency single-use, rollback, backup/restore exercise recorded. |
| Security | Auth, tenant isolation, policy, schema, scope, capability/approval/replay invariants; malicious retrieval test; dependency and secret scans. |
| Performance | Local Docker environment; target 10 concurrent clients and 1,000 requests per route; report p50/p95 gateway-only latency excluding inference, throughput and errors. Prototype acceptance target p95 ≤100 ms for local synthetic routes (not a production SLO), plus cost model. |
| Usability | Reviewer completes required workflow and explorer task; keyboard/accessibility review. |
| Documentation/reproducibility | Clean checkout reproduces deterministic suite and benchmark; source/evidence provenance; API/operator docs. |
| Scalability | Declared-load test and capacity/cost model for bounded Cloud Run topology. |

## G0 decision

**G0 established for bounded local synthetic implementation only.** The competitive review, this technical review, evidence register, and acceptance rubric exist before application source. The approved scope is the local synthetic vertical slice and deterministic benchmark preparation; release and deployment scope is not approved. Decision rationale: it tests the core authorization hypothesis without real customer data, live external tools, paid inference, or public exposure. Open gaps: current verified dependencies/runtime account, production PostgreSQL and object-storage configuration, Cloud Run/IaC pricing, hardened deployment identity/network route proof, provider credentials, the held-out 200+ scenario benchmark, clean external reproduction, commercial validation, and deployment/recovery evidence. G0 does not imply G1 or security certification.
