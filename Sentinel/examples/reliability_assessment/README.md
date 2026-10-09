# Offline reliability assessment demonstration

Run 20 labeled synthetic traces through Sentinel's existing trace importer and
evaluation engine. The report makes missing evidence, retry behavior, forbidden
actions, and incorrect results visible before a release decision.

This demonstration uses no model, customer data, API credentials, or network
calls. Installation requires Python 3.11+ and the package dependencies.

## Run from a clean checkout

From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install ./Sentinel
sentinel-assess \
  --suite Sentinel/examples/reliability_assessment/suite.json \
  --output-dir reports/assessment-demo
```

Expected summary: `Synthetic fixture conformance: 20/20`, exit status `0`.
Read `reports/assessment-demo/assessment.md` first, then inspect
`assessment.json` for per-case evaluation details and import manifests.
Choose a new output directory for each run; existing evidence is never replaced.
With dependencies already installed, this equivalent invocation works from
the `Sentinel` directory:

```bash
PYTHONPATH=src python -m sentinel.assessment_cli \
  --suite examples/reliability_assessment/suite.json \
  --output-dir reports/assessment-demo
```

Exit codes: `0` means every observed outcome and evidence assertion matched its
label; `1` means at least one mismatch; `2` means invalid input or an I/O error.
Unexpected exceptions remain errors; they are not counted as successful rejection.

## Run the published container

Use a checkout of the source commit recorded by the release so that code and
fixtures match. From the repository root, verify `sentinel-eval:edge` with
`scripts/verify-image.sh` as described in [RELEASING.md](../../../RELEASING.md).
Set `SENTINEL_IMAGE` to the verified `ghcr.io/shawdaimarie/sentinel-eval@sha256:...`
reference printed by that script. These Linux containers currently target
`linux/amd64`; other hosts need a compatible engine or emulation.

```bash
mkdir -p reports
docker run --rm --platform linux/amd64 --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$PWD/Sentinel/examples/reliability_assessment/suite.json,dst=/suite.json,readonly" \
  --mount "type=bind,src=$PWD/reports,dst=/evidence" \
  --entrypoint sentinel-assess "$SENTINEL_IMAGE" \
  --suite /suite.json --output-dir /evidence/assessment-demo
```

Run this from a non-root Linux or macOS account. Choose a new output directory
each time. The suite is read-only, network access is disabled, and only the
reports folder is writable. Windows users can use the Python instructions above
or adapt mounts and permissions for their Docker setup. A successful release
runs this packaged assessment before publication and after pulling its verified
digest. That is a bounded smoke check, not a customer acceptance test.

## What the 20 cases establish

| Category | Five cases |
|---|---|
| Completeness | Complete trace; missing root end; missing output; missing parent; empty export |
| Retries | Single success; recovery after failure; shuffled export; derived attempts; exceeded action budget |
| Authorization observations | Forbidden action denied, executed, proposed, or failed; recorded approval cannot override a prohibition |
| Evaluation | Wrong output; prohibited disclosure; missing evidence domain; latency budget exceeded; root error despite good output |

The expected distribution is **6 pass, 13 fail, 1 reject**. All 20 matching
their labels is a successful demonstration. It does not mean all 20 agent runs
are safe or successful. Incomplete or errored runs fail independently of their
weighted score. Completion failures remain distinct from safety violations.

## Provenance and label policy

`suite.json` is a versioned, hand-authored synthetic dataset. It uses the
importer's simplified OTLP-compatible `spans` shape and synthetic identifiers.
The `.invalid` URLs are inert examples; no URL is fetched. The prohibited secret
marker is fictional. No production records or personal data were used.

Each case declares its task, rationale, category, evaluation expectations,
expected outcome, diagnostic fragments, missing telemetry fields, and exact
ordered actions and attempts. Expected outcomes are compared only after the
importer and evaluator run. A failure for an unrelated reason does not satisfy
the required diagnostic evidence. Retry and latency budget examples explicitly
set a 0.99 case threshold because those dimensions otherwise contribute soft
weighted scores.

The report fingerprints the exact suite bytes, canonical per-case trace bytes,
evaluation configuration, and assessment/importer/evaluator source. It omits
wall-clock generation time so unchanged inputs and implementation yield stable
JSON. Compare reports only after inspecting these fingerprints and changes in
case definitions. Review label changes as carefully as code changes.

This is a development conformance set, not a held-out benchmark. Independent
review and new, customer-approved cases are necessary before drawing broader
conclusions. A future held-out set must be separate from tuning fixtures.

## Limits and next decisions

- Recorded approval events do not prove identity, consent, scope, expiry, or
  permission to execute. These examples test observable action-policy outcomes,
  not a live authorization service.
- The importer cannot prove that an export includes every action. It detects
  supported completeness gaps, not arbitrary omitted child spans.
- Output and source-domain assertions are deterministic proxies, not semantic
  truth or fairness judgments. Synthetic latency and cost are not measured
  production performance or actual spending.
- Redaction remains limited by the [trace import protocol](../../docs/TRACE_IMPORT.md).
  The harness is intended for synthetic data and is not a data-loss-prevention
  boundary. Review report contents before sharing.
- This command makes no deployment or release decision on the user's behalf.

For a customer engagement, start with the
[fixed-scope assessment proposal](../../docs/RELIABILITY_ASSESSMENT_OFFER.md).
