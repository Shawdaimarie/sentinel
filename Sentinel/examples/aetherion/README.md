# Aetherion Technologies — fictional engineering workflow

**FICTIONAL COMPANY · SYNTHETIC DATA · NOT A PRODUCTION DEPLOYMENT**

Aetherion Technologies is an invented software engineering company used to
demonstrate how Sentinel might govern AI coding agents modifying backend APIs,
database operations, and deployment pipelines.

The runner actually uses Sentinel policy, hash-chained audit logging and its
evaluation engine against **inert synthetic actions**. It does not call external
tools, execute real tests, access a database, run an AI model, or deploy software.
In generated evaluation records, action status "executed" means simulated
execution for a test fixture. Zero latency and cost values are placeholders,
not measurements.

## Workflow

1. A coding agent proposes source reads, test runs and an unauthorized database
   write. Policy checks permit the read/tests and deny the write.
2. A read-only migration review allows a staging query but denies schema writes.
3. A release agent asks for human approval, while production promotion is denied.
4. Sentinel appends each decision to a SHA-256 hash chain and verifies it.
5. Deterministic cases check correct output and hard-fail if a prohibited action
   is observed as anything other than denied.
6. A paired *identical* synthetic baseline exercises the regression engine. It
   demonstrates gate mechanics only, not an improvement in real performance.
7. An additional OTLP JSON fixture demonstrates trace import, redaction/manifest
   generation, and evaluation.
8. The Aegis Go policy fixture covers workload-specific tool scopes and a
   staging-promotion rule marked require_approval=true. Its policy matcher is not
   a real signed-token or human-approval integration.

## Run the simulated policy and audit workflow

From repository root:

~~~bash
cd Sentinel
python -m pip install -e ".[dev]"
python examples/aetherion/run_demo.py --output-dir reports/aetherion-demo-1
~~~

Use a fresh output directory for every run: the runner refuses to overwrite
existing evidence. Review audit.jsonl, candidate_runs.jsonl, evaluation.md,
evaluation.json and comparison.json inside that output directory.

## Normalize and evaluate the synthetic OpenTelemetry trace

From the Sentinel directory:

~~~bash
sentinel-import-otel \
  --input examples/aetherion/otel_trace.json \
  --output reports/aetherion-otel-runs.jsonl \
  --manifest reports/aetherion-otel-manifest.json

sentinel-eval \
  --cases examples/aetherion/otel_case.jsonl \
  --runs reports/aetherion-otel-runs.jsonl \
  --report reports/aetherion-otel-evaluation.md \
  --json-out reports/aetherion-otel-evaluation.json
~~~

These fixture traces are not from a live collector. The provenance manifest
fingerprints the submitted example data and importer configuration.

## Evaluate the Aegis Go policy

From the Aegis directory:

~~~bash
go run ./cmd/aegis-policy-eval \
  --policy ../Sentinel/examples/aetherion/aegis_policy.json \
  --cases ../Sentinel/examples/aetherion/aegis_cases.json
~~~

An "allow" result for staging promotion establishes only a *policy match*;
Aegis's actual runtime would still require a valid signed capability,
separately signed human approval, trusted issuer, persistent replay state and
secure logging. This example intentionally does not authorize deployments.

## Run the tests

From the Sentinel directory:

~~~bash
pytest -q tests/test_aetherion_demo.py
~~~

The tests cover the generated workflow, audit verification, intentional audit
tampering, forbidden-action hard failures, and OTLP import/evaluation.

## Boundaries before real adoption

The fictional demonstration is not an identity provider, deployment adapter,
monitoring service or production inference system. Real adoption would require
live tool adapters, trusted identity integration, secure signed approvals,
durable replay/revocation state, externally anchored audit evidence, collector
integration, representative benchmarks, infrastructure monitoring and
independent security review.

**Do not cite Aetherion as a real employer, customer, project deployment, or
confirmed production use in job applications.**
