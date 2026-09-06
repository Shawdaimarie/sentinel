# Aegis Architecture

## Goal

Aegis adds a zero-trust authorization control plane beside Sentinel's governed
execution and evaluation system. Sentinel records and evaluates what agents do;
Aegis decides whether a workload has authority to attempt a tool action at all.

## Data Flow

```text
OIDC/SPIFFE issuer ──► Ed25519 JWT capability ─┐
                                                │
human approval issuer ─► signed approval JWT ───┤
                                                ▼
                                      Aegis /v1/authorize
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       ▼                        ▼                        ▼
             issuer-scoped JWKS         deny-by-default policy       shared state
                verification            + policy hash binding       replay/revoke/rate
                       └────────────────────────┬────────────────────────┘
                                                ▼
                                  audit record + OTel event
                                                │
                                                ▼
                                          allow or deny
```

## Components

### JWT and JWKS

`internal/aegis/jwt.go` verifies compact JWTs signed with Ed25519 (`EdDSA`).
`internal/aegis/keys.go` loads OKP Ed25519 JWKS documents, validates
issuer-scoped trust bundles, publishes non-revoked public keys, rotates active
signing keys in tests and tooling, and rejects revoked keys. Verification first
uses the untrusted `iss` claim only as a selector into the configured trusted
issuer set; a token whose issuer is not the active policy issuer is denied
before policy evaluation. Duplicate issuers, duplicate `kid` values, empty
JWKS documents, non-signature keys, and non-HTTPS issuer metadata fail at load
time. Revoked keys are removed from the public JWKS response and denied during
verification.

### Workload Identity

`types.go` accepts OIDC-style `iss`, `aud`, and `sub` claims and extracts
SPIFFE-compatible identities when either `sub` or `spiffe_id` is a
`spiffe://trust-domain/path` URI. A malformed SPIFFE URI denies the request.
When both `sub` and `spiffe_id` are SPIFFE URIs, they must match exactly so a
token cannot present one subject while widening policy matching through another
SPIFFE identity.

### Policy Engine

`policy.go` matches workload identity, SPIFFE trust domain, tool, action, and
resource against explicit rules. Only exact matches and bounded trailing
wildcards are supported. The most specific rule wins, and deny wins ties.
Absence of a matching allow rule denies the request.

### Replay, Revocation, and Rate State

`state.go` defines the production contract: state stores must provide atomic JTI
reservation, revocation checks, and rate-limit reservations. The memory
implementation is used for tests; the file-backed implementation records durable
JSONL events for local reference runs, including quota reservations that survive
restart. Multi-instance production deployments should replace it with a true
distributed compare-and-set store so replay, revocation, and rate limits are
consistent across replicas.

### Authorization Path

`authorizer.go` performs checks in fail-closed order:

1. required configuration exists;
2. shared state is healthy;
3. token issuer is trusted for the active policy and the capability signature
   and key status are valid;
4. issuer, audience, expiry, not-before, JTI, and scope are valid;
5. workload identity is syntactically valid;
6. subject is not revoked;
7. capability policy hash matches the active policy;
8. the active policy allows the requested scope;
9. TTL is within policy;
10. matching signed approval exists when required;
11. rate limit quota is reserved through state;
12. capability JTI is atomically reserved; and
13. decision audit append succeeds.

Any failure returns a denial reason and appends a decision record when the audit
sink is available. Audit unavailability denies.

### Observability

`observability.go` parses W3C `traceparent` headers or creates fresh trace/span
IDs. Each authorization result includes an OpenTelemetry-shaped event named
`aegis.authorization.decision` with decision, reason, policy, key, workload,
tool, action, resource, and SPIFFE attributes.

### HTTP Surface

`http.go` exposes:

- `GET /.well-known/openid-configuration`
- `GET /jwks.json`
- `POST /v1/authorize`

The server applies bounded headers, body size, read/write timeouts, strict JSON
decoding, method checks, content-type checks, and `127.0.0.1:8080` as the safe
default listen address.

`cmd/aegis` accepts either `--jwks` for the local single-issuer reference path
or `--trust-bundle` for issuer-scoped verifier configuration. `--check-config`
loads policy, verifier keys, state, and audit configuration, then exits before
serving traffic.

## Decision Record

Every authorization decision can be represented as:

- subject and SPIFFE trust domain;
- requested tool, action, and resource;
- matched rule;
- signing key ID;
- active policy hash;
- trace ID and span ID;
- sequence number;
- previous hash; and
- current record hash.

The local hash chain detects retained-record modification, middle deletion,
reordering, and sequence mutation. It does not prove the log is complete without
external anchoring.
