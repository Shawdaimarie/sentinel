.PHONY: demo down test test-isolated scenarios

demo:
	docker compose up --build -d

down:
	docker compose down

test:
	sh tools/run_local_tests.sh

test-isolated:
	sh tools/run_isolated_tests.sh

scenarios:
	python3 tools/validate_scenarios.py
