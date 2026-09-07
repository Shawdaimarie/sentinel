# Structured Output Schema

## Purpose

The evaluator can emit newline-delimited JSON and scenario JSON so automated systems can ingest review results without parsing Markdown. This supports pull-request comments, release dashboards, audit logs, model-comparison reports, calibration records, and universal-support packets.

## Command

```bash
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
```

## Record Types

| Record Type | Description |
| --- | --- |
| `summary` | One record per review with score, verdict, evidence level, promotion gate, risk index, and category counts. |
| `metadata` | One record per review with file, detected or supplied language/surface, supported surfaces, and active rule count. |
| `finding` | One record per detected issue with rule ID, category, severity, file, line, evidence, rationale, and recommendation. |
| `calibration_summary` | One record per model-comparison report with winner, score spread, consensus gap, decision, and project name. |
| `calibration_candidate` | One record per ranked candidate with score, risk index, promotion gate, severity signal, finding counts, and category counts. |

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

## Metadata Payload

Each review payload includes metadata:

| Field | Meaning |
| --- | --- |
| `file` | Reviewed file path or synthetic scenario file name. |
| `language` | Detected or supplied language and surface label. |
| `supported_surfaces` | Universal support matrix exposed by the evaluator. |
| `rule_count` | Active default rules plus contextual scale-review signal. |

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

## Hygiene Rules

- Keep records deterministic and line-oriented.
- Preserve stable field names for downstream tools.
- Avoid embedding secrets, account identifiers, private URLs, or proprietary snippets.
- Treat JSONL, scenario JSON, and support metadata as machine-readable evidence, not as replacements for human review.

## Scenario Library Output

The command-line evaluator can emit the sanitized scenario library:

```bash
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --scenario-library
```

The output includes each scenario definition and its governed review payload. Use it for reviewer packets, dashboard seeds, or future pull-request summaries.

## Supported Surface Output

The command-line evaluator can emit the supported review surface list:

```bash
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --list-surfaces
```

The output includes the active rule count and supported surfaces for Python, TypeScript/JavaScript, SQL/data access, shell/release scripts, container images, infrastructure policy, AI/ML workflows, and agent tooling.

## Calibration Output

The reusable comparison helper returns a calibration report with:

- Project name.
- Winning candidate identifier.
- Score spread.
- Consensus gap.
- Overall decision.
- Ranked candidate summaries with score, risk index, promotion gate, max severity, finding totals, severe finding totals, and category counts.

`calibration_report_to_jsonl()` converts that report into line-oriented records for automation, review packets, and calibration audit logs.

The browser application also supports a local calibration audit snapshot. That snapshot stores review metadata, weights, rankings, score spread, confidence signal, and decision gates in the browser. It should not contain candidate source code, secrets, private links, account identifiers, or proprietary task text.
