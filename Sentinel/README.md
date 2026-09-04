# Sentinel

**Governed agent execution, deterministic evaluation, and offline production-trace normalization.**

Sentinel is a Python 3.11+ reference platform for evaluating and controlling
tool-using AI workflows. It keeps authorization, execution, audit evidence,
trace provenance, and release decisions separate enough to inspect and test.

## Capabilities

### Governed execution

- Deny-by-default policy evaluation before every action.
- Decision logging before side effects.
- Per-agent action and network boundaries.
- Manual redirect handling with policy evaluation at each hop.
- SHA-256 or HMAC-SHA256 audit chaining.

### Deterministic evaluation

- Strict `EvalCase` and `AgentRun` contracts.
- Correctness, safety, grounding, tool-use, latency, cost, and action budgets.
- Hard failures for forbidden actions and prohibited output.
- Candidate-versus-baseline regression analysis.
- Markdown and JSON evidence with input fingerprints.

### OpenTelemetry import

- Offline OTLP JSON parsing; no provider credentials or network access.
- Trace/span identifier and topology validation.
- Deterministic root selection and cycle detection.
- Tool, retry, approval, evidence, latency, and cost normalization.
- Fail-closed partial-trace handling.
- Configurable sensitive-attribute redaction.
- Bounded preservation of unknown provider metadata.
- Strict `AgentRun` JSONL plus a separate provenance manifest.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Import a trace export

```bash
sentinel-import-otel \
  --input examples/otel/agent_trace.json \
  --output reports/otel-agent-runs.jsonl \
  --manifest reports/otel-import-manifest.json
```

Additional sensitive attributes can be removed with repeated flags:

```bash
sentinel-import-otel \
  --input trace.json \
  --output runs.jsonl \
  --redact customer.account_id \
  --redact vendor.private_payload
```

A trace with missing output or root timestamps is emitted as
`completed=false` with an explicit `partial telemetry` error. Multiple roots,
cycles, malformed identifiers, duplicate span IDs, or a missing case identifier
fail the import rather than being guessed.

See [`docs/TRACE_IMPORT.md`](docs/TRACE_IMPORT.md) for the mapping and security
boundary.

## Evaluate imported runs

```bash
sentinel-eval \
  --cases examples/otel/eval_case.jsonl \
  --runs reports/otel-agent-runs.jsonl \
  --report reports/otel-evaluation.md \
  --json-out reports/otel-evaluation.json \
  --min-score 0.90
```

## Run a governed claim-verification workflow

```bash
sentinel run \
  --page https://essentialdigitalsolution.com/ \
  --control https://essentialdigitalsolution.com/

sentinel verify-audit
```

For keyed audit integrity:

```bash
export SENTINEL_AUDIT_KEY="material-from-a-secret-manager"
sentinel run --page https://example.com
sentinel verify-audit
```

Introducing a key requires a new log file; a log is entirely keyed or entirely
unkeyed.

## Quality gates

```bash
make install
make quality
make test
make import-otel
make compare
make docker
```

GitHub Actions runs Ruff, strict mypy, pytest, dependency audit, deterministic
evaluation, OTLP normalization, imported-run evaluation, portable
Python/TypeScript/Go conformance, CodeQL, and a non-root container build.

## Repository map

```text
src/sentinel/
  policy.py             policy evaluation and budgets
  audit.py              hash/HMAC audit chain
  http.py               governed retrieval
  evaluation.py         deterministic scoring and release gates
  trace_import.py       OTLP JSON normalization and provenance
  trace_cli.py          sentinel-import-otel CLI
  agents/               governed crawler/verifier/prober/reporter

tests/                  unit, security, evaluation, trace-import tests
examples/otel/           trace fixture, strict run output, manifest, eval case
schemas/                 JSON contracts
spec/                    portable audit profile and vectors
verifiers/               independent Python, TypeScript, and Go verification
docs/                    protocols, crosswalks, case study, roadmap
```

## Interpretation boundary

Sentinel does not certify an agent as safe. It makes a defined set of behaviors,
limits, and evidence inspectable. Coverage remains bounded by the trace data and
versioned cases provided. Production use requires domain-specific cases,
repeated trials, human review, external audit storage, operational monitoring,
and independent security assessment.
