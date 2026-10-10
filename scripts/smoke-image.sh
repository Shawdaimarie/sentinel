#!/usr/bin/env bash
# Run packaged behavior checks using synthetic inputs, never production keys.
# Requires Docker, curl and Python 3; run from a checkout matching the image.
set -euo pipefail

component="${1:?Usage: smoke-image.sh COMPONENT IMAGE}"
image="${2:?Usage: smoke-image.sh COMPONENT IMAGE}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
container=""
volume=""
scratch="$(mktemp -d)"
cleanup() {
  if [ -n "$container" ]; then
    docker logs "$container" >&2 || true
    docker rm -f "$container" >/dev/null || true
  fi
  if [ -n "$volume" ]; then
    docker volume rm "$volume" >/dev/null || true
  fi
  rm -rf "$scratch"
}
trap cleanup EXIT
restricted=(--read-only --cap-drop ALL --security-opt no-new-privileges --memory 256m --cpus 1)

case "$component" in
  sentinel-eval)
    test "$(docker image inspect "$image" --format '{{.Config.User}}')" = sentinel
    docker run --rm "${restricted[@]}" --network none "$image" --help
    docker run --rm "${restricted[@]}" --network none \
      --mount "type=bind,src=${root}/Sentinel/examples/reliability_assessment/suite.json,dst=/suite.json,readonly" \
      --tmpfs /evidence:rw,nosuid,nodev,size=16m,mode=1777 \
      --entrypoint sentinel-assess "$image" \
      --suite /suite.json --output-dir /evidence/assessment
    ;;
  aegis-authorizer)
    test "$(docker image inspect "$image" --format '{{.Config.User}}')" = 65532:65532
    # Docker generates a fresh name. Never reuse or delete a caller's volume.
    volume="$(docker volume create --label org.sentinel.purpose=smoke-test)"
    for sequence in 1 2; do
      container="$(docker run -d "${restricted[@]}" \
        -p 127.0.0.1::8080 \
        --mount "type=bind,src=${root}/Aegis/examples,dst=/examples,readonly" \
        --mount "type=volume,src=${volume},dst=/data" \
        "$image" --policy /examples/policy.json --jwks /examples/jwks.json \
        --listen 0.0.0.0:8080 --audit-log /data/decisions.jsonl --state-log /data/state.jsonl)"
      address="$(docker port "$container" 8080/tcp)"
      ready=false
      for attempt in $(seq 1 20); do
        if curl --fail --silent --max-time 2 "http://${address}/.well-known/openid-configuration" > "$scratch/discovery.json"; then
          ready=true
          break
        fi
        sleep 1
      done
      test "$ready" = true
      python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["issuer"] == "https://aegis.local.example"' "$scratch/discovery.json"
      status="$(curl --silent --show-error --max-time 5 -o "$scratch/denied-${sequence}.json" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d '{}' "http://${address}/v1/authorize")"
      test "$status" = 403
      python3 - "$scratch/denied-${sequence}.json" "$sequence" <<'PY'
import json, re, sys
result = json.load(open(sys.argv[1]))
assert result["allowed"] is False and result["reason"] == "invalid_token", result
assert result["audit_sequence"] == int(sys.argv[2]), result
assert re.fullmatch(r"[0-9a-f]{64}", result["audit_hash"]), result
PY
      docker cp "$container:/data/decisions.jsonl" "$scratch/audit-${sequence}.jsonl"
      docker rm -f "$container" >/dev/null
      container=""
    done
    python3 - "$scratch" <<'PY'
import json, sys
from pathlib import Path
work = Path(sys.argv[1])
first = [json.loads(line) for line in (work / "audit-1.jsonl").read_text().splitlines()]
second = [json.loads(line) for line in (work / "audit-2.jsonl").read_text().splitlines()]
assert len(first) == 1 and len(second) == 2, (first, second)
assert second[0] == first[0], "Replacing the container changed the previous audit record"
assert second[1]["sequence"] == 2 and second[1]["previous_hash"] == first[0]["record_hash"]
for index, record in enumerate(second, 1):
    response = json.loads((work / f"denied-{index}.json").read_text())
    assert record["record_hash"] == response["audit_hash"]
    assert record["reason"] == "invalid_token" and record["decision"] == "deny"
PY
    echo "Persistent audit check passed: two container instances, one volume, linked records 1 and 2"
    ;;
  *) echo "Unknown component: $component" >&2; exit 2 ;;
esac
echo "Packaged behavior smoke check passed: $component ($image)"
