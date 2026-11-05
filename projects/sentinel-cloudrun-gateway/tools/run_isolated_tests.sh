#!/bin/sh
set -eu

# Uses a separate Compose project and database so the active demo is untouched.
export COMPOSE_PROJECT_NAME="sentinel-verify-$$"
export SENTINEL_GATEWAY_PORT=$((20000 + ($$ % 20000)))
export SENTINEL_EXPLORER_PORT=$((SENTINEL_GATEWAY_PORT + 1))
export SENTINEL_BASE_URL="http://127.0.0.1:${SENTINEL_GATEWAY_PORT}"

cleanup() {
  docker compose down --volumes --remove-orphans
}
trap cleanup EXIT INT TERM

docker compose up --build -d
ready=0
for attempt in $(seq 1 60); do
  if curl --fail --silent "$SENTINEL_BASE_URL/health" >/dev/null; then ready=1; break; fi
  sleep 1
done
test "$ready" -eq 1
ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent "http://127.0.0.1:${SENTINEL_EXPLORER_PORT}/" >/dev/null; then ready=1; break; fi
  sleep 1
done
test "$ready" -eq 1
python3 tools/benchmark_gateway.py --requests 1000 --concurrency 10

python3 tools/validate_scenarios.py
python3 tests/migration_privileges.py
python3 tests/smoke.py
python3 tests/rate_limit.py
python3 tests/rollback.py

SENTINEL_CAPABILITY_TTL_SECONDS=1 docker compose up -d --force-recreate gateway
ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent "$SENTINEL_BASE_URL/health" >/dev/null; then ready=1; break; fi
  sleep 1
done
test "$ready" -eq 1
python3 tests/expiry.py
python3 tests/backup_restore.py
echo "PASS: isolated clean-Compose regression; the existing demo project was not modified"
