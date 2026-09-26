#!/usr/bin/env bash
# Verify a published Sentinel image before you run it.
#
# Resolves the reference to an immutable digest, then checks that the digest
# carries Sigstore-signed SLSA provenance and an SPDX SBOM produced by this
# repository's release workflow from the expected source ref. Prints the
# digest reference to deploy. Exits non-zero if anything cannot be verified.
#
# Usage:
#   scripts/verify-image.sh IMAGE[:TAG|@sha256:DIGEST] [--source-ref REF]
#
# The source ref is inferred only when the tag names it unambiguously:
#   vX.Y.Z or X.Y.Z  -> refs/tags/vX.Y.Z
#   edge             -> refs/heads/main
# Floating tags (latest, X.Y), sha-<commit> tags, and digests can come from
# more than one ref, so they require --source-ref. Trust inputs are never
# guessed.
#
# Requires: gh (2.49+) and docker with buildx.

set -euo pipefail

readonly REPO="Shawdaimarie/sentinel"
readonly SIGNER="${REPO}/.github/workflows/release.yml"
readonly SPDX="https://spdx.dev/Document/v2.3"
readonly REGISTRY="ghcr.io/shawdaimarie"

fail() {
  echo "verify-image: $*" >&2
  exit 1
}

usage() {
  sed -n '9,11p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

image=""
source_ref=""
while [ $# -gt 0 ]; do
  case "$1" in
    --source-ref)
      [ $# -ge 2 ] || usage
      source_ref="$2"
      shift 2
      ;;
    -h | --help) usage ;;
    -*) usage ;;
    *)
      [ -z "$image" ] || usage
      image="$1"
      shift
      ;;
  esac
done
[ -n "$image" ] || usage

case "$image" in
  "${REGISTRY}"/sentinel-eval[:@]* | "${REGISTRY}"/aegis-authorizer[:@]*) ;;
  *) fail "not a Sentinel release image: ${image} (expected ${REGISTRY}/sentinel-eval or ${REGISTRY}/aegis-authorizer with a tag or digest)" ;;
esac

case "$image" in
  *@sha256:*)
    name="${image%@*}"
    name="${name%:*}"
    digest="${image#*@}"
    tag=""
    ;;
  *)
    name="${image%:*}"
    tag="${image##*:}"
    digest=""
    ;;
esac

if [ -z "$source_ref" ]; then
  case "$tag" in
    v[0-9]*.[0-9]*.[0-9]*) source_ref="refs/tags/${tag}" ;;
    [0-9]*.[0-9]*.[0-9]*) source_ref="refs/tags/v${tag}" ;;
    edge) source_ref="refs/heads/main" ;;
    *) fail "cannot infer the source ref for '${tag:-${digest}}'; pass --source-ref (for example refs/tags/v0.7.0 or refs/heads/main)" ;;
  esac
fi
case "$source_ref" in
  refs/heads/main | refs/tags/v*) ;;
  *) fail "source ref ${source_ref} is not releasable; only refs/heads/main and refs/tags/v* are signed" ;;
esac

command -v gh >/dev/null 2>&1 || fail "gh is required: https://cli.github.com"

if [ -z "$digest" ]; then
  command -v docker >/dev/null 2>&1 || fail "docker with buildx is required to resolve ${image}"
  digest="$(docker buildx imagetools inspect "$image" --format '{{.Manifest.Digest}}')" ||
    fail "could not resolve ${image} to a digest"
fi
case "$digest" in
  sha256:*) ;;
  *) fail "resolved an invalid digest '${digest}' for ${image}" ;;
esac

subject="${name}@${digest}"
echo "Subject:    ${subject}"
echo "Signer:     ${SIGNER}"
echo "Source ref: ${source_ref}"

gh attestation verify "oci://${subject}" \
  --repo "$REPO" --signer-workflow "$SIGNER" --source-ref "$source_ref" >/dev/null ||
  fail "build provenance did not verify for ${subject}"
echo "Provenance: verified (SLSA v1)"

gh attestation verify "oci://${subject}" \
  --repo "$REPO" --signer-workflow "$SIGNER" --source-ref "$source_ref" \
  --predicate-type "$SPDX" >/dev/null ||
  fail "SBOM attestation did not verify for ${subject}"
echo "SBOM:       verified (SPDX 2.3)"

echo
echo "Deploy by digest so what runs is what was verified:"
echo "  ${subject}"
