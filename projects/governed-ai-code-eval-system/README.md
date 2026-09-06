# Governed AI Code Evaluation System

Live application deployment: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

## Project Type

Interactive AI engineering and software engineering application for evaluating generated code through governed review gates.

## What It Does

The application provides a reviewer-facing workspace where candidate code can be assessed before it is accepted, promoted, or used as proof of engineering quality.

It produces:

- Readiness score.
- Risk index.
- Categorized findings.
- Evidence maturity signal.
- Promotion gate.
- Required remediation actions.
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
- Structured technical communication.
- Release hygiene and verification.

## Application Workflow

1. Name the review.
2. Evaluate candidate code.
3. Mark supporting evidence such as tests, threat model, and performance budget.
4. Review scored findings and required actions.
5. Use the promotion gate to decide whether the code can move forward.
6. Preserve JSONL output as machine-readable evidence.

## Evidence Package

This GitHub project package includes:

- [Application user guide](./docs/APPLICATION_USER_GUIDE.md).
- [Governed approval rubric](./docs/GOVERNED_APPROVAL_RUBRIC.md).
- [Structured output schema](./docs/STRUCTURED_OUTPUT_SCHEMA.md).
- [Handshake-ready project entry](./docs/HANDSHAKE_PROJECT_ENTRY.md).
- Security and publication boundaries.
- Verification record for the application release.

The deployed application source was committed locally as `7c3636e1a8ed573be951ddcf0de4b5cd928158ba` and saved as Sites version 9.

## Verification Record

Verified on September 5, 2026:

```bash
pnpm run assurance
pnpm run lint
pnpm run build
pnpm run build
python3 -m unittest discover -s packages/evaluator/tests
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
python3 -m compileall packages/evaluator/src packages/evaluator/tests
```

## Claim Boundary

This project supports top-tier candidate readiness through visible, governed evidence. It does not claim external certification, clearance, employer approval, or institutional endorsement unless such validation is separately granted by an external reviewer.
