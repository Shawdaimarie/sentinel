# Repeated evaluation diagnostics

A high mean score can coexist with an intermittent failure. Sentinel can now
write an optional per-case diagnostic report alongside its usual evaluation:

```sh
sentinel-eval \
  --cases examples/otel/eval_case.jsonl \
  --runs examples/otel/agent_runs.jsonl \
  --trials-json reports/trials.json \
  --json-out reports/evaluation.json \
  --report reports/evaluation.md
```

Run this from `Sentinel/` after installing the package. This bundled synthetic
fixture contains only one observation, so `sample_stddev_score` is `null` and the
report warns that dispersion is unavailable. No provider credentials are needed.

For repeated evaluations, capture independent executions of the same case in
the runs JSONL file with a distinct `run_id` for each execution. Keep the model,
model version, prompt, tool policy, and generation configuration fixed under the
selected `--system`. Record seeds and execution provenance separately where
available. Renaming or copying one run does not create another real trial.

Each case is reported separately, with sorted run IDs, observed sample count,
mean, median, minimum, maximum, sample standard deviation (using n - 1), failure
count/rate, and safety failure count/rate. The report copies the source file
fingerprints and the evaluator's existing gate result. Cases with unequal trial
counts are not pooled into a new cross-case average.

Missing-run placeholders are reported separately from observed samples. Their
statistics are null, not zero, and they cannot produce an all-safe result. A
single observed run has no sample standard deviation. Any observed safety
failure remains visible in `safety_failed_runs` and makes
`all_observed_runs_safe` false, including when evaluation thresholds are relaxed.

This report is descriptive and does not change evaluation thresholds, exit codes,
human approval, or release decisions. The default evaluator still fails the
suite for a safety failure. Do not treat a relaxed gate result as evidence that
all repeated observations were safe.

These summaries provide no confidence intervals or independence guarantee.
Small samples can miss rare failures; identical results do not establish
reliability. This is the descriptive-statistics portion of issue #13, not its
full repeated-trial gating or calibrated human-review workflow.
