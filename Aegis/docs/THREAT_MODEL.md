# Aegis Threat Model

## Security Objectives

1. Verify workload identity before tool access.
2. Enforce least privilege for subject, trust domain, tool, action, and resource.
3. Deny expired, malformed, tampered, replayed, revoked, or stale-policy
   capabilities.
4. Require a separately signed approval for consequential actions.
5. Preserve decision evidence for review and incident response.
6. Fail closed when state, audit, policy, key, or observability context is not
   trustworthy.

## Trust Boundaries

```text
workload / MCP client ── signed capability ──► Aegis
human approval system ─ signed approval JWT ─► Aegis
OIDC/JWKS issuer ───── public verification ──► Aegis
distributed state ─── replay/revoke checks ──► Aegis
audit/telemetry sinks ◄── decision evidence ── Aegis
```

## STRIDE Analysis

| Category | Threat | Control | Evidence |
|---|---|---|---|
| Spoofing | A caller invents a subject or SPIFFE ID | Ed25519 JWT verification plus issuer/audience checks | `TestPolicyDriftTamperExpiryAndScopeEscalationDeny` |
| Spoofing | Malformed SPIFFE URI bypasses trust-domain policy | Strict `spiffe://` parsing, no query/fragment/traversal | `TestSPIFFEValidationRejectsMalformedIdentity` |
| Tampering | Capability scope is edited after signing | Signature verification over header and claims | tamper test |
| Tampering | Stale capability survives policy change | Capability embeds active policy SHA-256 | policy-drift test |
| Repudiation | Allow/deny happens without evidence | Decision audit append before returning allow | replay/audit assertions |
| Information disclosure | Public example contains private key material | Example JWKS is public-key-only and cannot sign tokens | repository fixture |
| Denial of service | Caller floods tool authorization | Per workload/tool/action fixed-window limits | rate-limit test |
| Denial of service | Oversized or ambiguous HTTP input consumes resources | body, header, timeout, content-type, and JSON limits | HTTP bounds test |
| Elevation of privilege | Approval for one capability is reused for another | Approval binds capability JTI, hash, subject, tool, action, resource, and policy hash | approval mismatch test |
| Elevation of privilege | Used or revoked capability is replayed | State store reserves JTI atomically and checks revocation | replay/revocation tests |
| Elevation of privilege | Compromised key continues to authorize | Revoked keys are denied and removed from JWKS | key revocation test |

## Residual Risk

Aegis does not yet include a production OIDC issuer, SPIRE server, cloud KMS/HSM,
SIEM integration, or distributed database adapter. The reference file state
store is useful for local runs but is not a multi-process distributed lock. A
production deployment must use an atomic compare-and-set state service and must
deny on timeout or consistency errors.

Audit hashes detect mutation of retained records, not deletion of the entire
log or tail truncation. Production deployments must stream records to external
append-only storage and anchor terminal digests.

The OpenTelemetry-shaped event in the reference response is not a collector
exporter. Production deployments should export spans/logs through the official
OpenTelemetry SDK and collector with alerting on deny spikes, state failures,
audit failures, and unknown key IDs.

The reference service verifies authorization evidence; it does not prove that an
AI agent's output is correct or safe. Sentinel evaluation gates remain necessary
for behavior-level assurance.
