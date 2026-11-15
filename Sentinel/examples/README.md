# Evaluation examples

This directory contains small deterministic fixtures that demonstrate Sentinel's
release-gate and human-review workflows. They are not production safety
benchmarks.

## Agent behavior evaluation

- `eval_cases.jsonl` defines six observable behaviors.
- `baseline_runs.jsonl` represents a slower, more expensive baseline.
- `eval_runs.jsonl` represents a candidate with equivalent behavior and lower
  recorded latency/cost.
- `reports/` contains generated example output.

```bash
sentinel-eval \
  --cases examples/eval_cases.jsonl \
  --runs examples/eval_runs.jsonl \
  --baseline-runs examples/baseline_runs.jsonl \
  --report examples/reports/evaluation.md \
  --json-out examples/reports/evaluation.json \
  --comparison-json examples/reports/comparison.json
```

## Fictional engineering-company workflow

The [Aetherion Technologies demo](aetherion/README.md) exercises Sentinel's
deny-by-default policy, local audit-chain verification, deterministic evaluation
and synthetic OpenTelemetry trace normalization alongside a separate Aegis
Go policy-matching fixture. Aetherion is fictional; this is not customer or
production deployment evidence.

## Coding-agent review scorecard

`code_review_scorecard_cases.json` covers safe, unsafe, incomplete,
over-engineered, and unverifiable code-agent responses. The expected outcomes
exercise `accept`, `accept_with_edits`, `needs_human_design`, and `reject`.
Explicit critical findings demonstrate that a polished answer cannot average
away secret exposure, destructive actions, or fabricated evidence.

```bash
sentinel-code-review \
  --cases examples/code_review_scorecard_cases.json \
  --json-out examples/reports/code_review_scorecard.json \
  --markdown-out examples/reports/code_review_scorecard.md
```

Read the
[coding-agent review rubric](../docs/CODING_AGENT_REVIEW_RUBRIC.md) and inspect
the machine-readable contracts in [`../schemas/`](../schemas/).

The fixture data are illustrative. A production benchmark should capture real
system traces, use repeated trials, include domain-specific red-team cases, and
add calibrated human review for open-ended semantic quality.
