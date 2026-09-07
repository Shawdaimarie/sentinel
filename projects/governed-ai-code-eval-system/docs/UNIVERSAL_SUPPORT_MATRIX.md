# Universal Support Matrix

## Purpose

The universal support matrix defines the broader review surfaces covered by the evaluator. It keeps the project useful beyond one language or one task type while preserving a clear claim boundary.

## Supported Review Surfaces

| Surface | Coverage | Primary Risk Signals |
| --- | --- | --- |
| Python | Agent logic, ML workflows, API clients, scripts, and evaluator packages. | Unsafe execution, deserialization, secrets, shell calls, missing timeouts, mutable defaults. |
| TypeScript/JavaScript | Frontend, API, worker, and agent-tool snippets. | Function constructors, child processes, unvalidated JSON parsing, fetch calls without cancellation. |
| SQL/data access | Query helpers and reviewer-facing data-access paths. | Interpolated SQL, weak tenant boundaries, unvalidated model or user-controlled values. |
| Shell/release scripts | Build, deploy, setup, and automation snippets. | Remote scripts piped to interpreters, runtime dependency installs, mutable image tags. |
| Container images | Dockerfile and runtime hardening snippets. | Latest tags, root users, unpinned bases, runtime installs, weak provenance. |
| Infrastructure policy | Policy and deployment configuration fragments. | Wildcard permissions, unclear least privilege, broad resource authority. |
| AI/ML workflows | Training, inference, evaluation, and artifact lifecycle code. | Evaluation leakage, unseeded splits, mutable models, request-path model loading. |
| Agent tooling | Tool calls, prompt boundaries, model-output parsing, and audit evidence. | Prompt injection, sensitive logs, unchecked tool arguments, dynamic execution. |

## Proof Interfaces

The Python proof pack exposes:

- `supported_review_surfaces()` for listing supported review surfaces.
- `detect_language()` for metadata-level surface detection.
- `review_payload()` metadata with file, detected language or surface, supported surfaces, and rule count.
- `review_scenario_library()` for running universal scenarios through the same governed review model.

The command-line evaluator exposes:

```bash
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --list-surfaces
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --scenario-library
```

## New Universal Controls

This release adds or widens checks for:

- JavaScript `Function` constructor execution.
- Node child-process execution.
- Remote script execution through `curl` or `wget` piped to interpreters.
- Interpolated SQL execution.
- Root container runtime users.
- Wildcard infrastructure permissions.
- JavaScript JSON parsing without schema validation.
- Fetch calls without cancellation signals.
- Unpinned container base images.

## Claim Boundary

Accurate positioning:

This project provides universal static-review support for common software, AI, data, release, runtime, and infrastructure snippets.

Do not present it as complete language parsing, formal verification, production security certification, or a replacement for expert review. It is a governed evidence layer that makes review risk visible and repeatable.
