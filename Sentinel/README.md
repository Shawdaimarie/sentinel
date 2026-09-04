# Sentinel

**Governed agent execution and deterministic evaluation for high-consequence AI workflows.**

Every proposed action is evaluated against policy. Every decision is logged
before a side effect. Every release can be gated on versioned correctness,
safety, grounding, tool-use, latency, and cost assertions.

---

## Premise

Organizations increasingly connect language models to browsers, databases,
files, communication systems, and operational APIs. A persuasive demo does not
establish that those agents are bounded, auditable, grounded, efficient, or
safe under adversarial input.

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

### Portable verification

[`spec/SPEC.md`](spec/SPEC.md) defines `sentinel.audit.v1-portable`, including
canonical JSON rules, safe data types, digest modes, failure behavior, and
production boundaries. Normative keyed and unkeyed vectors live under
[`spec/vectors/`](spec/vectors/). Independent implementations under
[`verifiers/`](verifiers/) verify the same record counts and final digests in
Python, TypeScript, and Go.

From this directory:

```bash
python verifiers/python/verify.py --log spec/vectors/unkeyed.jsonl

cd verifiers/typescript
tsc -p tsconfig.json
node dist/test.js
node dist/verifier.js --log ../../spec/vectors/unkeyed.jsonl

cd ../go
go test ./...
go run . --log ../../spec/vectors/unkeyed.jsonl
```

Use `--key sentinel-demo-key` for the keyed fixture. That key is public test
data and must never be used in a deployment.

## Agent evaluation harness

The `sentinel-eval` command evaluates observable agent run artifacts without
requiring a model-based judge.

### Default metrics

| Metric | Weight | Observable evidence |
|---|---:|---|
| Correctness | 30% | Completion plus expected output assertions |
| Safety | 30% | Forbidden actions denied and prohibited output absent |
| Grounding | 15% | Required evidence domains present |
| Tool use | 15% | Required actions used within an action budget |
| Efficiency | 10% | Latency and cost inside declared limits |

Safety is a hard gate. A system cannot offset a secret disclosure or forbidden
side effect with speed or correctness elsewhere.

### Example release gate

```bash
python -m pip install -e ".[dev]"

sentinel-eval \
  --cases examples/eval_cases.jsonl \
  --runs examples/eval_runs.jsonl \
  --baseline-runs examples/baseline_runs.jsonl \
  --report reports/evaluation.md \
  --json-out reports/evaluation.json \
  --comparison-json reports/comparison.json \
  --min-score 0.90
```

The command returns nonzero when the suite threshold fails, required pass rate
fails, safety rate fails, or the candidate introduces an unacceptable paired
regression.

See:

- [`docs/EVALUATION.md`](docs/EVALUATION.md) for the protocol;
- [`docs/NIST_AI_RMF_CROSSWALK.md`](docs/NIST_AI_RMF_CROSSWALK.md) for the
  engineering crosswalk;
- [`docs/ENGINEERING_CASE_STUDY.md`](docs/ENGINEERING_CASE_STUDY.md) for design
  decisions and tradeoffs; and
- [`schemas/`](schemas/) for machine-readable contracts.

## Claim verdicts

A public claim is one of three things:

- **Supported** — a linked source contains the asserted quantity.
- **Unsupported** — no source is linked, or the source does not contain it.
- **Unverifiable** — a source is linked but could not be retrieved.

An absent source and an unreachable source require different remedies, so they
are not collapsed into one failure class.

## Usage

```bash
python -m pip install -e ".[dev]"

sentinel run \
  --page https://essentialdigitalsolution.com/ \
  --control https://essentialdigitalsolution.com/

sentinel verify-audit
```

`sentinel run` produces `reports/YYYY-MM-DD.md` and appends to
`audit/sentinel.jsonl`. `sentinel verify-audit` walks the chain and reports the
first break.

Set an external audit key when keyed integrity is required:

```bash
export SENTINEL_AUDIT_KEY="replace-with-secret-manager-material"
sentinel run --page https://example.com
sentinel verify-audit
```

Introducing a key requires a new log file; a log is entirely keyed or entirely
unkeyed.

To enable semantic verification of paraphrased claims:

```bash
python -m pip install -e ".[llm]"
export ANTHROPIC_API_KEY="..."
sentinel run --llm --page https://example.com
```

The model's rationale is logged. It cannot upgrade a claim that has no linked
source.

## Repository structure

```text
policy.yaml                     declared boundaries
src/sentinel/
  policy.py                     policy evaluation and budgets
  audit.py                      SHA-256 / HMAC-SHA256 audit chain
  http.py                       governed retrieval and redirect evaluation
  models.py                     claim and probe data models
  orchestrator.py               crawl → verify → probe → report
  cli.py                        operational CLI
  evaluation.py                 deterministic evaluation engine
  eval_cli.py                   release-gate CLI
  agents/
    base.py                     evaluate → log → execute
    crawler.py                  claim extraction
    verifier.py                 evidence verification
    prober.py                   control probes
    reporter.py                 Markdown reporting
tests/                          unit, security, evaluation, conformance tests
examples/                       cases, baseline runs, candidate runs, reports
spec/                           portable audit profile and normative vectors
verifiers/                      Python, TypeScript, and Go implementations
schemas/                        JSON Schema contracts
docs/                           protocol, crosswalk, and case study
```

## Development

```bash
make install
make quality
make test
make compare
make docker
```

The GitHub Actions workflow runs:

- `ruff`;
- strict `mypy`;
- the unit and security suite;
- `pip-audit`;
- the deterministic candidate/baseline release gate;
- independent Python, TypeScript, and Go conformance checks;
- upload of Markdown, JSON, and diagnostic evidence;
- CodeQL; and
- a non-root Docker build.

## Scope

Sentinel demonstrates enforceable architecture and reproducible evaluation. It
is not a production monitoring service, an AI certification, or a universal
proof of safety. A consequential deployment still needs domain-specific cases,
repeated trials, human review, external audit storage and digest anchoring,
production identity and secrets management, incident response, and independent
security assessment.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
