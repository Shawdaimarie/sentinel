# Architecture

## Components

```
                       ┌──────────────┐
                       │ policy.yaml  │
                       └──────┬───────┘
                              │ load
                              ▼
   pages ──► crawler ──► verifier ──┐        ┌──────────┐
                                    ├──► reporter ──► reports/YYYY-MM-DD.md
   controls ──► prober ─────────────┘        └──────────┘
        │           │          │                  │
        └───────────┴──────────┴──────────────────┘
                      every act() ──► audit/sentinel.jsonl (hash chain)
```

### Policy engine (`policy.py`)

Loads a declarative document and answers one question: may *this agent* perform *this action* on *this target*, now? Evaluation checks, in order: the agent is declared; the action is in its allowed set; its per-run budget is not exhausted; for HTTP actions, the target host is the declared domain or a subdomain of it; for filesystem actions, the path is under an allowed prefix and contains no traversal. Any failure returns a denial with a stated reason. Nothing is allowed by omission.

The engine holds per-run counters, so one instance is created per orchestrator run and shared across agents. Denied actions do not consume budget.

### Audit log (`audit.py`)

Append-only JSON Lines. Each record carries the digest of the previous record and its own digest over all other fields — SHA-256 when unkeyed, HMAC-SHA256 when `SENTINEL_AUDIT_KEY` is set. `verify()` walks the file and raises on the first sequence gap, chain break, keyed-to-unkeyed downgrade, or content mismatch, in that order. The log reopens cleanly: a new process continues the chain from the last record.

The record format, canonical serialisation, and verification order are specified in [sentinel-spec](https://github.com/Shawdaimarie/sentinel-spec), which also ships conformance vectors and independent verifiers in three languages. `audit.py` is one implementation of that specification, not its definition.

This makes tampering *detectable*, not *impossible*, and truncation of the tail is not detectable by the chain alone. See SECURITY.md.

### Agent base (`agents/base.py`)

`Agent.act(action, target, **payload)` is the only way an agent produces an effect. It evaluates, appends the decision to the log, and — only if allowed — dispatches to an executor registered for that action name. The ordering is the point: the log entry exists before the side effect, so a crash mid-execution leaves evidence of the attempt.

### Governed retrieval (`http.py`)

The crawler and verifier fetch through `governed_get`, which submits every redirect hop to `Agent.act` so the policy engine sees the new location. Bodies are capped at 2 MiB and must be a textual content type. This is where the network trust boundary is enforced; see SECURITY.md §3.

### Agents

- **Crawler.** Fetches a page, strips script and style, treats block-level elements as sentence boundaries, and keeps sentences that assert a quantity. Collects every outbound link as candidate evidence. Extraction favours recall; the verifier is responsible for precision.
- **Verifier.** For each claim, retrieves each evidence link (within policy) and checks whether the asserted quantity appears verbatim. Optionally asks Claude whether the source supports a paraphrased claim; the model's rationale is logged, and it cannot rescue a claim with no source.
- **Prober.** Issues a HEAD request, measures wall-clock latency, and compares status and latency to thresholds declared in policy.
- **Reporter.** Renders Markdown. Every claim row and control row includes the audit sequence number of the action that produced it.

### Orchestrator (`orchestrator.py`)

Runs crawl → verify → probe → report on one policy instance and one log. Policy violations and retrieval failures are collected as findings and surfaced in the report, not raised — a page that fails to load is information, not an exception.

## Data flow

1. `Claim` — text, source page, candidate evidence URLs, audit sequence of the fetch.
2. `Verification` — the claim, a verdict, a rationale, and the audit sequence of the decisive action.
3. `ProbeResult` — target, observed status and latency, healthy flag, audit sequence.
4. Report — a Markdown document citing 2 and 3 by sequence.

## Extension points

- **New action types.** Add the name to an agent's `allowed_actions` in policy, register an executor, and add a branch in `Policy.evaluate` if the action needs target validation.
- **New controls.** The prober is HTTP-only. A DNS, TLS-expiry, or dependency-version prober follows the same pattern: a new `Agent` subclass, a new action name, a new policy entry.
- **External audit storage.** `AuditLog` writes to a local file. Replacing the sink with an append-only object store or a transparency log is a one-class change; `sentinel-ledger` is the planned implementation.
- **Independent verification.** Any verifier that passes the sentinel-spec vectors can check this log. Deployments that do not want to trust the writing host's Python can verify with the Go or TypeScript implementation.
