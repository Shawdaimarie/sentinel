CREATE INDEX suites_history ON sentinel_history.suites (suite, sequence);
CREATE INDEX runs_case_history ON sentinel_history.runs (case_id, suite_id);
CREATE INDEX runs_safety_failures ON sentinel_history.runs (suite_id)
    WHERE NOT safety_passed;
CREATE INDEX tags_history ON sentinel_history.tags (tag, suite_id);
CREATE INDEX comparisons_candidate ON sentinel_history.comparisons (candidate_id, sequence);
CREATE INDEX comparisons_baseline ON sentinel_history.comparisons (baseline_id);
