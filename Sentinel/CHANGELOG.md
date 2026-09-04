# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Deterministic coding-agent review scorer for converting rubric dimension scores into reproducible accept, accept-with-edits, needs-human-design, and reject decisions.
- Tests for strong accepts, security hard rejects, missing or duplicate dimensions, safety-aware comparisons, and margin-based ties.
- Coding-agent review cases for safe refactors, unsafe shell interpolation, and missing-test API outputs.
- Coding-agent review rubric for assessing AI-generated code across requirement fit, correctness, security, maintainability, verification, and communication.
- Secure agentic delivery playbook for separating model suggestion from executable action across backend, frontend, policy, evaluation, audit, and human-review boundaries.
- AI engineering value scorecard for translating governed-agent and model-evaluation work into business-facing evidence for applied AI, software engineering, developer-tooling, and internal-efficiency roles.

## [0.2.1] - 2026-09-04

### Added

- Language-neutral `sentinel.audit.v1-portable` specification.
- Normative keyed and unkeyed conformance vectors with expected final digests.
- Independent standard-library Python and Go verifiers.
- Independent dependency-free TypeScript verifier after compilation.
- Cross-language CI proving identical verification outcomes and binding
  Sentinel's own audit implementation to the portable vectors.

### Changed

- Security and architecture documentation now link to tested, in-repository
  evidence rather than an external specification dependency.
- The public landing page now exposes polyglot verification and its trust
  boundary directly to reviewers.

## [0.2.0] - 2026-09-04

### Added

- Deterministic agent-evaluation harness for correctness, safety, grounding,
  tool-use discipline, latency, cost, and action budgets.
- Versioned JSONL contracts for evaluation cases and observable agent runs.
- Hard release failures for forbidden actions, prohibited output, missing
  cases, and safety regressions.
- Paired baseline/candidate comparison with pass-to-fail and score-regression
  detection.
- Tag-slice analysis for security, privacy, governance, reliability,
  grounding, human oversight, and regulated workflows.
- Machine-readable JSON and human-reviewable Markdown reports with SHA-256
  fingerprints of every input artifact.
- Example benchmark suite, baseline runs, and generated evidence reports.
- Non-root Docker image, Make targets, dependency update configuration, and a
  CI workflow that runs quality, tests, evaluation gates, dependency audit,
  and a container build.
- NIST AI RMF crosswalk, evaluation protocol, and engineering case study.

### Changed

- Package version advanced to `0.2.0`.
- Project positioning expanded from governed execution to governed execution
  plus release-grade evaluation.

## [0.1.1] - 2026-08-31

### Security

- `verify-audit` now rejects a keyed-to-unkeyed downgrade. Previously the
  `keyed` flag inside each record selected the verification algorithm, so an
  attacker able to rewrite the log could flip it to `false` on every record,
  recompute plain SHA-256 forward, and pass keyed verification. A verifier
  holding a key now refuses any unkeyed record. The behavior is covered by
  `test_keyed_verifier_rejects_downgrade_to_unkeyed` and the portable
  conformance vectors under `spec/vectors/`.

### Changed

- A log is now entirely keyed or entirely unkeyed. Introducing a key requires
  starting a new log file.

### Added

- The audit-chain format was documented language-neutrally and later promoted
  into the in-repository portable profile with independent Python, TypeScript,
  and Go verification.

## [0.1.0] - 2026-08-29

Initial implementation.
