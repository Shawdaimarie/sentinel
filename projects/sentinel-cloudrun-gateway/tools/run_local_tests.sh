#!/bin/sh
set -eu

# Tests intentionally use an isolated synthetic Compose database; running this
# script removes the current demo's local synthetic records and restarts it clean.
docker compose down
docker compose up --build -d
ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8080/health >/dev/null; then ready=1; break; fi
  sleep 1
done
test "$ready" -eq 1
python3 tools/validate_scenarios.py
python3 tests/smoke.py
python3 tests/rate_limit.py
docker compose down
SENTINEL_CAPABILITY_TTL_SECONDS=1 docker compose up --build -d
sleep 2
python3 tests/expiry.py
docker compose down
docker compose up --build -d
