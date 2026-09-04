# Sentinel

**Governed agent execution and deterministic evaluation for high-consequence AI workflows.**

[![CI](https://github.com/Shawdaimarie/sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/Shawdaimarie/sentinel/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Sentinel is a reference implementation for teams that need AI agents to be
**observable, bounded, testable, and reviewable** before they affect business
systems. It combines a deny-by-default policy engine, pre-execution audit
logging, governed network access, a deterministic evaluation harness, and a
portable audit-chain specification independently verified in Python,
TypeScript, and Go.

The implementation lives in [`Sentinel/`](Sentinel/).

## Engineering signal

| Capability | Concrete evidence |
|---|---|
| Agent governance | Every action is evaluated against declarative policy before dispatch |
| Audit integrity | Append-only SHA-256 or HMAC-SHA256 chain with downgrade detection |
| Portable verification | Language-neutral profile, normative vectors, and independent Python, TypeScript, and Go verifiers |
| Network containment | Every redirect hop is re-evaluated; private and non-HTTP targets are denied |
| Evaluation engineering | Versioned JSONL cases, deterministic scoring, slice analysis, and hard safety gates |
| Release discipline | Paired baseline comparison and CI failure on unacceptable regressions |
| Software quality | Strict types, unit/security tests, dependency audit, CodeQL, and a non-root container build |
| Reproducibility | Input SHA-256 fingerprints, machine-readable reports, and cross-language digest agreement |

## Quick start

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

Verify the portable audit vectors without trusting the main package:

```bash
python verifiers/python/verify.py --log spec/vectors/unkeyed.jsonl

cd verifiers/typescript
tsc -p tsconfig.json
node dist/verifier.js --log ../../spec/vectors/unkeyed.jsonl

cd ../go
go run . --log ../../spec/vectors/unkeyed.jsonl
```

Or run the evaluation gate in a container:

```bash
docker build -t sentinel-eval Sentinel
docker run --rm \
  -v "$PWD/Sentinel/examples:/workspace/examples:ro" \
  -v "$PWD/Sentinel/reports:/workspace/reports" \
  sentinel-eval \
  --cases examples/eval_cases.jsonl \
  --runs examples/eval_runs.jsonl \
  --report reports/evaluation.md \
  --json-out reports/evaluation.json
```

## Why this repository exists

Reliable AI deployment is not just a model-selection problem. It is a systems
problem involving permissions, evidence, failure behavior, cost boundaries,
human approval, regression detection, and an audit trail that survives review.
Sentinel treats those properties as executable engineering constraints.

The project is informed by the [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework),
the [NIST Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence),
and the [OWASP AI Agent Security guidance](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html).
See the [`NIST AI RMF crosswalk`](Sentinel/docs/NIST_AI_RMF_CROSSWALK.md) for the
project's concrete mapping.

## Repository map

```text
Sentinel/
  src/sentinel/              governed agents, policy, audit, HTTP, evaluation
  tests/                     unit, security, evaluation, and conformance tests
  examples/                  versioned cases, candidate runs, baseline runs
  spec/                      portable audit-chain profile and normative vectors
  verifiers/                 independent Python, TypeScript, and Go verifiers
  schemas/                   generated JSON contracts
  docs/                      architecture, evaluation protocol, case study
  Dockerfile                 non-root runtime image
.github/workflows/ci.yml      quality, security, evaluation, polyglot, container gates
```

## Scope

Sentinel is a reference implementation, not a certification and not a claim
that an AI system is universally safe. The evaluation harness measures only the
observable assertions encoded in its versioned cases. A portable hash chain
makes alteration of retained records detectable; it does not establish that a
log is complete. Consequential deployment requires domain-specific cases,
repeated trials, human review, external digest anchoring, operational
monitoring, and independent security assessment.
