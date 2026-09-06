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

## Primary Workflow

1. Open the application workspace.
2. Name the review.
3. Select the evidence that has been attached: tests, threat model, and performance budget.
4. Review or edit the candidate code.
5. Inspect the score, risk index, evidence level, findings, and promotion gate.
6. Use the JSONL output as the machine-readable review artifact.

## Review Lenses

The application checks candidate code across six reviewer-facing lenses:

- Security
- Correctness
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

The application demonstrates practical AI engineering judgment because it does not treat model-generated code as automatically trustworthy. It requires inspectable proof, shows the reasoning behind each finding, and converts review outcomes into a format suitable for CI comments, audit logs, dashboards, and model-comparison reports.

## Public Release Boundaries

- Do not include confidential client names, private access links, account identifiers, or proprietary task text.
- Do not claim certification, clearance, ranking, or endorsement unless an external authority has granted it.
- Keep sample code synthetic and sanitized.
- Treat the application as a reviewer-ready proof asset, not as a replacement for professional review.
