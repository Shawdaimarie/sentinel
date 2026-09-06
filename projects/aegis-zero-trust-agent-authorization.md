# Aegis: Zero-Trust Agent Authorization

## Portfolio Summary

Aegis is a Go reference authorization gateway for AI agents and MCP-compatible
tools. It verifies short-lived Ed25519 JWT capabilities against
JWKS-compatible public keys, parses SPIFFE-compatible workload identities,
enforces deny-by-default policy, requires separately signed human approvals for
consequential actions, blocks replay through stateful JTI reservation, supports
key rotation and revocation, rate-limits workloads, and records each decision
with audit and OpenTelemetry-shaped evidence.

## Shipped Evidence

- Standalone Go module under `Aegis/`.
- OIDC discovery and JWKS HTTP endpoints.
- `/v1/authorize` endpoint with strict method, content type, body-size, header,
  timeout, and safe-listen defaults.
- Deny-by-default policy engine with exact and bounded trailing-wildcard
  matching.
- Policy hash binding for invalidating stale capabilities.
- Replay/revocation state interface with memory and file-backed reference
  implementations.
- Signed approval-token binding to capability JTI, capability hash, subject,
  tool, action, resource, and policy hash.
- Key rotation and revoked-key denial.
- Fixed-window rate limiting by subject, tool, and action.
- Hash-chained decision audit records.
- OpenTelemetry-shaped authorization decision events and W3C `traceparent`
  propagation.
- Security tests and benchmark smoke coverage in `Aegis/internal/aegis/`.
- GitHub Actions workflow for Go format, vet, race tests, policy harness,
  benchmark smoke, static build, non-root container build, and binary evidence.
- CodeQL expanded to analyze Go as well as Python.
- Architecture, threat model, and runbook documentation.

## Resume-Ready Language

Built Aegis, a Go zero-trust authorization gateway for AI agents and
MCP-compatible tools, with Ed25519 JWT/JWKS verification, SPIFFE-compatible
workload identity, policy-hash-bound capabilities, signed human approvals,
replay/revocation state, key rotation, rate limiting, hash-chained audit
records, OpenTelemetry-shaped decision events, race-tested security coverage,
CodeQL, and non-root container CI.

## Boundaries

Aegis is not a production identity provider, SPIRE deployment, HSM, SIEM, or
globally distributed database. Production use still requires trusted
OIDC/SPIFFE issuer integration, KMS/HSM key custody, atomic distributed
replay/revocation storage, external audit anchoring, collector-backed telemetry,
mTLS/network policy, and independent security review.
