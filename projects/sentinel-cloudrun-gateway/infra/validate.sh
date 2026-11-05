#!/bin/sh
set -eu
# Offline with respect to cloud APIs: init downloads signed providers, then mock plans.
# No plan against real accounts, apply, login, or resource creation occurs here.
cd "$(dirname "$0")"
root=$(pwd)
engine='hashicorp/terraform:1.13.5@sha256:6bbb82d575aa7bd4f0a2c6e3a0838ab9590426c08a71d7a2783643f01004d356'
mkdir -p evidence
for cloud in gcp aws azure oci; do
  docker run --rm -v "$root/$cloud:/infra" -w /infra "$engine" init -backend=false -input=false -lockfile=readonly -no-color >"evidence/$cloud-init.log" 2>&1
  docker run --rm -v "$root/$cloud:/infra" -w /infra "$engine" fmt -check -recursive -no-color >"evidence/$cloud-format.log" 2>&1
  docker run --rm -v "$root/$cloud:/infra" -w /infra "$engine" validate -no-color >"evidence/$cloud-validate.log" 2>&1
  docker run --rm -v "$root/$cloud:/infra" -w /infra "$engine" test -no-color >"evidence/$cloud-test.log" 2>&1
  echo "PASS: $cloud format, provider schema, and mocked configuration guardrails (not deployed)"
done
