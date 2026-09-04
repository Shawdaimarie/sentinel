.PHONY: install quality test import-otel evaluate compare automation docker

install:
	python -m pip install -e ".[dev]"

quality:
	ruff check src tests
	mypy src

# Security, trace-import, code-review, and automation tests are part of the default test suite.
test:
	pytest -q

import-otel:
	sentinel-import-otel \
		--input examples/otel/agent_trace.json \
		--output reports/otel-agent-runs.jsonl \
		--manifest reports/otel-import-manifest.json
	sentinel-eval \
		--cases examples/otel/eval_case.jsonl \
		--runs reports/otel-agent-runs.jsonl \
		--report reports/otel-evaluation.md \
		--json-out reports/otel-evaluation.json \
		--min-score 0.90

evaluate:
	sentinel-eval \
		--cases examples/eval_cases.jsonl \
		--runs examples/eval_runs.jsonl \
		--report reports/evaluation.md \
		--json-out reports/evaluation.json \
		--min-score 0.90

compare:
	sentinel-eval \
		--cases examples/eval_cases.jsonl \
		--runs examples/eval_runs.jsonl \
		--baseline-runs examples/baseline_runs.jsonl \
		--report reports/evaluation.md \
		--json-out reports/evaluation.json \
		--comparison-json reports/comparison.json \
		--min-score 0.90

automation:
	sentinel-automation \
		--catalog automation/stability_tasks.json \
		--execute \
		--json-out reports/automation/stability.json \
		--markdown-out reports/automation/stability.md \
		--min-benefit-score 0.85

docker:
	docker build -t sentinel-eval .
