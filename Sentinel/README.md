# sentinel

**A governed multi-agent system for continuous verification of business claims and controls.**
Every action evaluated against policy. Every action logged. Every finding traceable to evidence.

[![ci](https://github.com/Shawdaimarie/sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/Shawdaimarie/sentinel/actions/workflows/ci.yml)

---

## Premise

Most organisations make public assertions no one can trace — uptime figures, latency numbers, client counts — and rely on controls that were validated once and never probed again. Sentinel is a working demonstration of the alternative: autonomous agents that crawl a public surface, test each quantitative claim against a linked source, probe critical controls on a schedule, and produce a report in which every line cites the logged action that produced it.

It is built for [Essential Digital Solution](https://essentialdigitalsolution.com), whose stated principle it implements: assertions trace to a source record; controls are probed continuously rather than validated once.

## Design

Four agents, one policy, one audit log.

| Agent | Role | Permitted actions |
|-------|------|-------------------|
| `crawler` | Retrieve pages; extract quantitative claims | `http.get` on the monitored domain |
| `verifier` | Test each claim against linked evidence | `http.get`, optional `llm.complete` |
| `prober` | Probe controls; compare to declared thresholds | `http.head`, `http.get` |
| `reporter` | Compile findings with audit citations | `fs.write` to `reports/` only |

Two properties hold for every agent, without exception:

1. **No unevaluated action.** An agent proposes an action; the policy engine decides; only then does execution occur. The default decision is deny. A denied action is logged with its reason and raises, so refusals are as visible as successes.
2. **No unlogged action.** Each decision is appended to a hash-chained log *before* execution. Editing, deleting, or reordering any record breaks the chain, which `sentinel verify-audit` detects. With a key present, the chain cannot be recomputed by an attacker who rewrites the file, and a keyed verifier refuses a log that has been downgraded to unkeyed.
3. **No unevaluated network hop.** Redirects are not followed automatically; each hop is a policy-evaluated action. Hosts resolving to private, loopback, or link-local addresses are refused. Responses are bounded in size and restricted to textual types.

Boundaries — permitted actions, permitted domains, per-run budgets, thresholds — are declared once, in [`policy.yaml`](policy.yaml). There is no code path around it.

## Verdicts

A claim is one of three things, and the distinction is deliberate:

- **Supported** — a linked source contains the asserted quantity.
- **Unsupported** — no source is linked, or the source does not contain it.
- **Unverifiable** — a source is linked but could not be retrieved.

An absent source and an unreachable one call for different remedies; collapsing them would hide which problem the organisation has.

## Usage

```bash
pip install -e ".[dev]"

sentinel run \
  --page https://essentialdigitalsolution.com/ \
  --control https://essentialdigitalsolution.com/

sentinel verify-audit
```

`run` produces `reports/YYYY-MM-DD.md` and appends to `audit/sentinel.jsonl`. `verify-audit` walks the chain and reports the first break, if any.

Set `SENTINEL_AUDIT_KEY` to authenticate the log with HMAC-SHA256; without it the chain is plain SHA-256 and `verify-audit` says so. A log is entirely keyed or entirely unkeyed; introducing a key means starting a new log file.

The log format is specified in [sentinel-spec](https://github.com/Shawdaimarie/sentinel-spec), so it can be verified without trusting this implementation: the same file yields the same verdict from the Python, TypeScript, and Go verifiers there. Pin the policy with `--policy-sha256 <digest>` to refuse a run under any policy other than the one reviewed.

To enable semantic verification for paraphrased claims, install the optional dependency and set `ANTHROPIC_API_KEY`:

```bash
pip install -e ".[llm]"
sentinel run --llm --page https://essentialdigitalsolution.com/
```

The model's rationale is logged alongside its verdict. It never overrides an absent source.

## Repository

```
policy.yaml                  Declared boundaries — the only place they are decided
src/sentinel/
  policy.py                  Policy engine: evaluate, record, deny by default
  audit.py                   Append-only, hash-chained log (format: sentinel-spec)
  models.py                  Claim, Verification, ProbeResult
  orchestrator.py            Runs the agents in sequence on one policy and one log
  cli.py                     `sentinel run`, `sentinel verify-audit`
  http.py                    Governed retrieval: per-hop evaluation, size and type limits
  agents/
    base.py                  Agent.act — evaluate, log, then execute
    crawler.py  verifier.py  prober.py  reporter.py
tests/                       Policy boundaries, chain integrity, agent behaviour,
                             and one test per control named in SECURITY.md
ARCHITECTURE.md              Component design and data flow
SECURITY.md                  Objectives, adversary model, STRIDE analysis, residual risk
```

## Development

```bash
ruff check src tests && mypy src && pytest
```

CI runs these, `pip-audit`, and CodeQL on Python 3.11 and 3.12. `mypy` is configured strict. A separate job in [sentinel-spec](https://github.com/Shawdaimarie/sentinel-spec) installs this repository from `main` and asserts its digests match the conformance vectors.

## Scope

This is a reference implementation. It demonstrates that governance can be enforced structurally — in the shape of the code — rather than by convention. It is not, as shipped, a production monitoring service; see [SECURITY.md](SECURITY.md) for what would need to change.

## License

Apache-2.0. See [LICENSE](LICENSE).
