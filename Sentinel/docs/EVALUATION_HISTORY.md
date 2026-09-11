# Evaluation history

Sentinel can store evaluation metadata in PostgreSQL and query changes across
releases. The optional `history` extra adds `sentinel-history`; ordinary
evaluation continues to work without a database. PostgreSQL 16 is the tested
development and CI target.

## Storage contract and architecture

```text
SuiteReport -> bounded validation -> minimized snapshot + normalized rows
                                      | immutable source hashes
                                      v
                                PostgreSQL history
                                      |
                   read-only history, slices and paired comparison
                                      |
ComparisonReport -> replay against two stored suites -> stored regressions
```

`sentinel_history` contains versioned migrations, suites, cases, runs, metric
values, tags, source fingerprints, comparisons and regressions. Case identities
are scoped to a report, which carries the fingerprint of its case definitions.
A minimized JSONB snapshot retains the existing evaluator contract for replay;
normalized rows support case, metric and tag queries. Both representations are
inserted in one transaction. No raw prompts, outputs, URLs, tool arguments or
diagnostic text are stored. Metric details and failure text are replaced with
fixed placeholders; failure counts, scores and gate decisions remain visible.

Suite, release, system, case, run and tag identifiers must be non-sensitive
slugs of at most 128 characters. This syntax check is **not** a privacy
classifier: a token or personal identifier that looks like a slug can still
leak. Use pseudonymous identifiers and review source metadata before import.
Reports are limited to 8 MiB and 10,000 runs. Both `cases` and `runs` SHA-256
fingerprints are mandatory. Unknown report versions, duplicate JSON keys,
non-finite numbers and inconsistent aggregates are rejected.

An import ID hashes the suite label, release identifier and canonical input
report. Formatting changes do not create another record. The first accepted
artifact's exact-byte SHA-256 is retained separately. A new timestamp or other
content change is a different report; reuse of the same suite/release/system
is rejected. Give repeated trials or reevaluations distinct release identifiers.
The unique database constraint also makes concurrent identical imports safe.

Queries use fixed parameterized SQL, a read-only transaction, a five-second
connection/lock timeout and a thirty-second statement timeout. Pages contain
1–100 rows, with an offset and `next_offset`; offsets are limited to 100,000.
Ordering is stable by import sequence and case/run/tag keys. Pages are not a
shared database snapshot: retention between requests can shift offsets. Use a
database snapshot for large reproducible exports.

## Local setup

From `Sentinel/`:

```bash
python -m pip install -e ".[dev,history]"
# Set SENTINEL_HISTORY_DEV_PASSWORD securely in your shell, outside source control.
docker compose -f compose.history.yml up -d --wait
```

The database is bound to loopback port 5433 and stores data in a named volume.
The owner is `sentinel_owner`, database `sentinel_history`. No default password
is supplied. For connections outside the local development host, require TLS
with certificate verification (`sslmode=verify-full`) and restrict network access.

Set `SENTINEL_HISTORY_OWNER_DSN` through your secret manager or protected local
environment. Connection strings are never command arguments. Then:

```bash
sentinel-history migrate
docker compose -f compose.history.yml exec -T postgres \
  psql -U sentinel_owner -d sentinel_history -v ON_ERROR_STOP=1 < history/roles.sql
```

The SQL creates two NOLOGIN groups. As database administrator, create separate
login roles, assign their passwords with interactive `psql` `\password`, and
grant each login exactly one appropriate group:

```sql
CREATE ROLE history_reader_login LOGIN;
GRANT sentinel_history_reader TO history_reader_login;
CREATE ROLE history_writer_login LOGIN;
GRANT sentinel_history_writer TO history_writer_login;
```

Set `SENTINEL_HISTORY_READER_DSN` and `SENTINEL_HISTORY_WRITER_DSN` with those
separate credentials. The CLI never falls back to the owner connection.
The reader gets SELECT only. The writer gets SELECT, INSERT and sequence use;
it cannot update, delete, truncate, change migrations or create schema objects.
Review existing grants before reusing these group names in a shared cluster.
The grant script is additive; it does not remove unrelated privileges.

## Import, query and compare

Produce reports with the existing `sentinel-eval --json-out` option. Candidate
and baseline each need their own SuiteReport, using the same case definitions,
scoring configuration and case/run pair keys.

```bash
sentinel-eval --cases examples/eval_cases.jsonl --runs examples/baseline_runs.jsonl \
  --json-out reports/baseline.json --report reports/baseline.md
sentinel-eval --cases examples/eval_cases.jsonl --runs examples/eval_runs.jsonl \
  --json-out reports/candidate.json --report reports/candidate.md \
  --baseline-runs examples/baseline_runs.jsonl --comparison-json reports/comparison.json

sentinel-history import-suite --input reports/baseline.json --suite demo --release baseline-1
sentinel-history import-suite --input reports/candidate.json --suite demo --release candidate-1
sentinel-history query --suite demo --limit 20 --offset 0
sentinel-history query --suite demo --view runs --case-id privacy --safety-only
sentinel-history query --suite demo --view slices --tag security
```

Use the IDs returned by the two imports:

```bash
sentinel-history get --id BASELINE_ID
sentinel-history compare --baseline BASELINE_ID --candidate CANDIDATE_ID
sentinel-history import-comparison --input reports/comparison.json \
  --baseline BASELINE_ID --candidate CANDIDATE_ID
sentinel-history query --suite demo --view comparisons
```

`compare` writes nothing. It reports the evaluator's promotion decision,
individual regressions, cost delta and mean-latency delta. Comparisons reject
changed case fingerprints, configurations, suite labels or unmatched run keys.
This is intentionally stricter than the evaluator's shared-pair comparison.
Stored comparisons must exactly match the replayed decision, including their
regression tolerance; callers cannot import a fabricated passing comparison.

CLI exit codes: 0 means the requested storage/query operation succeeded; 2
means invalid input or a database failure. A comparison returning 0 can still
have `promotion_recommended=false`. For release enforcement, keep using
`sentinel-eval` or explicitly evaluate the returned decision. Never treat a
successful query as permission to release.

## Migrations and recovery

Migrations ship inside the Python wheel. `migrate` serializes migration writers
with a transaction-scoped advisory lock, validates checksums, and applies all
pending SQL in one transaction. Failure rolls back the migration attempt.
Already-applied SQL must not be edited. Add a new forward migration instead.
Reapply `history/roles.sql` after adding tables. Automatic destructive down
migrations are intentionally unavailable.

Migration 001 creates the tables; 002 adds indexes. CI tests upgrading a populated
001 database, repeat application, checksum mismatch, and rejection of downgrade.
Before upgrading a deployed database, stop imports and create a verified backup.
If an incompatible upgrade fails after deployment, restore into a separate
database and switch connections after validation rather than editing live history.

Use PostgreSQL 16 client tools or newer compatible tools. Configure connection
details with protected PostgreSQL environment variables or a service file and
restrict backup directory permissions:

```bash
umask 077
pg_dump --format=custom --no-owner --no-privileges --file=history.dump
# Administrator creates a separate empty recovery database first.
pg_restore --exit-on-error --no-owner --no-privileges \
  --dbname=RECOVERY_DATABASE history.dump
```

Backups exclude grants: provision roles and reapply `history/roles.sql` on the
recovery database before serving readers/writers. Verify migrations, source
hashes, suite counts and a known baseline/candidate comparison before changing
the application connections. Protect and encrypt backups separately. CI restores
a real dump into a fresh database and reproduces a stored release comparison.
This is a logical restore test, not a claim about production RPO/RTO or point-in-time recovery.

## Retention and threat boundary

There is no automatic deletion and no delete command in the reader/writer CLI.
Choose retention before using operational data. A database owner can delete
selected suites in a transaction after checking an explicit retention cutoff.
Foreign keys cascade to normalized records and comparisons referencing either
deleted suite, including regression rows. Preview affected comparison IDs,
export needed evidence, and record the deletion decision in an external audit
log before committing it. Backups have their own retention; database deletion
does not remove older backups or externally held input artifacts.

Hashes provide references, not authenticity, encryption or proof of completeness.
The history service does not possess raw source artifacts, so it can replay a
comparison but cannot independently reevaluate the original agent output. A
writer can submit a well-formed dishonest report; a database owner can alter
stored records. Protect writer identity, review release evidence, retain raw
sources in controlled storage and anchor important evidence outside this database.
There is no HTTP service, tenant isolation or authorization server in this increment.

## Verification

Use a disposable PostgreSQL database whose name ends in `_test`. Integration
tests reset its history schema and create temporary login roles and a recovery
database; never point them at an operational database.

```bash
# Set SENTINEL_HISTORY_TEST_DSN to that disposable database's administrator DSN.
pytest -q tests/test_history.py tests/test_history_postgres.py
```

`pg_dump` and `pg_restore` must be available. The `evaluation-history` CI job
starts an ephemeral PostgreSQL 16 service, installs the built package, verifies
packaged migrations, and tests transactions, role boundaries, pagination,
comparison replay and backup/restore. Its fixed password belongs only to the
disposable CI service. Without the test DSN, ordinary local tests skip the
PostgreSQL integration module; those skips are not database verification.
