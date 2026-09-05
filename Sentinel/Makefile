.PHONY: install quality test import-otel evaluate compare code-review data-gate automation value-route capsules docker

install:
	python -m pip install -e ".[dev]"

quality:
	ruff check src tests
	mypy src

# Security, trace-import, code-review, value-routing, capsules, and automation tests are part of the default test suite.
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

code-review:
	sentinel-code-review \
		--cases examples/code_review_scorecard_cases.json \
		--json-out reports/code-review/scorecard.json \
		--markdown-out reports/code-review/scorecard.md

data-gate:
	sentinel-data-gate \
		--input examples/training/agent_safety_examples.jsonl \
		--json-out reports/data-gate/agent_safety_examples.json \
		--markdown-out reports/data-gate/agent_safety_examples.md \
		--min-examples 20

automation:
	sentinel-automation \
		--catalog automation/stability_tasks.json \
		--execute \
		--json-out reports/automation/stability.json \
		--markdown-out reports/automation/stability.md \
		--min-benefit-score 0.85

value-route:
	sentinel-value-router \
		--items examples/value_route_items.json \
		--json-out reports/value-route/value_routes.json \
		--markdown-out reports/value-route/value_routes.md \
		--min-score 0.70

capsules:
	sentinel-capsule \
		--capsules examples/deployment_capsules.json \
		--root . \
		--json-out reports/capsules/deployment_capsules.json \
		--markdown-out reports/capsules/deployment_capsules.md \
		--min-score 0.68

docker:
	docker build -t sentinel-eval .
