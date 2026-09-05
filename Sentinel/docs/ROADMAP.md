# Sentinel technical roadmap

This roadmap describes planned engineering work. Items are not implemented or
production-ready until they are merged with tests, evaluation evidence,
security review, and green CI.

## Current foundation — 0.2.x

Delivered:

- deny-by-default agent policy and per-run action budgets;
- pre-execution append-only audit decisions;
- SHA-256 and HMAC-SHA256 chains with downgrade detection;
- governed network retrieval with per-hop redirect evaluation;
- deterministic evaluation of correctness, safety, grounding, tool use,
  latency, cost, and action budgets;
- hard safety gates and paired baseline regression checks;
- versioned benchmark cases and machine-readable reports;
- training-data quality gates for schema, source notes, privacy posture, split
  hygiene, and AI-agent safety coverage;
- portable audit profile with independent Python, TypeScript, and Go
  verification;
- Python 3.11/3.12 CI, strict typing, dependency audit, CodeQL, and a non-root
  container build; and
- an engineering crosswalk to NIST AI RMF functions.

## Next expansion — controlled AI training readiness

Objective: connect Sentinel's evaluation foundation to post-training work
without allowing weak data or unsupported improvement claims into the process.

- Expand the Training Data Quality Gate with dataset cards, source authority
  labels, annotation provenance, and risk-class balancing.
- Add model-output pair support for supervised fine-tuning and preference
  optimization.
- Add baseline model evaluation reports before any training experiment.
- Add training run manifests covering model, method, dataset split, seed,
  hyperparameters, compute assumptions, and limitations.
- Compare before/after behavior with the existing deterministic evaluator.
- Block training promotion on safety, privacy, grounding, or human-approval
  regressions.

Exit criteria:

- one public synthetic dataset passes the data gate;
- invalid or privacy-sensitive examples fail closed;
- one baseline report exists before training;
- one post-training experiment improves a declared target metric; and
- no safety regression is allowed to pass through aggregate score inflation.

## 0.3 — production trace ingestion

Objective: evaluate real system behavior without hand-authoring `AgentRun`
records.

- Import OpenTelemetry spans into the portable run contract.
- Add adapters for captured OpenAI, Anthropic, Gemini, and local-model tool
  traces without requiring provider credentials in CI.
- Preserve parent/child action relationships, retries, human approvals, token
  use, latency, and recorded cost.
- Validate trace completeness and mark partial traces explicitly.
- Add repeated-trial statistics, variance alerts, and confidence intervals.
- Add regression slices by model, tool, workflow, environment, and risk class.

Exit criteria:

- one end-to-end example imports an OpenTelemetry trace;
- missing or malformed spans fail visibly;
- provider adapters produce the same normalized contract;
- deterministic fixtures remain reproducible; and
- security review covers prompt, metadata, and credential redaction.

## 0.4 — longitudinal evaluation service

Objective: make evaluation history queryable while preserving provenance.

- PostgreSQL schema for suites, cases, runs, metrics, releases, and input
  fingerprints.
- Idempotent ingestion keyed by content digest.
- Read-only API for release history, regressions, slices, latency, and cost.
- Migration strategy and rollback tests.
- Retention and deletion policy for captured traces.
- Role-separated database credentials and least-privilege queries.
- Containerized local stack and health checks.

Exit criteria:

- migrations run from an empty database and upgrade a previous schema;
- duplicate reports do not create duplicate observations;
- authorization tests prevent writes through read-only paths;
- backup and restore are documented and exercised; and
- the service can reproduce a release decision from stored artifacts.

## 0.5 — external audit anchoring and policy provenance

Objective: address the hash chain's documented completeness boundary.

- Pluggable append-only sinks for object-lock or transparency-log storage.
- External anchoring of final digests at declared intervals.
- Key-provider interface for secrets managers or HSM-backed material.
- Signed policy bundles and deployment-time fingerprint verification.
- Explicit chain rotation and key-rotation records.
- Recovery behavior for unavailable anchors.
- Cross-language verification of anchored checkpoints.

Exit criteria:

- tail truncation is detectable from an independent checkpoint;
- the writer cannot read long-lived key material from local disk;
- policy substitution fails before agent execution;
- rotation does not silently join incompatible trust domains; and
- residual risk remains documented.

## 0.6 — calibrated human evaluation

Objective: add defensible review for semantic dimensions that deterministic
assertions cannot measure well.

- Reviewer rubric versioning and qualification cases.
- Blind duplicate items for intra-rater consistency.
- Inter-rater agreement and disagreement analysis.
- Adjudication queues with retained rationale.
- Separation of model identity from reviewer display where appropriate.
- Dataset cards describing construction, exclusions, and limitations.
- Export into the same release report without allowing human scores to hide
  hard safety failures.

Exit criteria:

- reviewer calibration is measurable;
- disagreement remains visible rather than averaged away;
- sensitive content handling is documented; and
- deterministic and human evaluation results retain separate provenance.

## Candidate contributions

High-value contributions are deliberately scoped around evidence:

1. Add a failing evaluation case for a real, documented agent failure mode.
2. Improve a trust-boundary test without expanding permissions.
3. Implement an importer behind a strict normalized contract.
4. Add an independent verifier or cross-runtime conformance case.
5. Improve report diagnostics while preserving deterministic output.
6. Document a deployment limitation with a testable mitigation.

Every roadmap item must preserve the project's central rule: a persuasive
aggregate score never overrides an explicit safety failure.
