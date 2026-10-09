#!/usr/bin/env bash
# Run packaged behavior checks using synthetic inputs, never production keys.
# Requires Docker, curl and Python 3; run from a checkout matching the image.
set -euo pipefail

component="${1:?Usage: smoke-image.sh COMPONENT IMAGE}"
image="${2:?Usage: smoke-image.sh COMPONENT IMAGE}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
container=""
scratch="$(mktemp -d)"
cleanup() {
  if [ -n "$container" ]; then
    docker logs "$container" >&2 || true
    docker rm -f "$container" >/dev/null || true
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
    container="$(docker run -d "${restricted[@]}" \
      -p 127.0.0.1::8080 \
      --mount "type=bind,src=${root}/Aegis/examples,dst=/examples,readonly" \
      --tmpfs /audit:rw,nosuid,nodev,size=16m,mode=1777 \
      "$image" --policy /examples/policy.json --jwks /examples/jwks.json \
      --listen 0.0.0.0:8080 --audit-log /audit/decisions.jsonl --state-log /audit/state.jsonl)"
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
    status="$(curl --silent --show-error --max-time 5 -o "$scratch/denied.json" -w '%{http_code}' \
      -H 'Content-Type: application/json' -d '{}' "http://${address}/v1/authorize")"
    test "$status" = 403
    python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["allowed"] is False' "$scratch/denied.json"
    ;;
  *) echo "Unknown component: $component" >&2; exit 2 ;;
esac
echo "Packaged behavior smoke check passed: $component ($image)"
