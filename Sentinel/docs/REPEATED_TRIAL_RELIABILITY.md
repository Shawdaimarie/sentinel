# Repeated trial reliability assessment

The first implementation adds an offline assessment around the existing
deterministic evaluator. It validates a predeclared case/trial grid, verifies
input SHA-256 fingerprints, preserves hard failures, and reports uncertainty
without counting repeated runs of one case as independent cases.

This is an initial milestone implementation. It does not collect live traces,
train models, calibrate probabilities, independently verify sampling claims,
or authorize business actions.

## Run the example

From `Sentinel/`, install the package and run:

```bash
python -m pip install -e ".[dev]"
sentinel-reliability \
  --manifest examples/reliability_assessment/repeated_trials/manifest.json \
  --cases examples/reliability_assessment/repeated_trials/cases.jsonl \
  --runs examples/reliability_assessment/repeated_trials/runs.jsonl \
  --output-dir reports/repeated-trials
```

The command returns **3**, meaning **inconclusive**, despite all nine synthetic
observations passing deterministic assertions. The report identifies the
synthetic evidence, undeclared independent sampling, and insufficient number
of cases. Do not change those declarations to manufacture a passing example.

Outputs are `reliability.json` and `reliability.md`. The output directory must
not already exist. Each input is limited to 10 MiB. Invalid JSON, duplicate
keys, non-finite values, undeclared trials, duplicate observations, unexpected
systems, and digest mismatches are rejected. The command performs no model
calls or network actions.

| Exit code | Meaning |
| --- | --- |
| 0 | Declared reliability prerequisites and existing deterministic gates pass |
| 1 | An observed hard failure, deterministic gate failure, paired regression, or statistical failure blocks promotion |
| 2 | Invalid input or output-writing error; do not use partial output as accepted evidence |
| 3 | Insufficient evidence; promotion is not recommended |

## Versioned contracts

The [manifest schema](../schemas/reliability-manifest-v1.schema.json) declares
case IDs, at least two expected trial IDs per case, candidate/baseline identity,
artifact hashes, sampling scope, evidence type, source commit, model/prompt/tool/
runtime versions, confidence level, target pass rate, minimum cases, and
existing evaluation configuration. Use explicit `unavailable` provenance values
when a provider does not expose a version; such a value does not prove replayability.

Freeze the manifest and cases before collecting observations. Populate the
artifact digests after capture and retain a separately timestamped design record
when independently proving preregistration matters. A hash alone does not prove
when a design was chosen or whether cases were selected without bias.

The [report schema](../schemas/reliability-assessment-v1.schema.json) preserves
the manifest, exact input hashes, deterministic results, individual missing
trial IDs, observed case pass rates, decision reasons, and optional bounds.
No database schema or existing `AgentRun` contract changes are required.

Stored inputs replay to byte-identical JSON under the same implementation and
environment. Nested evaluation reports use `replayed-from-hashed-inputs` in
their generated-at field; this is deliberately not a new observation timestamp.
Record capture timestamps in the source evidence. Raw model calls are not
claimed to be deterministic.

## Statistical method and assumptions

For each case, calculate the fraction of its declared trials that pass. The
overall estimand is the equal-weight mean of these case pass rates, not the
run-weighted mean and not a traffic-weighted success probability. A fixed,
complete grid is required. Missing observations remain unknown; they are not
discarded to improve the result.

The first implementation uses a conservative two-sided Hoeffding interval:

```text
radius = (upper_support - lower_support) * sqrt(log(2 / alpha) / (2 * case_count))
interval = [mean - radius, mean + radius], clipped to the known support
```

For pass rates, support is `[0, 1]`. Repeated trials within a case may be
dependent; the independent units are the sampled cases. For population claims,
cases must represent the declared population, and case clusters must be
independent, including their execution conditions. Shared outages or shared
session state can invalidate that assumption. Fixed handpicked cases do not
establish population reliability simply because the independence flag is set.

The method does not require a normal approximation or nonzero observed
variance. Identical successes still produce a nonzero uncertainty radius.
With 200 independent cases all having pass rate 1, the 95% lower bound is
approximately 0.903968. With 20 such cases, adding more identical repetitions
does not narrow the case-level bound.

This follows the bounded independent-variable inequality in
[Hoeffding, 1963](https://www.tandfonline.com/doi/abs/10.1080/01621459.1963.10500830).
It is intentionally conservative. It is not the independent Bernoulli
zero-failure bound illustrated in the research blueprint. The units and
assumptions differ.

Bounds are withheld if the grid is incomplete, evidence is synthetic,
independent sampling is not declared, or minimum case count is unmet. When
available, a lower bound at or above the declared target clears the statistical
gate; an upper bound below the target fails it; an overlapping interval is
inconclusive. Hard failures take precedence even when evidence is incomplete.

## Baseline comparisons

Declare baseline identity and digest together and supply `--baseline-runs`.
Both systems must contain the entire same case/trial grid. Partial overlap
never produces a comparison of just the available successful subset.

The existing paired score and pass-to-fail regression rules remain in force.
The new report also contains a case-level interval for the candidate-minus-
baseline pass-rate delta, with support `[-1, 1]`. When two bounds are reported,
Bonferroni allocation uses half the requested error budget for each, giving
joint coverage at least the declared confidence level under the assumptions.

The delta interval is descriptive inferential evidence, not a statistical
noninferiority gate. A reliability pass does not claim superiority to baseline.
No optional stopping, adaptive confidence sequences, subgroup inference,
probability calibration, or multiple-candidate selection correction is included.
Choose a fixed sample design; repeated looks and cherry-picked candidate
selection require a separate statistical protocol.

## Verification and remaining work

Tests cover known-answer interval endpoints, within-case repetition, sufficient
and insufficient evidence, missing entire cases and individual trials, empty
observations, hard failures under permissive weights, exact baseline pairing,
tampering, strict input validation, deterministic replay, CLI exit behavior,
output preservation, and schema drift.

Next work: independent review of case construction and sampling; operational
shadow-mode evidence; perturbation and grader-integrity suites; probability
calibration; history integration; and measured performance of this new path.
The existing offline capacity benchmark does not measure this new command.
