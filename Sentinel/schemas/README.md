# Machine-readable contracts

These schemas define Sentinel evaluation, trace-import, and coding-agent review
artifacts.

- `eval-case.schema.json` — deterministic behavior expectations.
- `agent-run.schema.json` — provider-neutral observable run input.
- `otel-import-manifest.schema.json` — trace topology, retry evidence,
  completeness, redaction accounting, and source/configuration fingerprints.
- `code_review_cases.schema.json` — versioned human-review dimensions, case
  classes, expected decisions, and explicit critical findings.
- `code_review_report.schema.json` — reproducible scorecard output, reviewer
  actions, decisive failure modes, counts, and input fingerprint.

The OTLP importer deliberately writes provider fields to the manifest instead
of extending `AgentRun`; this keeps evaluation fixtures stable across tracing
vendors. The coding-agent scorecard similarly keeps human-assigned evidence
explicit rather than presenting the output as an automated proof of safety.
