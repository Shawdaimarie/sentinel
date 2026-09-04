# OpenTelemetry trace import protocol

## Purpose

`sentinel-import-otel` converts an offline OTLP JSON export into two artifacts:

1. strict Sentinel `AgentRun` JSONL for deterministic evaluation; and
2. a provenance manifest containing trace topology, retry attempts, bounded
   metadata, completeness markers, redaction counts, and source/configuration
   SHA-256 fingerprints.

The separation is intentional. `AgentRun` remains provider-neutral and stable,
while the manifest retains operational trace evidence that does not belong in
the evaluator's core contract.

## Security boundary

Trace files are untrusted input. The importer:

- never executes trace content;
- never opens a URL found in a span;
- never contacts an observability or model provider;
- validates trace and span identifiers;
- rejects duplicate span IDs, parent cycles, and ambiguous roots;
- strips URL credentials and redacts sensitive query parameters;
- redacts common authorization, cookie, token, password, API-key, secret, and
  direct personal-identifier attributes; and
- bounds unknown-provider metadata by count and value length.

The importer is not a data-loss-prevention system. Teams must extend the
redaction list for domain-specific identifiers and must review trace-export
policy before collecting production data.

## Supported input shapes

The importer accepts either:

- standard OTLP JSON `resourceSpans[].scopeSpans[].spans[]`; or
- a simplified top-level `spans[]` array for deterministic fixtures.

Legacy `instrumentationLibrarySpans` is accepted as an alias for `scopeSpans`.
Trace IDs must be 32 hexadecimal characters and span IDs must be 16 hexadecimal
characters.

## Minimal semantic mapping

Sentinel deliberately supports a small, explicit mapping while generative-AI
semantic conventions continue to evolve.

| Sentinel field | Accepted OTLP attributes |
|---|---|
| Case ID | `sentinel.case.id`, `eval.case.id`, `case.id`, or `--case-id` |
| Run ID | `sentinel.run.id`, `run.id`, otherwise trace ID |
| System | `sentinel.system`, `service.name`, otherwise `--system` |
| Output | `sentinel.output`, `gen_ai.response.text`, `gen_ai.output.messages`, `output.value` |
| Tool name | `gen_ai.tool.name`, `sentinel.tool.name`, `tool.name` |
| Tool target | `sentinel.tool.target`, `url.full`, `http.url`, `db.operation.name`, `db.statement` |
| Action status | `sentinel.action.status`, `tool.status`, otherwise span status |
| Retry attempt | `sentinel.retry.attempt`, `retry.attempt`, `tool.attempt`, otherwise derived order |
| Approval | `sentinel.approval.status`, `approval.status`, `approval.decision` |
| Evidence | `sentinel.evidence.url(s)`, `gen_ai.evidence.url`, `evidence.url` |
| Cost | `sentinel.cost.usd`, `gen_ai.usage.cost`, `gen_ai.cost.usd` |

A span is treated as a tool when one of the following is true:

- `sentinel.span.kind=tool`;
- `openinference.span.kind=TOOL`;
- `gen_ai.operation.name` is `execute_tool` or `tool_call`; or
- the span name begins with `tool.`.

Approval spans and events remain distinct from executed tools.

## Completeness rules

A trace has exactly one root. A span whose parent is absent from the export can
serve as the root only when it is the sole root candidate; the run is then
marked partial.

The importer marks an `AgentRun` incomplete when the trace lacks:

- final output;
- root start time;
- root end time; or
- the root's parent span in a partial export.

An incomplete run is emitted with `completed=false` and an explicit error such
as:

```text
partial telemetry: missing output, root.endTimeUnixNano
```

The importer never converts missing telemetry into successful behavior.

## Ordering and retries

Tool spans and approval events are sorted by nanosecond start/event time, then
by stable identifiers. The strict `AgentRun.actions` list preserves this order.
The manifest additionally stores:

- span ID;
- parent span ID;
- normalized action name and target;
- action status;
- retry attempt;
- event time; and
- bounded metadata.

Explicit retry attributes take precedence. When absent, attempts are derived
from repeated name/target pairs in chronological order.

## Redaction and metadata policy

Common sensitive keys are removed automatically. Add domain-specific keys with:

```bash
--redact customer.account_id --redact health.member_id
```

Unknown attributes are retained only in the manifest, sorted deterministically,
and limited by:

```bash
--metadata-limit 32 --metadata-value-limit 256
```

The strict `AgentRun` output therefore remains compatible with the existing
schema and does not inherit arbitrary vendor fields.

## Reproducibility

The manifest records:

- importer identifier;
- SHA-256 of the exact source bytes;
- SHA-256 of the canonical importer configuration, including the effective
  redaction set;
- trace and run counts;
- partial-run count;
- redaction count;
- warnings; and
- per-trace topology.

Given identical source bytes, configuration, and Sentinel version, output order
and manifest content are deterministic.

## CLI

```bash
sentinel-import-otel \
  --input trace.json \
  --output reports/runs.jsonl \
  --manifest reports/import-manifest.json \
  --system candidate \
  --case-id optional-global-override \
  --redact customer.account_id
```

The command returns:

- `0` on successful normalization;
- `2` for invalid JSON, topology, identifiers, configuration, or I/O errors.

## Unsupported conventions and residual risk

The current importer does not provide:

- live collection or an OpenTelemetry Collector deployment;
- provider API authentication;
- protobuf OTLP parsing;
- distributed-trace stitching across separate export files;
- model-based grading;
- semantic interpretation of arbitrary vendor payloads;
- proof that an export contains every span produced; or
- automatic legal or privacy compliance.

A production pipeline should enforce collection policy upstream, preserve raw
exports in access-controlled storage, review domain-specific sensitive fields,
and anchor source/manifests in an independently controlled evidence store.
