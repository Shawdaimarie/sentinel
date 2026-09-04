.PHONY: install quality test evaluate compare docker

install:
	python -m pip install -e ".[dev]"

quality:
	ruff check src tests
	mypy src

# Security tests are part of the default test suite.
test:
	pytest -q

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

docker:
	docker build -t sentinel-eval .
