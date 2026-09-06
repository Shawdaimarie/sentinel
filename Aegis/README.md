# Aegis

**Zero-trust authorization gateway for AI agents and MCP-compatible tools.**

Aegis is a standalone Go reference service in the Sentinel repository. It
answers one security question before a tool call executes:

> Is this workload identity allowed to use this tool, action, and resource now?

The answer is fail-closed. Missing identity, invalid signatures, stale policy
hashes, replayed capabilities, revoked principals, missing approval, exhausted
rate limits, state-store failure, and audit failure all deny the request.

## What Shipped

- Ed25519 JWT capability verification with JWKS-compatible public keys.
- OIDC discovery and JWKS endpoints for integrating with existing identity
  plumbing.
- SPIFFE-compatible workload identity parsing for `spiffe://` subjects.
- Deny-by-default policy matching across subject, trust domain, tool, action,
  and resource.
- Policy hash binding so stale capabilities fail after policy changes.
- Separate signed human-approval JWTs for approval-required actions.
- Atomic replay protection and revocation interfaces for shared state stores.
- Key rotation and key revocation support.
- State-backed fixed-window rate limits by workload, tool, and action.
- Hash-chained decision audit records.
- OpenTelemetry-shaped decision events with W3C `traceparent` propagation.
- Bounded HTTP server defaults for method, content type, body size, headers,
  read/write timeout, and safe listen address.
- Failure-injection tests for state-store unavailability.
- Policy evaluation harness and benchmark smoke test.
- Non-root static container image and CI gates for Go format, vet, race tests,
  build, benchmark smoke, Docker, and CodeQL.

## Quick Start

```bash
cd Aegis
go test -race ./...
go run ./cmd/aegis-policy-eval \
  --policy examples/policy.json \
  --cases examples/policy_eval_cases.json
go build -trimpath -ldflags="-s -w -buildid=" ./cmd/aegis
```

The public `examples/jwks.json` contains only a synthetic public key for server
startup shape. It cannot sign capabilities. Real deployments must load public
keys from a trusted issuer or workload identity provider and keep private keys
outside the authorizer.

## HTTP API

Start the service:

```bash
go run ./cmd/aegis \
  --policy examples/policy.json \
  --jwks examples/jwks.json \
  --listen 127.0.0.1:8080
```

Authorize a signed capability:

```http
POST /v1/authorize
Content-Type: application/json
Traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

{
  "token": "<signed capability jwt>",
  "approval_token": "<optional signed approval jwt>"
}
```

Responses include the decision, reason, audit sequence/hash, trace identifiers,
and an OpenTelemetry-shaped decision event.

## Production Boundary

Aegis is a reference authorization layer, not a full identity provider, OAuth
authorization server, SPIRE deployment, HSM, SIEM, or globally replicated
database. Production use requires:

- a trusted OIDC or workload-identity issuer;
- managed JWKS rotation and emergency key removal;
- an atomic distributed state adapter such as Redis, DynamoDB, Spanner, or etcd
  for replay, revocation, and rate-limit reservations;
- external append-only audit storage and digest anchoring;
- collector-backed OpenTelemetry export;
- mTLS/network policy around the authorizer;
- operational SLOs, alerting, and break-glass procedures; and
- independent security review before consequential tool access.

See [Architecture](docs/ARCHITECTURE.md), [Threat Model](docs/THREAT_MODEL.md),
and [Runbook](docs/RUNBOOK.md).
