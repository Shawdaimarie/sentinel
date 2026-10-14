# Reproduce the offline evaluation capacity test

Use this procedure to measure the local `sentinel-eval` command against the
[criteria merged before measurement](PERFORMANCE_ACCEPTANCE.md). It tests saved
synthetic traces, with no model calls or paid hosting. It does not test the
optional PostgreSQL history service, Aegis, a web API, or customer traffic.

The runner requires macOS or Linux for per-process resource accounting and a
Python 3.12 installation. Use an otherwise idle machine for comparable numbers;
the first recorded experiment used an uncontrolled desktop and is not a stable
hardware benchmark. Do not run load tests against an operational service.

## Install the exact source

From a clone of this repository containing the runner, choose the previously
merged criteria and package source. The first protocol version uses the same
commit for both:

```bash
git fetch origin main
CRITERIA_COMMIT=f9793cdd34ca7f7782abb3f699b42b0e04ab3f9e
PACKAGE_COMMIT=f9793cdd34ca7f7782abb3f699b42b0e04ab3f9e
git worktree add --detach ../sentinel-capacity-source "$PACKAGE_COMMIT"
python3.12 -m venv ../capacity-builder
python3.12 -m venv ../capacity-runtime
../capacity-builder/bin/python -m pip install --require-hashes --only-binary=:all: \
  -r ../sentinel-capacity-source/Sentinel/requirements-build.txt
../capacity-builder/bin/python -m pip wheel --no-deps --no-build-isolation \
  --wheel-dir ../capacity-wheels ../sentinel-capacity-source/Sentinel
../capacity-runtime/bin/python -m pip install --require-hashes --only-binary=:all: \
  -r ../sentinel-capacity-source/Sentinel/requirements-runtime.txt
../capacity-runtime/bin/python -m pip install --no-index --no-deps \
  ../capacity-wheels/sentinel-0.6.0-py3-none-any.whl
../capacity-runtime/bin/python -m pip check
```

Use new directories if those paths already exist. Package wheel hashes can vary
with build metadata; the runner records the supplied wheel hash, verifies its
package files byte for byte against the selected source commit, and checks that
the runtime was installed from that wheel. An editable installation is rejected.
The original experiment's recorded builder versions are in its evidence; these
commands use the repository's hashed build requirements for subsequent runs.

## Run once and inspect failures

```bash
../capacity-runtime/bin/python scripts/benchmark-offline-eval.py \
  --repo . \
  --python ../capacity-runtime/bin/python \
  --wheel ../capacity-wheels/sentinel-0.6.0-py3-none-any.whl \
  --criteria-commit "$CRITERIA_COMMIT" \
  --package-commit "$PACKAGE_COMMIT" \
  --output ../capacity-results-01
```

The output directory must not already exist. The normal experiment takes about
eight minutes, with a 900-second acceptance budget and a ten-second
deadline for each evaluator process. It covers one and two workers, a five-minute
two-worker soak, increasing load up to eight workers, and missing/malformed
input files followed by valid recovery batches. The runner stops increasing load
after a failing level. A stopped or incomplete run never qualifies as passing.

Read `summary.json` for PASS, FAIL or INCOMPLETE and each stage's failed criteria.
Exit 0 means the overall protocol passed; exit 1 means it did not. Setup failures
can exit before an evidence directory is created. `operations.jsonl` records
every measured operation, including deliberate failures, with its timing,
resource use, validation result and report hash. Three warm-ups are recorded but
excluded from capacity summaries. Keep the generated inputs, criteria snapshot,
source identifiers, wheel hash and runner hash with the report.

The runner keeps one validated report pair per stage and all deliberately failed
or incorrect report pairs. Other passing report files are removed after
validation to bound disk use; their hashes and measurements remain in the raw
operation log. It never overwrites an earlier evidence directory. Failure tests
use separate seeded reports and confirm their exact bytes survive the rejection.

Latency is evaluator process creation through exit. Throughput includes wrapper,
validation and scheduling overhead. Peak memory comes from one child per fresh
measurement wrapper, preventing concurrent processes from mixing their resource
counters. Memory is checked after each evaluator exits; the runner does not enforce an OS
allocation limit. The sum of the largest concurrent-worker peak values is a conservative
upper bound, not a sampled simultaneous peak. Currency cost remains unavailable;
CPU seconds per validated operation are measured separately from trace-provided
cost fields.

If all increasing-load stages pass, report “saturation not reached at the tested
limit.” If a stage fails, retain it and report the highest passing tested level
without claiming an extrapolated capacity. Investigate that measured failure
before changing the implementation. Keep the criteria unchanged for before/after
comparisons; a new protocol requires its own reviewed criteria and new evidence.

The [October 14 measured report](benchmarks/OFFLINE_2026-10-14.md) includes all
stages, raw evidence, checksums and limitations.
