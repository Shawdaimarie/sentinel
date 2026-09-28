#!/usr/bin/env bash
# Smoke-test the Sentinel and Aegis container images.
#
# The same script runs in CI against freshly built images and, in INSTALLING.md,
# against verified release digests. What users run is what CI proves.
#
# Usage (from the repository root):
#   bash scripts/smoke-test-images.sh SENTINEL_IMAGE AEGIS_IMAGE
#
# Checks:
#   sentinel-eval     --help works; the bundled example suite passes the release
#                     gate inside the container as the non-root user.
#   aegis-authorizer  configuration loads; discovery endpoints answer 200; an
#                     authorization request without a capability is refused
#                     with 403 (fail closed).
#
# Requires: docker, curl. Uses only the loopback interface of the host.

set -euo pipefail

[ $# -eq 2 ] || { sed -n '7,8p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
sentinel_image="$1"
aegis_image="$2"
port="${AEGIS_SMOKE_PORT:-18080}"
root="$(cd "$(dirname "$0")/.." && pwd)"
container=""
volume="aegis-smoke-$$"

cleanup() {
  if [ -n "$container" ]; then
    docker rm -f "$container" >/dev/null 2>&1 || true
  fi
  docker volume rm -f "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT

step() { echo "==> $*"; }
fail() { echo "smoke-test: $*" >&2; exit 1; }

step "sentinel-eval: --help"
docker run --rm "$sentinel_image" --help >/dev/null || fail "sentinel-eval --help failed"

step "sentinel-eval: example suite passes the release gate and writes reports"
reports="$(mktemp -d)"
docker run --rm --read-only --tmpfs /tmp --user "$(id -u):$(id -g)" \
  -v "$root/Sentinel/examples:/workspace/examples:ro" \
  -v "$reports:/workspace/reports" \
  "$sentinel_image" \
  --cases examples/eval_cases.jsonl \
  --runs examples/eval_runs.jsonl ||
  fail "sentinel-eval release gate failed inside the container"
[ -s "$reports/evaluation.md" ] || fail "sentinel-eval did not write reports/evaluation.md"
rm -rf "$reports"

aegis_args=(
  --policy /config/policy.json
  --trust-bundle /config/trust_bundle.json
  --audit-log /data/aegis-decisions.jsonl
  --state-log /data/aegis-state.jsonl
)
aegis_mounts=(
  --read-only
  -v "$root/Aegis/examples:/config:ro"
  -v "$volume:/data"
)

step "aegis-authorizer: configuration loads"
docker run --rm "${aegis_mounts[@]}" "$aegis_image" "${aegis_args[@]}" --check-config ||
  fail "aegis configuration check failed"

step "aegis-authorizer: serve on 127.0.0.1:${port}"
container="$(docker run -d "${aegis_mounts[@]}" -p "127.0.0.1:${port}:8080" \
  "$aegis_image" "${aegis_args[@]}" --listen 0.0.0.0:8080)"

base="http://127.0.0.1:${port}"
ready=""
for _ in $(seq 1 30); do
  if curl -fsS "$base/.well-known/openid-configuration" >/dev/null 2>&1; then
    ready=yes
    break
  fi
  sleep 1
done
[ -n "$ready" ] || { docker logs "$container" >&2 || true; fail "aegis did not become ready"; }

status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

step "aegis-authorizer: discovery endpoints answer 200"
[ "$(status "$base/.well-known/openid-configuration")" = 200 ] || fail "openid-configuration not 200"
[ "$(status "$base/jwks.json")" = 200 ] || fail "jwks.json not 200"

step "aegis-authorizer: request without a capability is refused (403)"
code="$(status -X POST -H 'Content-Type: application/json' -d '{}' "$base/v1/authorize")"
[ "$code" = 403 ] || fail "expected 403 for a request without a capability, got ${code}"

echo "smoke-test: all checks passed"
