# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Container installation and recovery guide with verified-digest usage and
  persistent Aegis storage. Packaged Aegis checks now require successful audit
  writes and linked records across container replacement; CI rejects the prior
  image layout without a writable data directory.
- A `/data` directory owned by Aegis's existing non-root user, allowing a fresh
  Docker named volume to retain audit and state files without root execution.
- Wheel-based first-run guide and installed-command checks on Python 3.11/3.12:
  a passing synthetic trace, a specifically identified forbidden-action failure,
  and malformed input that creates no output. Checks run outside the source tree.
- Version- and hash-locked Python build/runtime dependencies for the Sentinel
  container, retaining the prior release's runtime versions. Required Python 3.12
  CI checks a fresh installation, modified-wheel and missing-pin rejection, and
  installed assessment conformance. Development tools and optional extras remain
  outside these locks; full image byte reproducibility is not claimed.
- Weekly and manual rescanning of verified, immutable published `edge` image
  digests, with a fresh vulnerability database check and retained evidence.
- Offline `sentinel-assess` demonstration with 20 labeled synthetic traces,
  deterministic JSON/Markdown evidence, input and implementation fingerprints,
  and a bounded reliability-assessment proposal.
- Packaged runtime smoke checks before publication and after pulling a verified
  image digest: assessment conformance and Aegis startup/credential rejection.
- Maintenance, compatibility, recovery, and user-value measurement guidance.
- `release.yml` workflow that builds and publishes the `sentinel-eval` and
  `aegis-authorizer` container images to GitHub Container Registry on pushes
  to `main` (`edge` tag) and on `vX.Y.Z` tags (`latest`, `X.Y`, `X.Y.Z`), with
  no external secrets required. See `RELEASING.md` for the release process.
- Supply-chain evidence for published images: Sigstore-signed SLSA v1 build
  provenance and SPDX 2.3 SBOM attestations bound to each image digest,
  verified in the release job with `release.yml` pinned as the only trusted
  signer, plus `sha-<commit>` tags and a per-run summary of digest, commit,
  and ref.
- `release-guard` job that fails closed when a release runs from any ref other
  than `main` or a version tag, when a version tag points at a commit outside
  `main`, or when the tag does not match the declared package version.
- Pre-publish vulnerability gate: images are built locally, inventoried, and
  blocked on fixable high or critical findings before anything is pushed.
  Exceptions require a justified, code-owned entry in `.grype.yaml`.
- Every GitHub Action pinned to a commit SHA, and every base and service image
  pinned by digest, with Dependabot tracking Docker and Compose updates.
- `scripts/verify-image.sh`: one-command consumer verification that resolves a
  tag to its digest, verifies provenance and SBOM against the pinned signer and
  source ref, and refuses to guess the ref for floating tags.
- `tests/test_release_workflow.py` executes the release guards and asserts the
  pipeline's supply-chain invariants; `tests/test_verify_image_script.py`
  covers the verification script offline.
- Deployment capsule manifests for packaging public proof and private delivery
  assets with SHA-256 file evidence, visibility, license expression, required
  terms, blockers, next actions, and manifest digests.
- `sentinel-capsule` CLI for building JSON and Markdown capsule reports from a
  declared capsule catalog.
- Deployment capsule examples for Sentinel public proof and private delivery
  boundary cases.
- Dedicated deployment-capsule workflow that uploads generated capsule evidence.
- Capsule tests for ready public proof, sensitive-data blockers, non-public
  distribution blockers, missing required assets, duplicate capsule IDs, unsafe
  paths, and CLI output behavior.
- Value-route and deployment-capsule gates inside the default stability
  automation catalog.
- Trust-readiness scorer for evaluating whether a proposal is clear, evidenced,
  principled, emotionally intelligent, and safe enough to say yes to.
- Trust and communication standard defining evidence-before-confidence,
  clarity-before-performance, safety-before-speed, value-before-volume,
  dignity-before-persuasion, and accountability-before-delegation principles.
- Tests for safest-yes decisions, conditional acceptance terms, hard security
  blockers, weak-alignment states, duplicate dimensions, and invalid scores.
- Benefit-gated `sentinel-automation` runner for executing only allowlisted,
  high-value stability tasks from a JSON catalog.
- Default stability catalog covering linting, strict typing, tests, dependency
  audit, deterministic agent release gating, and coding-agent scorecard output.
- Scheduled and manually dispatchable `Stability Automation` GitHub Actions
  workflow that uploads JSON, Markdown, and evaluation evidence.
- Automation refinement documentation describing quality, security, evaluation,
  observability, portfolio, and governance layers.
- Tests for catalog loading, command allowlisting, shell-token rejection,
  benefit-threshold skips, duplicate task rejection, manual-task boundaries,
  report payloads, and Markdown output.
- `make automation` target for running the full benefit-gated stability suite.
- Deterministic coding-agent review scorer for converting rubric dimension
  scores into reproducible accept, accept-with-edits, needs-human-design, and
  reject decisions.
- Tests for strong accepts, security hard rejects, missing or duplicate
  dimensions, safety-aware comparisons, and margin-based ties.
- Coding-agent review cases for safe refactors, unsafe shell interpolation, and
  missing-test API outputs.
- Coding-agent review rubric for assessing AI-generated code across requirement
  fit, correctness, security, maintainability, verification, and communication.
- Secure agentic delivery playbook for separating model suggestion from
  executable action across backend, frontend, policy, evaluation, audit, and
  human-review boundaries.
- AI engineering value scorecard for translating governed-agent and
  model-evaluation work into business-facing evidence for applied AI, software
  engineering, developer-tooling, and internal-efficiency roles.

### Changed

- Package version advanced to `0.6.0`.
- Project positioning now includes deployment capsules in addition to governed
  execution, deterministic evaluation, code-review scoring, trace normalization,
  trust communication, benefit-gated automation, and value routing.

### Fixed

- Trace file imports reject raw inputs over 16 MiB before JSON parsing or
  writing evidence. Existing reports remain intact on rejection; larger exports
  must be split into complete-trace batches. This bounds file reads, not the
  parser's total memory or execution time.
- Incomplete or errored runs cannot pass evaluation through a high weighted
  score. This tightens release acceptance; safety and completion remain distinct.
- `test_release_ruleset.py` rejected any workflow with an `include` matrix,
  which failed CI once `release.yml` was added. It now expands include-only
  matrices into the job names GitHub reports.

## [0.3.0] - 2026-09-04

### Added

- Offline `sentinel-import-otel` command for normalizing OTLP JSON exports into
  strict, provider-neutral `AgentRun` JSONL.
- Identifier, topology, duplicate-span, ambiguous-root, and cycle validation for
  untrusted trace input.
- Tool, retry, approval, evidence, latency, cost, and completion mapping across
  a documented minimal semantic-convention profile.
- Fail-closed partial-trace behavior that cannot silently represent missing
  output or root timing as a complete run.
- Configurable sensitive-attribute redaction, URL credential/query scrubbing,
  and bounded preservation of unknown provider metadata.
- Reproducibility manifest containing source/configuration SHA-256 fingerprints,
  trace topology, retry attempts, completeness, warnings, and redaction counts.
- Versioned OTLP fixture, strict output, manifest schema, dedicated tests, and a
  CI workflow that evaluates the imported run through Sentinel's release gate.

### Changed

- Package version advanced to `0.3.0`.
- Sentinel now connects production observability artifacts to deterministic
  evaluation without making the core `AgentRun` contract provider-specific.

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
