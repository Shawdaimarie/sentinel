# Stability Automation and Refinement Method

Sentinel's automation layer turns software-refinement work into repeatable,
benefit-gated tasks. The goal is not uncontrolled autonomy. The goal is to make
high-value engineering checks run consistently, produce evidence, and refuse
work that is unsafe, manual, identity-sensitive, or not worth running.

## Operating rule

Every automated task must satisfy three conditions before it can execute:

1. **Required value** — the task must have a declared purpose tied to quality,
   security, evaluation, observability, portfolio credibility, or governance.
2. **Benefit gate** — the task must meet or exceed the configured minimum
   benefit score. The default automation threshold is `0.85`.
3. **Safety gate** — the task must use an allowlisted command with no shell
   expansion, destructive chaining, hidden identity work, or external credential
   requirement.

This means the system does not attempt to automate interviews, identity checks,
legal documents, background checks, account sign-ins, or assessment responses.
Those remain human-only work.

## Refinement layers

| Layer | Purpose | Automated evidence |
|---|---|---|
| Quality | Preserve implementation discipline. | Ruff, strict mypy, tests. |
| Security | Surface risk before proof is reused externally. | Dependency audit and hard safety gates. |
| Evaluation | Keep AI-agent behavior measurable across changes. | Deterministic release gate and coding-agent scorecard. |
| Observability | Connect runtime traces to evaluation contracts. | OTLP trace import and normalized run artifacts. |
| Portfolio | Keep public proof credible. | CI-backed case studies and verifiable project links. |
| Governance | Separate automated work from human-only decisions. | Manual tasks are tracked but never executed by the runner. |

## Command boundary

The runner executes commands with `subprocess.run` and `shell=False`. It only
accepts explicit command arrays whose first executable is allowlisted.

Current allowed executables:

- `python` with explicitly allowlisted modules only;
- `ruff`;
- `mypy`;
- `pytest`;
- `pip-audit`;
- `sentinel-eval`;
- `sentinel-code-review`; and
- `sentinel-import-otel`.

Arguments containing shell chaining or expansion tokens are rejected.

## Stability catalog

The default catalog is:

```text
automation/stability_tasks.json
```

It currently runs:

1. source and test linting;
2. strict type checking;
3. unit, security, evaluation, and automation tests;
4. dependency vulnerability audit;
5. deterministic agent release gate; and
6. coding-agent review scorecard generation.

Each task carries a rationale, a benefit score, required/optional status, and
evidence paths.

## Local execution

From `Sentinel/`:

```bash
python -m pip install -e ".[dev]" pip-audit
sentinel-automation \
  --catalog automation/stability_tasks.json \
  --execute \
  --json-out reports/automation/stability.json \
  --markdown-out reports/automation/stability.md \
  --min-benefit-score 0.85
```

If any required automated task is skipped or fails, the command exits nonzero.

## GitHub Actions execution

The `Stability Automation` workflow runs this same catalog on a schedule,
through manual dispatch, and when automation-relevant files change. It uploads
JSON, Markdown, and evaluation artifacts so that the project keeps a current
trail of proof.

## What this proves

This layer proves that the project can:

- distinguish beneficial automation from unsafe automation;
- keep quality, security, and evaluation tasks tied to explicit business value;
- run repeatable software-development refinement without hidden side effects;
- preserve evidence for review; and
- maintain human control over identity-sensitive and contractual actions.

## What this does not prove

It does not prove universal AI safety, production certification, or guaranteed
employment income. It strengthens the engineering evidence used to compete for
software engineering, applied AI, AI reliability, model evaluation, and
developer tooling roles.
