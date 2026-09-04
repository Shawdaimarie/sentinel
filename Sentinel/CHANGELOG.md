# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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
  holding a key now refuses any unkeyed record. Found while writing
  [sentinel-spec](https://github.com/Shawdaimarie/sentinel-spec); covered by
  `test_keyed_verifier_rejects_downgrade_to_unkeyed` and spec vector 10.

### Changed

- A log is now entirely keyed or entirely unkeyed. Introducing a key requires
  starting a new log file.

### Added

- The audit-chain format is specified language-neutrally in sentinel-spec,
  with conformance vectors and verifiers in Python, TypeScript, and Go.
  `README.md`, `ARCHITECTURE.md`, and `SECURITY.md` link to it.

## [0.1.0] - 2026-08-29

Initial implementation.
