# Offline evaluation performance acceptance

This protocol answers a bounded operator question: can one developer evaluate
repeated batches of saved agent traces without excessive delay, memory use, or
loss of an earlier report when an input fails? It sets pass/fail criteria before
the capacity test in [issue 62](https://github.com/Shawdaimarie/sentinel/issues/62).
The criteria must merge before the first measured run. Their source is
[`offline-evaluation-v1.json`](../benchmarks/offline-evaluation-v1.json).

These are engineering targets for a local reference workload, not measured
capacity, a buyer's service-level agreement, or evidence of model quality.
The reference operation is one complete `sentinel-eval` process: interpreter
startup, input loading, evaluation, and JSON/Markdown report generation. No
network request or model inference occurs. Recorded `latency_ms` and `cost_usd`
inside input traces describe the synthetic agent runs; they must never be used
as measurements of evaluator runtime or infrastructure cost.

## Workload and environment

Use Python 3.12 and a fresh wheel installation of the exact assessed commit.
Record the wheel hash, dependency versions, operating system, architecture,
logical CPU count, available memory, power mode if available, and any competing
workload. Run on the existing local development machine without provisioning
paid infrastructure. Record unavailable environment fields as unavailable.
Results are specific to that machine; comparisons need the same environment.

Start with the six cases and six candidate runs in `examples/eval_cases.jsonl`
and `examples/eval_runs.jsonl`. Repeat the run set 20 times, changing only each
`run_id` to a unique deterministic identifier. Each batch has six cases and
120 runs and must stay below 1 MiB of combined input. Retain exact generated
input bytes and SHA-256 hashes. Outputs use a separate directory per operation;
workers never share report paths. All reports must contain exactly 120 results,
the expected input hashes, a passing evaluation gate, and no safety failures.
An exit code alone is insufficient evidence of a successful operation.

The reference demand is one batch at a time. Twice demand means two independent
concurrent batches. This is a closed-loop worker test, with no unmeasured request
queue: each worker starts another batch after validating its previous result.
It does not estimate latency under a fixed external arrival rate or prove
absence of overload when requests queue outside the process.

## Pass and fail rules

Discard three sequential warm-up batches. Measure each normal stage for at least
30 seconds and at least ten completed batches, draining all started work. Use
monotonic wall time from immediately before process creation through process
exit for each batch. Report nearest-rank p50, p95 and p99, sample count, total
stage duration including drain, and validated batches and runs per second.

| Stage | Concurrency | p95 maximum | p99 maximum | Validated throughput minimum |
|---|---:|---:|---:|---:|
| Expected demand | 1 | 3 seconds | 5 seconds | 0.3 batches/second |
| Twice demand | 2 | 5 seconds | 8 seconds | 0.5 batches/second |
| Sustained demand | 2 for 300 seconds | 5 seconds | 8 seconds | 0.5 batches/second |

Every stage requires zero unexpected process failures, timeouts, malformed
reports, wrong input hashes, missing results, or incorrect gate decisions.
Count all attempted batches, including failed ones; never drop failures from
the error-rate denominator. A deliberate negative case is successful only when
it produces its specified rejection. Separate those cases from normal traffic.

Each worker process has a ten-second deadline and a maximum peak resident
memory of 512 MiB. Record per-process user/system CPU seconds and peak RSS,
normalizing platform units. The sum of concurrent workers' peak RSS must stay
at or below 4 GiB; label this sum as an upper bound, not a sampled simultaneous
memory peak. Stop at eight workers or 900 seconds total. Exceeding a limit is a
failed or incomplete run, never a passing capacity claim. Record harness memory
separately when available. Do not alter the machine's security or power settings.

## Increasing load and failure recovery

After expected and twice-demand stages, test concurrency 1, 2, 4 and 8 for
30 seconds each using the same inputs. Apply the twice-demand latency, memory,
and zero-error thresholds at each level. Report throughput at every level.
The highest passing tested level is only a tested bound. If no level fails,
state that saturation was not reached; do not extrapolate a maximum capacity.
Stop increasing load after a failing level and preserve its results.

During the two-worker failure stage, alternate normal batches with five cases
of each local dependency failure: a missing runs file and a malformed JSONL
runs file. Seed the negative operation's report files with known sentinel bytes.
Each negative operation must exit 2 within ten seconds and leave those files
byte-identical. Immediately run a valid batch in that worker: it must pass
within ten seconds. Other workers' valid reports must remain correct. This
establishes recovery from these file-input failures only, not database or
network outages, process-crash atomicity, backup recovery, or Aegis availability.

For this stateless workload, the recovery objective is a successful next batch
within ten seconds; the data-loss objective is zero changes to the seeded
earlier reports on the two tested input failures. Production RTO and RPO remain
undefined until a real deployment and its owner establish them.

## Budget, evidence and change control

The incremental paid infrastructure budget is $0 and external model calls are
zero. Report measured CPU seconds per validated batch and per evaluated run.
Report currency cost per successful operation as unavailable unless an explicit
compute price and allocation basis are provided. Existing hardware, electricity,
and staff time are not free merely because no new service was purchased.

Retain the exact assessed commit, criteria commit and file hash, wheel and input
hashes, environment, dependency list, every operation's metrics/outcome, stage
summaries, commands and limitations. A rerun must create a new evidence directory
and never overwrite a prior result. The report must distinguish PASS, FAIL and
INCOMPLETE. Missing stages, missing metrics, mismatched criteria, a stopped run,
or insufficient samples prevent an overall PASS.

Never relax thresholds after seeing the measurements. Change workload or targets
in a new reviewed version, merge it, and rerun; retain the earlier results.
Use measured failures to choose work in
[issue 63](https://github.com/Shawdaimarie/sentinel/issues/63), then compare the
same workload and criteria before and after. No speculative cache, database
migration, hosted service, or new spending is part of this protocol.
