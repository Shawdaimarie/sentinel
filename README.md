# Sentinel

**Governed AI-agent execution, deterministic evaluation, training-data quality gates, and production-trace normalization.**

[![CI](https://github.com/Shawdaimarie/sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/Shawdaimarie/sentinel/actions/workflows/ci.yml)
[![Trace import](https://github.com/Shawdaimarie/sentinel/actions/workflows/trace-import.yml/badge.svg)](https://github.com/Shawdaimarie/sentinel/actions/workflows/trace-import.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Sentinel is a reference platform for teams that need tool-using AI systems to be
**bounded, observable, testable, and reviewable** before those systems affect
operational infrastructure. It combines:

- deny-by-default policy enforcement;
- pre-execution audit decisions;
- governed network access;
- deterministic correctness, safety, grounding, latency, and cost evaluation;
- paired baseline regression gates;
- training/evaluation dataset quality gates before post-training claims;
- independently verifiable audit chains in Python, TypeScript, and Go; and
- offline OpenTelemetry trace normalization into strict evaluation records.

The implementation lives in [`Sentinel/`](Sentinel/).

## Engineering evidence

| Capability | Inspectable evidence |
|---|---|
| Agent governance | Every proposed action is evaluated before dispatch |
| Audit integrity | SHA-256/HMAC-SHA256 chain with sequence and downgrade checks |
| Production trace bridge | OTLP JSON becomes strict `AgentRun` JSONL plus a provenance manifest |
| Trace safety | Malformed IDs, cycles, ambiguous roots, and invented completeness fail closed |
| Sensitive-data handling | Configurable redaction and bounded unknown-provider metadata |
| Training data readiness | JSONL examples are checked for schema, source, privacy, splits, and risk coverage |
| Evaluation engineering | Versioned cases, hard safety gates, slices, and baseline comparison |
| Portable verification | Independent Python, TypeScript, and Go implementations share vectors |
| Delivery discipline | Python 3.11/3.12, Ruff, strict mypy, pytest, `pip-audit`, CodeQL, Docker |

## Trace-to-evaluation quick start

```bash
cd Sentinel
python -m pip install -e ".[dev]"

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

The `AgentRun` output remains provider-neutral and validates against the
existing schema. Trace topology, retry attempts, bounded metadata, completeness
markers, and source/configuration SHA-256 fingerprints are retained in a
separate manifest so the evaluator contract does not become vendor-specific.

Read the [trace-import protocol](Sentinel/docs/TRACE_IMPORT.md) and inspect the
[versioned OTLP fixture](Sentinel/examples/otel/agent_trace.json).

## Governed evaluation quick start

```bash
cd Sentinel
python -m pip install -e ".[dev]"

ruff check src tests
mypy src
pytest -q

sentinel-eval \
  --cases examples/eval_cases.jsonl \
  --runs examples/eval_runs.jsonl \
  --baseline-runs examples/baseline_runs.jsonl \
  --report reports/evaluation.md \
  --json-out reports/evaluation.json \
  --comparison-json reports/comparison.json \
  --min-score 0.90
```

## Training-data quality quick start

```bash
cd Sentinel
python -m pip install -e ".[dev]"

sentinel-data-gate \
  --input examples/training/agent_safety_examples.jsonl \
  --json-out reports/data-gate/agent_safety_examples.json \
  --markdown-out reports/data-gate/agent_safety_examples.md \
  --min-examples 20
```

The data gate checks training and evaluation examples before fine-tuning,
preference optimization, benchmark publication, or public proof claims.

## Architecture

```text
OTLP JSON export ──> topology + identifier validation ──> redaction
       │                                                   │
       └───────────────────────────────────────────────────┤
                                                           ▼
                                       strict AgentRun JSONL + manifest
                                                           │
versioned cases ───────────────────────────────────────────┤
                                                           ▼
                                           deterministic evaluator
                                                           │
                                     hard safety + regression release gate

agent proposal ──> deny-by-default policy ──> audit decision ──> execute/deny
                                              │
                                              ▼
                         portable SHA-256/HMAC-SHA256 verification

training examples ──> schema + privacy + split checks ──> data gate report
```

## Reviewer path

A technical reviewer can evaluate the work without relying on résumé language:

1. Read the [architecture](Sentinel/ARCHITECTURE.md),
   [security model](Sentinel/SECURITY.md), and
   [trace-import protocol](Sentinel/docs/TRACE_IMPORT.md).
2. Inspect the [policy engine](Sentinel/src/sentinel/policy.py),
   [audit chain](Sentinel/src/sentinel/audit.py),
   [evaluation engine](Sentinel/src/sentinel/evaluation.py), and
   [OTLP importer](Sentinel/src/sentinel/trace_import.py).
3. Run the [unit and security tests](Sentinel/tests/) and the
   [trace-import workflow](.github/workflows/trace-import.yml).
4. Review the [example evaluation evidence](Sentinel/examples/reports/) and
   [OTLP fixture evidence](Sentinel/examples/otel/).
5. Verify the [portable audit specification](Sentinel/spec/SPEC.md) with the
   independent [Python, TypeScript, and Go verifiers](Sentinel/verifiers/).

## Why this work matters

Agent reliability is a systems problem, not only a model-selection problem.
Permissions, trace completeness, evidence quality, failure behavior, latency,
cost, human approval, and audit integrity all affect whether an AI workflow can
be trusted with broader operational authority. Sentinel makes those properties
explicit and testable.

The project is informed by the
[NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework),
its [Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence),
and the
[OWASP AI Agent Security guidance](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html).

## Scope and limits

Sentinel is a reference implementation, not an AI certification and not a
claim of universal safety. The OTLP importer supports an explicit subset of
semantic conventions and never treats absent telemetry as evidence of success.
A retained hash chain detects alteration of retained records; it does not prove
that a log is complete. Consequential deployments still require domain-specific
cases, repeated trials, calibrated human review, external digest anchoring,
production identity and secrets management, monitoring, and independent
security assessment.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
