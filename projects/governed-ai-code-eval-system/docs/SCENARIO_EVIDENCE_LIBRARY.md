# Scenario Evidence Library

## Purpose

The scenario evidence library expands the project beyond a single risky-code sample. It gives reviewers a sanitized, repeatable set of AI/ML engineering workflows that can be evaluated with the same governed rubric.

## Covered Workflows

| Workflow | Scenario | Primary Review Signals |
| --- | --- | --- |
| Model training | Training Leakage Review | Evaluation-data leakage, schema validation, deterministic splits, and reproducibility evidence. |
| Inference service | Artifact Control Review | Model artifact pinning, request timeouts, model lifecycle, latency, and rollback readiness. |
| MLOps pipeline | Supply-Chain Review | Runtime dependency installation, shell execution, mutable image tags, and release-governance risk. |
| Agent tooling | Tool Boundary Review | Prompt-injection language, dynamic execution, untrusted model-output parsing, and sensitive logs. |

## Evaluator Coverage

The Python proof pack exposes:

- `scenario_evidence_library()` for listing sanitized scenario definitions.
- `review_scenario_library()` for running each scenario through the evaluator.

The scenario tests confirm that every workflow produces expected governed findings and that the scenario text remains client-neutral.

## New Review Controls

This release adds AI/ML-specific review checks:

- `DATA-002`: evaluation split fitted during preprocessing.
- `REL-003`: mutable production artifact reference.
- `REL-004`: model load requires lifecycle review.
- `REL-005`: training split without deterministic seed.
- `SEC-012`: runtime dependency installation.

## Operating Standard

Use the scenario library to show breadth across realistic AI engineering work:

1. Select a scenario that matches the role or project surface.
2. Run the governed evaluator.
3. Preserve JSONL output and reviewer notes.
4. Compare candidates when more than one model output exists.
5. Save a calibration audit snapshot when the decision should be retained.

## Claim Boundary

Accurate positioning:

This project includes a sanitized AI/ML scenario evidence library covering model training, inference, MLOps, and agent tooling.

Do not present the scenario library as production validation, external certification, or benchmark authority. It is reviewer-ready proof of disciplined evaluation practice.
