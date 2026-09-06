# Structured Output Schema

## Purpose

The evaluator can emit newline-delimited JSON so automated systems can ingest review results without parsing Markdown. This supports pull-request comments, release dashboards, audit logs, and future model-comparison reports.

## Record Types

| Record Type | Description |
| --- | --- |
| `summary` | One record per review with score, verdict, evidence level, promotion gate, risk index, and category counts. |
| `finding` | One record per detected issue with rule ID, category, severity, file or line, evidence, rationale, and recommendation. |

## Summary Payload

| Field | Meaning |
| --- | --- |
| `project` | Human-readable review name. |
| `score` | Review score from 0 to 100. |
| `verdict` | Machine-friendly outcome such as `security_blocker` or `promotion_ready`. |
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
| `category` | Security, correctness, reliability, performance, maintainability, or evidence. |
| `severity` | Critical, high, medium, low, or info. |
| `line` | Source line for browser findings, or null for package-level evidence gaps. |
| `title` | Short finding name. |
| `evidence` | Sanitized code excerpt or review signal. |
| `rationale` | Why the finding matters. |
| `recommendation` | Minimum expected fix. |

## Hygiene Rules

- Keep records deterministic and line-oriented.
- Preserve stable field names for downstream tools.
- Avoid embedding secrets, account identifiers, private URLs, or proprietary snippets.
- Treat JSONL as machine-readable evidence, not as a replacement for human review.
