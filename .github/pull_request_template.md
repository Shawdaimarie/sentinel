## Objective

Describe the user-visible or risk-reduction outcome.

## Evidence

- [ ] Tests added or updated
- [ ] Evaluation cases added or updated when behavior changes
- [ ] `ruff check src tests`
- [ ] `mypy src`
- [ ] `pytest -q`
- [ ] `sentinel-eval` release gate
- [ ] Security boundaries reviewed
- [ ] Documentation and residual risk updated

## Risk review

What new permissions, data flows, external calls, or failure modes does this
change introduce? State why the change is safe to merge or identify the
remaining mitigation.

## Owner review preparation

Use [the owner review guide](https://github.com/Shawdaimarie/sentinel/blob/main/Sentinel/docs/OWNER_REVIEW.md).

- Explain the reproduction and expected user-visible result.
- Identify compatibility changes and the recovery or revert path.
- For performance claims, provide the workload, measurements, and tradeoffs.
- Link checks for the current head commit; distinguish skips and untested behavior.

The author or assistant prepares evidence, not approval. @Shawdaimarie records
the final decision against the full head SHA after reviewing it. Any new push
requires a fresh decision. Publishing and deployment need separate authorization.
