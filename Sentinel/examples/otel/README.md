# OTLP import example

This directory is a deterministic, credential-free example of Sentinel's
production-trace bridge.

- `agent_trace.json` — OTLP JSON export with an agent root, two tool attempts,
  approval evidence, cost, output, and a deliberately sensitive query value.
- `agent_runs.jsonl` — strict provider-neutral `AgentRun` output.
- `import_manifest.json` — source/configuration hashes, redaction count,
  completeness, topology, retry attempts, and bounded metadata.
- `eval_case.jsonl` — deterministic expectations used to evaluate the imported
  run in CI.

Regenerate and evaluate:

```bash
sentinel-import-otel \
  --input examples/otel/agent_trace.json \
  --output reports/otel-agent-runs.jsonl \
  --manifest reports/otel-import-manifest.json

sentinel-eval \
  --cases examples/otel/eval_case.jsonl \
  --runs reports/otel-agent-runs.jsonl \
  --report reports/otel-evaluation.md \
  --json-out reports/otel-evaluation.json \
  --min-score 0.90
```

The fixture is illustrative. It is not evidence that a deployed third-party
agent was evaluated or certified.
