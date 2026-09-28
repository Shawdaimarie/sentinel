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

The optional `history` extra now implements PostgreSQL storage and a read-only
CLI for this scope. See [evaluation history](EVALUATION_HISTORY.md) for the
storage contract, migration and role setup, query examples, and recovery tests.
This implementation does not expose an HTTP service or claim production readiness.

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

## Foundation program — eight steps for shared digital environments

Shared digital environments, from collaborative tools to immersive worlds,
put three things in the same place: AI agents acting for people, generated
media, and money. Each step below gives one of them a guarantee that is
enforced by code and checked by tests. None of them is a statement of
intent alone.

Each step names the value it protects, what ships, how completion is proven,
and the public practice it follows. A named practice is a design reference,
not a claim of certification, endorsement, or equivalence.

### 1. Close the release trust chain

*Protects: integrity, meaning what runs is what was reviewed.*

- Move provenance signing into an isolated reusable workflow, so build steps
  cannot influence what is signed.
- Publish an OpenSSF Scorecard result for the repository and track it.
- Re-scan published image digests on a schedule for vulnerabilities disclosed
  after release, and open an issue on any new high or critical finding.

Exit criteria: provenance verifies as SLSA Build Level 3; a newly disclosed
vulnerability in a shipped image opens an issue within one scheduled run; the
Scorecard result is published with every release.

Practice: SLSA (OpenSSF), npm registry provenance, OpenSSF Scorecard.

### 2. Make audit and policy independently checkable

*Protects: accountability, meaning no one can quietly rewrite what happened.*

Complete the 0.5 scope above. Anchor audit-chain checkpoints and policy-bundle
digests in a public transparency log, and verify signed policy before any
agent executes.

Exit criteria: truncating an audit log is detected from an external
checkpoint; a substituted policy is refused before execution; the Python,
TypeScript, and Go verifiers agree on anchored checkpoints.

Practice: Certificate Transparency (RFC 9162), Sigstore Rekor, and published
transparency logs for verifiable server software, such as Apple's Private
Cloud Compute.

### 3. Delegated authority that people can see and revoke

*Protects: consent and human authority, meaning an agent can do only what a
person granted, only for as long as they granted it.*

- Extend Aegis capabilities with explicit on-behalf-of delegation: which
  person delegated, to which agent, for which scope, until when.
- Make revocation take effect before the next authorization decision.
- Give every delegation a record that the person can read in plain language.

Exit criteria: an agent cannot exceed or outlive its delegation; revocation
is enforced on the next call; each allowed action names the delegating
person in the audit chain; delegation chains cannot widen scope.

Practice: OAuth 2.0 Token Exchange (RFC 8693) actor claims, W3C Verifiable
Credentials 2.0.

### 4. Privacy by construction in evaluation data

*Protects: privacy and dignity, meaning evaluation never becomes surveillance.*

- Redact personal data from imported traces before storage, with test
  vectors for each redaction rule.
- Enforce retention and deletion in evaluation history, not only document it.
- Publish aggregate metrics that could identify individuals only with
  differential-privacy noise and a declared privacy budget.

Exit criteria: seeded personal data never reaches storage; a deletion request
removes every derived record and is itself audited; aggregate reports state
their privacy parameters.

Practice: data minimization (GDPR Article 5), differential privacy in
large-scale telemetry, such as Apple's published approach.

### 5. Financial safeguards for content and actions

*Protects: people's money and trust, meaning an agent can neither mislead
about finances nor move funds without a human decision.*

- Ship the financial-content gate, which already exists on
  `feat/financial-content-gate`. It blocks personalized trade directives,
  guaranteed-return claims, fabricated data, and missing disclosures, and it
  always routes release to a human.
- Add financial-action policy to Aegis: per-action and per-period value
  limits, maker-checker approval above a threshold, idempotency keys against
  duplicate execution, and a cooling-off window for irreversible actions.
- Produce an evidence pack per decision, suitable for audit and operational
  resilience review.

Exit criteria: no autonomous path executes a financial action; a duplicate
request never executes twice; above-threshold actions require two distinct
approvers; every decision has a complete, verifiable evidence record.

Practice: maker-checker dual control in banking, idempotent payment APIs, and
EU DORA operational-resilience expectations.

### 6. Provenance for generated media

*Protects: truth and consent, meaning people can tell what was generated,
by what, and with whose authority.*

- Record content-credential manifests for media that governed agents
  produce.
- Evaluate that manifests are present, valid, and consistent with the
  agent's audit record.
- Treat missing or stripped provenance on publishable media as a hard gate.

Exit criteria: every published generated asset carries a valid manifest
linked to an audit entry; a tampered or missing manifest fails the gate.

Practice: C2PA Content Credentials, an open standard backed by Adobe,
Microsoft, Google, and others.

### 7. Fair, accessible, and multilingual evaluation

*Protects: equal treatment, meaning quality is measured for everyone, not
for an average user.*

- Add evaluation slices by language, locale, and accessibility need, and
  report each one separately, never averaged away.
- Check agent-produced interfaces against WCAG 2.2 success criteria that can
  be automated.
- Seed multilingual evaluation cases, starting with right-to-left and
  non-Latin scripts.

Exit criteria: a regression in any single slice fails the release even when
the overall score improves; accessibility failures are reported per
criterion.

Practice: IBM AI Fairness 360, Microsoft's Responsible AI Standard, W3C WCAG
2.2.

### 8. Governance evidence people can act on

*Protects: honesty and redress, meaning users, auditors, and affected people
can see what a system is, what it is not, and how to report harm.*

- Generate a system card for each release from recorded evidence: intended
  use, known limitations, evaluation results, and residual risks.
- Map controls to ISO/IEC 42001 and to EU AI Act technical-documentation
  topics, alongside the existing NIST AI RMF crosswalk.
- Publish an incident and coordinated-disclosure process with response
  targets.

Exit criteria: the system card is generated, never hand-edited, and fails CI
if evidence is missing; every mapped control links to a test or an explicit
gap; a disclosure report receives a tracked response.

Practice: IBM AI FactSheets, model cards, ISO/IEC 42001, ISO/IEC 29147.

### Order and dependencies

Steps 1 and 2 come first, because every later guarantee relies on trustworthy
builds and a trustworthy record. Step 3 is required before step 5 can
authorize any financial action. Steps 4, 6, and 7 can proceed in parallel.
Step 8 assembles the evidence from all the others.

### What this program does not claim

Completing these steps does not make any system safe for every use,
certified, or compliant with a specific law. It produces evidence for a
qualified reviewer to assess. Legal, financial, and accessibility compliance
remain decisions for accountable people with the relevant expertise.

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
