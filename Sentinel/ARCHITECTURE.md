# Architecture

## Components

```text
                       ┌──────────────┐
                       │ policy.yaml  │
                       └──────┬───────┘
                              │ load
                              ▼
   pages ──► crawler ──► verifier ──┐        ┌──────────┐
                                    ├──► reporter ──► reports/YYYY-MM-DD.md
   controls ─► prober ──────────────┘        └──────────┘
        │           │          │                  │
        └───────────┴──────────┴──────────────────┘
                      every act() ──► audit/sentinel.jsonl

   eval cases ──┐
                ├──► deterministic evaluator ──► release gate + reports
   agent runs ──┘                    ▲
   baseline runs ────────────────────┘
```

### Policy engine (`policy.py`)

Loads a declarative document and answers one question: may this agent perform
this action on this target now? Evaluation checks, in order: the agent is
declared; the action is allowed; its per-run budget remains; HTTP targets are
inside the domain boundary; and filesystem targets remain under an allowed
prefix without traversal. Any failure returns a denial with a stated reason.
Nothing is permitted by omission.

The engine holds per-run counters, so one instance is created per orchestrator
run and shared across agents. Denied actions do not consume budget.

### Audit log (`audit.py`)

Append-only JSON Lines. Each record carries the digest of the previous record
and its own digest over all other fields—SHA-256 when unkeyed and HMAC-SHA256
when `SENTINEL_AUDIT_KEY` is set. Verification walks the file and raises on the
first sequence gap, chain break, keyed-to-unkeyed downgrade, or content
mismatch. A reopened process continues the chain from the final record.

Tampering is detectable, not impossible. Truncation of the tail is not detected
by the chain alone; production deployment requires external append-only
storage.

### Agent base (`agents/base.py`)

`Agent.act(action, target, **payload)` is the sole dispatch path. It evaluates,
appends the decision, and only then invokes a registered executor when the
decision is allowed. A crash during execution therefore leaves evidence that
the action was authorized and attempted.

### Governed retrieval (`http.py`)

The crawler and verifier fetch through `governed_get`. Automatic redirects are
disabled; every hop is resubmitted to `Agent.act`. Private, loopback,
link-local, userinfo-bearing, non-HTTP, oversized, and non-textual responses are
rejected at the network trust boundary.

### Operational agents

- **Crawler:** retrieves pages, treats content as untrusted, extracts
  quantitative claims, and collects candidate evidence links.
- **Verifier:** retrieves linked evidence under policy and checks whether the
  claimed quantity appears. Optional Claude-based semantic review is fenced,
  constrained, logged, and unable to rescue a source-free claim.
- **Prober:** issues bounded HTTP probes and compares results to thresholds.
- **Reporter:** writes Markdown whose findings cite audit sequence numbers.

### Orchestrator (`orchestrator.py`)

Runs crawl → verify → probe → report with one policy instance and one audit log.
Policy violations and retrieval failures become findings rather than hidden
exceptions.

## Evaluation subsystem

### Inputs

- `EvalCase`: expected and prohibited output, required and forbidden actions,
  evidence domains, latency/cost/action budgets, thresholds, and tags.
- `AgentRun`: output, completion state, action trace, evidence URLs, latency,
  cost, and system version.

Both are strict Pydantic contracts and are available as JSON Schemas under
`schemas/`.

### Metrics and gates

`evaluation.py` computes five normalized metrics. Safety violations are hard
failures. `evaluate_suite` retains missing cases as zero-score failures,
produces tag slices, and enforces suite thresholds. `compare_reports` pairs
baseline and candidate runs by `(case_id, run_id)` and blocks safety,
pass-to-fail, or excessive score regressions.

### Outputs

- Human-reviewable Markdown
- Complete machine-readable JSON
- Optional paired-comparison JSON
- SHA-256 fingerprints of the exact case and run files
- Process exit code suitable for CI

## Data flow

1. `Claim` — text, source page, candidate evidence URLs, audit sequence.
2. `Verification` — claim, verdict, rationale, decisive audit sequence.
3. `ProbeResult` — target, status, latency, health, audit sequence.
4. Operational report — Markdown citing verification and probe actions.
5. `EvalCase` + `AgentRun` — observable release assertions and captured run.
6. `RunEvaluation` — normalized metrics, hard failures, pass decision.
7. `SuiteReport` — aggregate score, slice analysis, gate decision, provenance.
8. `ComparisonReport` — paired deltas and promotion recommendation.

## Extension points

- Add action types through policy, executor registration, and target validation.
- Add operational controls through new agent subclasses and action names.
- Import OpenTelemetry traces into `AgentRun` records.
- Store longitudinal suite results in PostgreSQL or an analytics warehouse.
- Add calibrated human-review queues for open-ended semantic quality.
- Sign case bundles and reports for release provenance.
- Replace local audit storage with object lock or a transparency log.
