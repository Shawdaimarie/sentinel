#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export COMPOSE_PROJECT_NAME="sentinel-performance-$$"
export SENTINEL_GATEWAY_PORT=18082
export SENTINEL_EXPLORER_PORT=15175
override=$(mktemp -t sentinel-performance)
python3 - "$override" <<'PY'
import json,sys
tokens={f'load-token-{i:02}':f'load-{i:02}:tenant-a' for i in range(50)}
with open(sys.argv[1],'w') as file:
    json.dump({'services':{'gateway':{'environment':{'SENTINEL_LOCAL_TOKENS':json.dumps(tokens)}}}},file)
PY
cleanup() {
  docker compose -f docker-compose.yml -f "$override" down --volumes --remove-orphans
  rm -f "$override"
}
trap cleanup EXIT INT TERM
docker compose -f docker-compose.yml -f "$override" up --build -d db gateway
ready=0
for attempt in $(seq 1 60); do
  if curl --fail --silent "http://127.0.0.1:$SENTINEL_GATEWAY_PORT/health" >/dev/null; then ready=1; break; fi
  sleep 1
done
test "$ready" -eq 1
python3 tools/load_benchmark.py --base-url "http://127.0.0.1:$SENTINEL_GATEWAY_PORT" --output "evaluation/artifacts/performance-$(date -u +%Y%m%dT%H%M%SZ).json"
