# Application User Guide

## Purpose

The application is a live governed review workspace for evaluating generated code before it is accepted, promoted, or used as portfolio evidence.

It converts candidate code and supporting evidence into:

- A numerical readiness score.
- A risk index.
- Categorized findings.
- A promotion gate.
- Required remediation actions.
- Newline-delimited JSON review output for automation.
- Model-calibration ranking.
- A local calibration audit trail for repeated model-comparison decisions.
- Scenario evidence for AI/ML workflow review.

## Primary Workflow

1. Open the application workspace.
2. Name the review.
3. Select the evidence that has been attached: tests, threat model, and performance budget.
4. Review or edit the candidate code.
5. Inspect the score, risk index, evidence level, findings, and promotion gate.
6. Use the JSONL output as the machine-readable review artifact.
7. Use the Model Calibration Lab when comparing multiple model or implementation candidates.
8. Save a local calibration snapshot or copy the audit JSON when the comparison needs decision evidence.
9. Use the Scenario Evidence Library when proving review breadth across AI/ML workflows.

## Review Lenses

The application checks candidate code across seven reviewer-facing lenses:

- Security
- Correctness
- Data quality
- Reliability
- Performance
- Maintainability
- Evidence quality

## Promotion Gates

| Gate | Meaning |
| --- | --- |
| `Security Blocker` | Critical risk is present and release should stop. |
| `Remediation Required` | High-severity issues remain before promotion. |
| `Evidence Hold` | Technical findings may be acceptable, but proof is incomplete. |
| `Approve With Notes` | Non-blocking findings remain and should be tracked. |
| `Promotion Ready` | No governed findings are present and evidence is complete. |

## Reviewer Value

The application demonstrates practical AI engineering judgment because it does not treat model-generated code as automatically trustworthy. It requires inspectable proof, shows the reasoning behind each finding, and converts review outcomes into a format suitable for CI comments, audit logs, dashboards, model-comparison reports, and scenario-based evaluation packets.

## Model Calibration Lab

The application includes a calibration workspace for comparing multiple candidate outputs. Reviewers can adjust weights for AI security boundary, task correctness, data reliability, and operational readiness, then inspect the score spread, top candidate, and decision gate.

This is designed for AI-sector evaluation work where the value is not only finding issues in one answer, but comparing model outputs consistently and documenting why one candidate should advance.

## Calibration Audit Trail

The application can save calibration snapshots in the browser. Each snapshot records the review name, timestamp, winning candidate, score spread, confidence signal, weights, candidate ranks, weighted scores, and decision gates.

The audit trail is local-first. It does not send data to a server, and it does not store candidate source code. Use the copied audit JSON when a reviewer, portfolio package, or project record needs repeatable decision evidence.

## Scenario Evidence Library

The Scenario Evidence Library demonstrates evaluator breadth across four sanitized AI/ML workflows:

- Model training leakage review.
- Inference artifact control review.
- MLOps supply-chain review.
- Agent tool-boundary review.

Each scenario maps a workflow to expected findings and a governed hold condition. Use it when a reviewer needs evidence that the system can reason beyond one hand-selected sample.

## High-Value Method Layer

The application includes method alignment for AI research systems, secure AI governance, software/platform engineering, model calibration, audit evidence, AI/ML scenario review, and data-quality evaluation tooling. These lanes are tied to public labor-market signals and to concrete controls inside the evaluator.

## Public Release Boundaries

- Do not include confidential client names, private access links, account identifiers, or proprietary task text.
- Do not claim certification, clearance, ranking, or endorsement unless an external authority has granted it.
- Keep sample code synthetic and sanitized.
- Treat the application as a reviewer-ready proof asset, not as a replacement for professional review.
