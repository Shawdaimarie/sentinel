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
