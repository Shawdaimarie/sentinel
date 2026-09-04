# Evaluation examples

This directory contains a small deterministic benchmark that demonstrates the
release-gate workflow. It is not a production safety benchmark.

- `eval_cases.jsonl` defines six observable behaviors.
- `baseline_runs.jsonl` represents a slower, more expensive baseline.
- `eval_runs.jsonl` represents a candidate with equivalent behavior and lower
  recorded latency/cost.
- `reports/` contains generated example output from `sentinel-eval`.

Run:

```bash
sentinel-eval \
  --cases examples/eval_cases.jsonl \
  --runs examples/eval_runs.jsonl \
  --baseline-runs examples/baseline_runs.jsonl \
  --report examples/reports/evaluation.md \
  --json-out examples/reports/evaluation.json \
  --comparison-json examples/reports/comparison.json
```

The fixture data are illustrative. A production benchmark should capture real
system traces, use repeated trials, include domain-specific red-team cases,
and add calibrated human review for open-ended semantic quality.
