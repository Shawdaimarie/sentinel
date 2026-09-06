# Structured Output Schema

## Purpose

The evaluator can emit newline-delimited JSON so automated systems can ingest review results without parsing Markdown. This supports pull-request comments, release dashboards, audit logs, model-comparison reports, and calibration records.

## Command

```bash
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
```

## Record Types

| Record Type | Description |
| --- | --- |
| `summary` | One record per review with score, verdict, evidence level, promotion gate, risk index, and category counts. |
| `finding` | One record per detected issue with rule ID, category, severity, file, line, evidence, rationale, and recommendation. |

## Summary Payload

| Field | Meaning |
| --- | --- |
| `project` | Human-readable review name. |
| `score` | Review score from 0 to 100. |
| `verdict` | Human-readable outcome such as `security_blocker` or `approve_with_notes`. |
| `max_severity` | Highest detected severity. |
| `total_findings` | Number of rule-based findings. |
| `required_actions` | Deduplicated action list needed before promotion. |
| `risk_index` | Inverse of score, where higher means riskier. |
| `evidence_level` | Evidence readiness tier. |
| `promotion_gate` | Release decision gate. |
| `category_counts` | Finding totals by category. |

## Finding Payload

| Field | Meaning |
| --- | --- |
| `rule_id` | Stable rule identifier. |
| `category` | Rule finding category: security, correctness, reliability, performance, or data quality. |
| `severity` | Critical, high, medium, low, or info. |
| `file` | Reviewed file path. |
| `line` | Source line for the finding. |
| `title` | Short finding name. |
| `evidence` | Sanitized code excerpt or review signal. |
| `rationale` | Why the finding matters. |
| `recommendation` | Minimum expected fix. |

## Calibration Output

The reusable comparison helper returns a calibration report with:

- Project name.
- Winning candidate identifier.
- Score spread.
- Consensus gap.
- Overall decision.
- Ranked candidate summaries with score, risk index, promotion gate, max severity, finding totals, severe finding totals, and category counts.

## Current Sample Output Signal

The current risky sample produces 14 findings across security, correctness, reliability, performance, and data quality. It is intended as a synthetic evaluator demonstration, not as confidential production code.

## Hygiene Rules

- Keep records deterministic and line-oriented.
- Preserve stable field names for downstream tools.
- Avoid embedding secrets, account identifiers, private URLs, or proprietary snippets.
- Treat JSONL and calibration reports as machine-readable evidence, not as a replacement for human review.
