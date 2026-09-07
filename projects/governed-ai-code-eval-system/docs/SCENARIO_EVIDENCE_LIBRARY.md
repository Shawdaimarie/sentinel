# Scenario Evidence Library

## Purpose

The scenario evidence library expands the project beyond a single risky-code sample. It gives reviewers a sanitized, repeatable set of AI, software, data, release, and runtime workflows that can be evaluated with the same governed rubric.

## Covered Workflows

| Workflow | Scenario | Primary Review Signals |
| --- | --- | --- |
| Model training | Training Leakage Review | Evaluation-data leakage, schema validation, deterministic splits, and reproducibility evidence. |
| Inference service | Artifact Control Review | Model artifact pinning, request timeouts, model lifecycle, latency, and rollback readiness. |
| MLOps pipeline | Supply-Chain Review | Runtime dependency installation, shell execution, mutable image tags, and release-governance risk. |
| Agent tooling | Tool Boundary Review | Prompt-injection language, dynamic execution, untrusted model-output parsing, and sensitive logs. |
| Frontend/API integration | TypeScript Agent API Review | JavaScript payload validation, fetch cancellation, dynamic function construction, and sensitive logs. |
| Data access | SQL Data Access Boundary Review | SQL parameterization, tenant boundaries, and injection-shaped inputs. |
| Release script | Release Shell Script Review | Remote script execution, runtime dependency installation, and mutable image tags. |
| Container runtime | Container Runtime Hardening Review | Base image pinning, non-root runtime, dependency pinning, and provenance. |

## Evaluator Coverage

The Python proof pack exposes:

- `scenario_evidence_library()` for listing sanitized scenario definitions.
- `review_scenario_library()` for running each scenario through the evaluator.
- `supported_review_surfaces()` for listing universal surfaces covered by the evaluator.

The scenario tests confirm that every workflow produces expected governed findings and that the scenario text remains client-neutral.

## New Review Controls

This release adds AI/ML-specific review checks:

- `DATA-002`: evaluation split fitted during preprocessing.
- `REL-003`: mutable production artifact reference.
- `REL-004`: model load requires lifecycle review.
- `REL-005`: training split without deterministic seed.
- `SEC-012`: runtime dependency installation.

This universal support pass adds broader checks:

- `DATA-003`: parsed JavaScript output without schema validation.
- `REL-006`: fetch call without cancellation signal.
- `REL-007`: unpinned container base image.
- `SEC-013`: JavaScript Function constructor execution.
- `SEC-014`: Node child process execution.
- `SEC-015`: remote script piped to interpreter.
- `SEC-016`: interpolated SQL execution.
- `SEC-017`: container runs as root.
- `SEC-018`: wildcard infrastructure permission.

## Operating Standard

Use the scenario library to show breadth across realistic AI engineering work:

1. Select a scenario that matches the role or project surface.
2. Run the governed evaluator.
3. Preserve JSONL output and reviewer notes.
4. Compare candidates when more than one model output exists.
5. Save a calibration audit snapshot when the decision should be retained.

## Claim Boundary

Accurate positioning:

This project includes a sanitized universal scenario evidence library covering model training, inference, MLOps, agent tooling, TypeScript/JavaScript APIs, SQL/data access, shell release scripts, and container runtime hardening.

Do not present the scenario library as production validation, external certification, or benchmark authority. It is reviewer-ready proof of disciplined evaluation practice.
