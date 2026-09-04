# Engineering case study: release gates for tool-using agents

## Problem

A tool-using agent can appear successful while violating the properties that
matter in production: it may call an unauthorized tool, disclose sensitive
content, omit evidence, exceed cost limits, loop on retries, or bypass human
approval. A single aggregate quality score can hide those failures.

## Decision

Sentinel uses a deterministic evaluation layer around observable run artifacts.
Cases are versioned with the code. Safety violations are hard failures, while
other dimensions retain weighted scores for diagnosis. Candidate runs can be
paired with a baseline so CI evaluates change rather than an isolated demo.

## Architecture

```text
versioned cases ─┐
                 ├─> strict validation ─> per-run metrics ─> hard gates
agent run JSONL ─┘                                 │
                                                  ├─> tag slices
baseline JSONL ────────────────────────────────────┴─> regression report
                                                           │
                                               Markdown + JSON + SHA-256
```

## Engineering tradeoffs

### Deterministic assertions over an opaque judge

Deterministic checks are limited, but they are reproducible. The harness uses
substring, action, evidence-domain, latency, cost, and action-budget assertions
for properties that can be observed directly. It does not claim to solve
open-ended semantic evaluation.

### Hard safety gates over compensating averages

A system that leaks a prohibited identifier should not pass because it is fast
and otherwise accurate. Safety failures therefore override the weighted score.

### Paired comparisons over unpaired headline metrics

Baseline and candidate results are paired by case and trial. A candidate is
blocked when it introduces a safety regression, turns a passing case into a
failure, or exceeds a declared score-regression tolerance.

### Evidence artifacts over console-only output

The CLI writes a reviewable Markdown report and a complete JSON record. Input
files are fingerprinted so a report can be tied to the exact fixtures used.

## Verification

The feature includes tests for:

- a fully compliant run;
- forbidden action execution;
- prohibited output disclosure;
- missing evidence;
- missing cases;
- duplicate run identifiers;
- unknown case references;
- safety regression detection;
- report provenance; and
- line-specific JSONL validation errors.

CI runs linting, strict type checks, unit/security tests, dependency audit, the
six-case example release gate, baseline comparison, and a non-root container
build.

## Next extensions

- Repeated-trial confidence intervals and variance alerts
- Provider adapters for captured OpenAI, Anthropic, Gemini, and local-model runs
- OpenTelemetry trace import
- PostgreSQL-backed longitudinal result storage
- Human-review queues for semantic dimensions
- Signed case bundles and provenance attestations
- Red-team datasets for indirect prompt injection and tool abuse
