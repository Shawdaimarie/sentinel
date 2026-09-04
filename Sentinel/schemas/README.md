# Machine-readable contracts

These schemas define Sentinel evaluation and trace-import artifacts.

- `eval-case.schema.json` — deterministic behavior expectations.
- `agent-run.schema.json` — provider-neutral observable run input.
- `otel-import-manifest.schema.json` — trace topology, retry evidence,
  completeness, redaction accounting, and source/configuration fingerprints.

The OTLP importer deliberately writes provider fields to the manifest instead
of extending `AgentRun`; this keeps evaluation fixtures stable across tracing
vendors.
