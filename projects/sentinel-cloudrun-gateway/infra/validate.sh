#!/bin/sh
set -eu
# Offline with respect to cloud APIs: init downloads signed providers, then mock plans.
# No plan against real accounts, apply, login, or resource creation occurs here.
cd "$(dirname "$0")"
root=$(pwd)
engine='hashicorp/terraform:1.13.5@sha256:6bbb82d575aa7bd4f0a2c6e3a0838ab9590426c08a71d7a2783643f01004d356'
mkdir -p evidence
run_terraform() {
  cloud=$1
  operation=$2
  shift 2
  log="evidence/$cloud-$operation.log"
  if ! docker run --rm -v "$root/$cloud:/infra" -w /infra "$engine" "$@" >"$log" 2>&1; then
    cat "$log"
    return 1
  fi
}

for cloud in gcp aws azure oci; do
  run_terraform "$cloud" init init -backend=false -input=false -lockfile=readonly -no-color
  run_terraform "$cloud" format fmt -check -recursive -no-color
  run_terraform "$cloud" validate validate -no-color
  run_terraform "$cloud" tests test -no-color
  echo "PASS: $cloud format, provider schema, and mocked configuration guardrails (not deployed)"
done
