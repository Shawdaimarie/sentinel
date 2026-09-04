# Sentinel

**Governed agent execution, deterministic evaluation, benefit-gated automation, and value routing for high-consequence AI workflows.**

Every proposed action is evaluated against policy. Every decision is logged
before a side effect. Every release can be gated on versioned correctness,
safety, grounding, tool-use, latency, and cost assertions. Every value-bearing
work item can be routed through evidence, security, deployability, and ownership
clarity before it is presented externally or scaled.

---

## Premise

Organizations increasingly connect language models to browsers, databases,
files, communication systems, and operational APIs. A persuasive demo does not
establish that those agents are bounded, auditable, grounded, efficient, safe
under adversarial input, or worth scaling.

Sentinel is a working reference implementation of a stricter pattern:

1. **Govern execution.** Agents cannot bypass declarative policy.
2. **Record decisions.** Allowed and denied actions are written to a
   tamper-evident log before execution.
3. **Treat external content as untrusted.** Every network hop is evaluated.
4. **Measure observable behavior.** Versioned cases score outputs, tool traces,
   evidence, latency, cost, and action budgets.
5. **Block regressions.** Safety failures and unacceptable paired regressions
   fail the release gate.
6. **Verify independently.** A portable profile and normative vectors are
   implemented separately in Python, TypeScript, and Go.
7. **Route value.** Public proof, private delivery, and human-only decisions are
   separated before work is reused, automated, or distributed.

## Architecture

```text
                         policy.yaml
                              │
                              ▼
                   deny-by-default policy
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
          crawler          verifier          prober
              └───────────────┬────────────────┘
                              ▼
                           reporter
                              │
                  Markdown findings + audit refs

 every Agent.act() ──> evaluate ──> append audit decision ──> execute or deny

 versioned eval cases ─┐
                       ├─> deterministic evaluator ─> release gate
 captured agent runs ──┘                  │
                                  Markdown + JSON + hashes

 portable spec + vectors ──> Python verifier
                         ├─> TypeScript verifier ──> identical final digest
                         └─> Go verifier

 code-agent response ──> rubric dimensions ──> score + decision label

 work item ──> value route gateway ──> deployable / pilot / review / hold / reject
```

Detailed component design is in [`ARCHITECTURE.md`](ARCHITECTURE.md). Security
objectives, threat analysis, controls, and residual risk are in
[`SECURITY.md`](SECURITY.md).

## Governed agents

| Agent | Role | Permitted actions |
|---|---|---|
| `crawler` | Retrieve pages and extract quantitative claims | `http.get` on declared domains |
| `verifier` | Test claims against linked evidence | `http.get`, optional `llm.complete` |
| `prober` | Probe controls and thresholds | `http.head`, `http.get` |
| `reporter` | Compile findings with audit citations | `fs.write` under `reports/` |

Three invariants apply:

1. **No unevaluated action.** The default policy decision is deny.
2. **No unlogged decision.** The audit record is appended before dispatch.
3. **No unevaluated network hop.** Redirects are followed manually and each
   destination is re-submitted to policy.

## Audit integrity

The audit log is append-only JSON Lines. Each record carries the digest of the
previous record and a digest of its own canonical content:

- SHA-256 when no key is configured;
- HMAC-SHA256 when `SENTINEL_AUDIT_KEY` is present; and
- explicit rejection of keyed-to-unkeyed downgrade during verification.

The chain detects modification, deletion in the middle, reordering, sequence
gaps, and keyed downgrade. It does not by itself detect deletion of the entire
file or truncation of the tail; production deployments must stream records to
external append-only storage.

## Agent evaluation harness

The `sentinel-eval` command evaluates observable agent run artifacts without
requiring a model-based judge.

| Metric | Weight | Observable evidence |
|---|---:|---|
| Correctness | 30% | Completion plus expected output assertions |
| Safety | 30% | Forbidden actions denied and prohibited output absent |
| Grounding | 15% | Required evidence domains present |
| Tool use | 15% | Required actions used within an action budget |
| Efficiency | 10% | Latency and cost inside declared limits |

Safety is a hard gate. A system cannot offset a secret disclosure or forbidden
side effect with speed or correctness elsewhere.

```bash
sentinel-eval \
  --cases examples/eval_cases.jsonl \
  --runs examples/eval_runs.jsonl \
  --baseline-runs examples/baseline_runs.jsonl \
  --report reports/evaluation.md \
  --json-out reports/evaluation.json \
  --comparison-json reports/comparison.json \
  --min-score 0.90
```

## Coding-agent review scorer

`sentinel-code-review` converts human rubric dimensions into deterministic
accept, accept-with-edits, needs-human-design, or reject decisions. It is meant
for AI-generated code review, coding-agent calibration, and model-evaluation
work where fluency is not enough.

Review dimensions:

- requirement fit;
- correctness;
- security;
- maintainability;
- verification; and
- communication.

Security remains a hard gate. A superficially high score cannot rescue an
unsafe answer that exposes secrets, bypasses authorization, runs destructive
commands, or introduces uncontrolled side effects.

## Value Route Gateway

`sentinel-value-router` connects engineering proof to deployable value. It routes
work items through five checks:

1. value;
2. evidence;
3. security;
4. deployment readiness; and
5. ownership and reuse clarity.

The router returns one of five lanes:

| Lane | Meaning |
|---|---|
| Deployable | Strong enough to present or reuse as professional proof. |
| Pilot | Useful enough for bounded testing before durable reuse. |
| Human review | Valuable but blocked by a human-only or approval-sensitive boundary. |
| Reserved hold | Potentially valuable but not clear enough for public distribution. |
| Reject | A hard blocker exists, usually security or sensitive-data exposure. |

```bash
sentinel-value-router \
  --items examples/value_route_items.json \
  --json-out reports/value-route/value_routes.json \
  --markdown-out reports/value-route/value_routes.md \
  --min-score 0.70
```

See:

- [`docs/VALUE_ROUTE_GATEWAY.md`](docs/VALUE_ROUTE_GATEWAY.md) for the routing
  method;
- [`docs/OWNERSHIP_AND_PUBLIC_PROOF_BOUNDARY.md`](docs/OWNERSHIP_AND_PUBLIC_PROOF_BOUNDARY.md)
  for the separation between public proof and private work;
- [`docs/TRUST_AND_COMMUNICATION_STANDARD.md`](docs/TRUST_AND_COMMUNICATION_STANDARD.md)
  for the safest-yes communication standard;
- [`docs/CODING_AGENT_REVIEW_RUBRIC.md`](docs/CODING_AGENT_REVIEW_RUBRIC.md)
  for the coding-agent review protocol; and
- [`docs/AUTOMATION.md`](docs/AUTOMATION.md) for benefit-gated automation.

## Automation and workflows

Sentinel includes scheduled and manually dispatchable workflows for:

- quality and deterministic evaluation;
- portable audit conformance;
- trace import;
- CodeQL;
- non-root container build;
- benefit-gated stability automation; and
- value-route report generation.

These workflows preserve a reviewer-visible trail of proof while keeping
identity, legal, financial, account, and assessment work human-controlled.

## Repository structure

```text
policy.yaml                     declared boundaries
src/sentinel/
  policy.py                     policy evaluation and budgets
  audit.py                      SHA-256 / HMAC-SHA256 audit chain
  http.py                       governed retrieval and redirect evaluation
  evaluation.py                 deterministic evaluation engine
  code_review.py                deterministic coding-agent review scorer
  trust_readiness.py            safest-yes decision scoring
  automation.py                 benefit-gated stability task runner
  value_router.py               deployable value routing gateway
  *_cli.py                      command-line interfaces
tests/                          unit, security, evaluation, conformance tests
examples/                       cases, baseline runs, candidate runs, route items
spec/                           portable audit profile and normative vectors
verifiers/                      Python, TypeScript, and Go implementations
schemas/                        JSON Schema contracts
docs/                           protocol, crosswalk, trust, automation, routing
```

## Development

```bash
make install
make quality
make test
make compare
make automation
make docker
```

## Scope

Sentinel demonstrates enforceable architecture, reproducible evaluation, trust
communication, benefit-gated automation, and deployable value routing. It is not
a production monitoring service, an AI certification, a legal opinion, or a
universal proof of safety. A consequential deployment still needs domain-specific
cases, repeated trials, human review, external audit storage and digest
anchoring, production identity and secrets management, incident response, and
independent security assessment.

## License

Apache-2.0. See [`LICENSE`](LICENSE). See
[`docs/OWNERSHIP_AND_PUBLIC_PROOF_BOUNDARY.md`](docs/OWNERSHIP_AND_PUBLIC_PROOF_BOUNDARY.md)
for the separation between repository license, public attribution, and private
commercial or identity-sensitive materials.
