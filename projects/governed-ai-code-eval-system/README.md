# Governed AI Code Evaluation System

Live application deployment: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

## Project Type

Interactive AI engineering and software engineering application for evaluating generated code, comparing model outputs, and preserving governed calibration evidence.

## What It Does

The application provides a reviewer-facing workspace where candidate code can be assessed before it is accepted, promoted, or used as proof of engineering quality.

It produces:

- Readiness score.
- Risk index.
- Categorized findings.
- Evidence maturity signal.
- Promotion gate.
- Required remediation actions.
- Model-calibration ranking.
- Local calibration audit snapshots.
- Newline-delimited JSON output for automation.

## Technical Value

This project demonstrates practical ability in high-demand technology areas:

- AI engineering.
- AI infrastructure.
- Software engineering.
- Secure coding.
- Code-agent evaluation.
- LLM application review.
- Model-output adjudication.
- Comparative model-output calibration.
- Calibration audit evidence.
- AI security and prompt-injection boundary review.
- Data-quality validation for generated or remote output.
- Structured technical communication.
- Release hygiene and verification.

## High-Value Method Layer

The current version maps the application to market-supported technology methods:

- AI research and evaluation systems.
- Secure AI and cybersecurity governance.
- Software and platform engineering.
- Data quality and model-evaluation tooling.
- Model-comparison calibration.
- Calibration audit trail.
- Executive technical review and release governance.

The project uses public labor-market sources from the U.S. Bureau of Labor Statistics to keep positioning grounded and accurate rather than inflated.

See: [High-value method alignment](./docs/HIGH_VALUE_METHOD_ALIGNMENT.md).

## Model Calibration Layer

The current release includes a Model Calibration Lab, reusable Python comparison helper, and local calibration audit trail. This supports AI-sector work where multiple candidate outputs must be ranked with consistent criteria before one is advanced.

Calibration criteria include:

- AI security boundary.
- Task correctness.
- Data reliability.
- Operational readiness.

See: [Model calibration protocol](./docs/MODEL_CALIBRATION_PROTOCOL.md).

## Calibration Audit Trail

The live application can save calibration snapshots locally in the browser and copy audit JSON for review packets. The audit trail preserves review metadata, score spread, weights, candidate ranks, and decision gates without storing candidate source code.

The Python proof pack also exposes `calibration_report_to_jsonl()` for line-oriented calibration evidence.

See: [Calibration audit trail](./docs/CALIBRATION_AUDIT_TRAIL.md).

## Application Workflow

1. Name the review.
2. Evaluate candidate code.
3. Mark supporting evidence such as tests, threat model, and performance budget.
4. Review scored findings and required actions.
5. Use the promotion gate to decide whether the code can move forward.
6. Compare candidate outputs in the calibration lab when more than one model or implementation is being evaluated.
7. Save a local calibration snapshot or copy the audit JSON when comparison evidence should be preserved.
8. Preserve JSONL output as machine-readable evidence.

## Evidence Package

This GitHub project package includes:

- [Application user guide](./docs/APPLICATION_USER_GUIDE.md).
- [Governed approval rubric](./docs/GOVERNED_APPROVAL_RUBRIC.md).
- [Structured output schema](./docs/STRUCTURED_OUTPUT_SCHEMA.md).
- [High-value method alignment](./docs/HIGH_VALUE_METHOD_ALIGNMENT.md).
- [Model calibration protocol](./docs/MODEL_CALIBRATION_PROTOCOL.md).
- [Calibration audit trail](./docs/CALIBRATION_AUDIT_TRAIL.md).
- [Handshake-ready project entry](./docs/HANDSHAKE_PROJECT_ENTRY.md).
- Security and publication boundaries.
- Verification record for the application release.

The deployed application source was committed locally as `9a398ed4659bd2999dc9dbe8a7bcb47db672fd98` and saved as Sites version 12.

## Current Proof Signals

- Evaluator tests: `10` passing.
- Sample governed review output: `14` findings across security, correctness, reliability, performance, and data quality.
- Calibration proof ranks the safer candidate first with high consensus separation.
- Calibration audit proof emits `calibration_summary` and ranked `calibration_candidate` JSONL records.
- Advanced AI-risk checks include prompt-injection bypass phrases, sensitive logging, unsafe model-output parsing, unsafe execution, hardcoded secret-like values, unsafe YAML/pickle deserialization, and missing network timeouts.
- The release passed assurance, lint, production build twice, Python unit tests, JSONL evaluator output, calibration audit proof, Python compilation, and a publication-boundary scan.

## Verification Record

Verified on September 6, 2026:

```bash
pnpm run assurance
pnpm run lint
pnpm run build
pnpm run build
python3 -m unittest discover -s packages/evaluator/tests
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
PYTHONPATH=packages/evaluator/src python3 -c "from governed_ai_code_eval import calibration_report_to_jsonl, compare_candidate_reviews; report = compare_candidate_reviews('calibration proof', [('safe', 'def ok():\n    return 1\n'), ('risky', 'result = eval(user_input)\n')], tests_present=True, threat_model_present=True, performance_budget_present=True); assert report.winner == 'safe'; assert 'calibration_summary' in calibration_report_to_jsonl(report)"
python3 -m compileall packages/evaluator/src packages/evaluator/tests packages/evaluator/examples
```

## Claim Boundary

This project supports top-tier candidate readiness through visible, governed evidence. It does not claim external certification, clearance, employer approval, guaranteed ranking, or institutional endorsement unless such validation is separately granted by an external reviewer.
