CREATE TABLE sentinel_history.suites (
    id text PRIMARY KEY CHECK (id ~ '^[a-f0-9]{64}$'),
    sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    suite text NOT NULL,
    release text NOT NULL,
    system text NOT NULL,
    generated_at timestamptz NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[a-f0-9]{64}$'),
    report jsonb NOT NULL,
    UNIQUE (suite, release, system)
);
CREATE TABLE sentinel_history.sources (
    suite_id text NOT NULL REFERENCES sentinel_history.suites(id) ON DELETE CASCADE,
    name text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    PRIMARY KEY (suite_id, name)
);
CREATE TABLE sentinel_history.cases (
    suite_id text NOT NULL REFERENCES sentinel_history.suites(id) ON DELETE CASCADE,
    case_id text NOT NULL,
    PRIMARY KEY (suite_id, case_id)
);
CREATE TABLE sentinel_history.runs (
    suite_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL,
    score double precision NOT NULL CHECK (score BETWEEN 0 AND 1),
    passed boolean NOT NULL,
    safety_passed boolean NOT NULL,
    latency_ms bigint NOT NULL CHECK (latency_ms >= 0),
    cost_usd double precision NOT NULL CHECK (cost_usd >= 0 AND cost_usd < 'Infinity'),
    executed_actions bigint NOT NULL CHECK (executed_actions >= 0),
    hard_failure_count integer NOT NULL CHECK (hard_failure_count >= 0),
    PRIMARY KEY (suite_id, case_id, run_id),
    FOREIGN KEY (suite_id, case_id)
        REFERENCES sentinel_history.cases(suite_id, case_id) ON DELETE CASCADE
);
CREATE TABLE sentinel_history.metrics (
    suite_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL,
    name text NOT NULL,
    value double precision NOT NULL CHECK (value BETWEEN 0 AND 1),
    weight double precision NOT NULL CHECK (weight BETWEEN 0 AND 1),
    passed boolean NOT NULL,
    PRIMARY KEY (suite_id, case_id, run_id, name),
    FOREIGN KEY (suite_id, case_id, run_id)
        REFERENCES sentinel_history.runs(suite_id, case_id, run_id) ON DELETE CASCADE
);
CREATE TABLE sentinel_history.tags (
    suite_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL,
    tag text NOT NULL,
    PRIMARY KEY (suite_id, case_id, run_id, tag),
    FOREIGN KEY (suite_id, case_id, run_id)
        REFERENCES sentinel_history.runs(suite_id, case_id, run_id) ON DELETE CASCADE
);
CREATE TABLE sentinel_history.comparisons (
    id text PRIMARY KEY CHECK (id ~ '^[a-f0-9]{64}$'),
    sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    baseline_id text NOT NULL REFERENCES sentinel_history.suites(id) ON DELETE CASCADE,
    candidate_id text NOT NULL REFERENCES sentinel_history.suites(id) ON DELETE CASCADE,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[a-f0-9]{64}$'),
    imported_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    report jsonb NOT NULL,
    CHECK (baseline_id <> candidate_id)
);
CREATE TABLE sentinel_history.regressions (
    comparison_id text NOT NULL REFERENCES sentinel_history.comparisons(id) ON DELETE CASCADE,
    case_id text NOT NULL,
    run_id text NOT NULL,
    baseline_score double precision NOT NULL,
    candidate_score double precision NOT NULL,
    delta double precision NOT NULL,
    reason text NOT NULL,
    PRIMARY KEY (comparison_id, case_id, run_id)
);
REVOKE ALL ON ALL TABLES IN SCHEMA sentinel_history FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA sentinel_history FROM PUBLIC;
