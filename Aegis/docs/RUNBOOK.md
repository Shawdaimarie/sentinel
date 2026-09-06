# Aegis Runbook

## When To Use

Use this runbook when Aegis denies unexpectedly, allows too broadly, reports
state/audit failures, or needs key/policy rotation.

## Health Checks

1. Confirm the process is serving discovery and JWKS:

   ```bash
   curl -fsS http://127.0.0.1:8080/.well-known/openid-configuration
   curl -fsS http://127.0.0.1:8080/jwks.json
   ```

2. Run the deterministic policy harness:

   ```bash
   go run ./cmd/aegis-policy-eval \
     --policy examples/policy.json \
     --cases examples/policy_eval_cases.json
   ```

3. Run the full verification suite:

   ```bash
   go test -race ./...
   go vet ./...
   go test -run '^$' -bench=. -benchtime=100x ./...
   ```

4. For issuer-scoped verification, confirm the configured trust bundle loads:

   ```bash
   go run ./cmd/aegis \
     --policy examples/policy.json \
     --trust-bundle examples/trust_bundle.json \
     --check-config
   ```

## Unexpected Deny

Check the decision reason in the `/v1/authorize` response and audit log.

Common reasons:

| Reason | Meaning | Action |
|---|---|---|
| `untrusted_issuer` | Token issuer is absent from the configured trusted issuer set or does not match the active policy issuer | Check trust-bundle contents, issuer URL, and JWKS rotation state |
| `unknown_signing_key` | `kid` is absent from JWKS | Confirm issuer rotation and JWKS refresh |
| `revoked_signing_key` | Signing key is explicitly revoked | Reissue capability with current key |
| `invalid_workload_identity` | SPIFFE identity is malformed or conflicts with another SPIFFE identity claim | Reissue token with one canonical workload identity |
| `policy_hash_mismatch` | Capability was minted under another policy | Re-mint after policy review |
| `approval_required` | Rule requires a signed approval JWT | Attach a matching approval token |
| `approval_scope_mismatch` | Approval does not bind this capability and scope | Reissue approval for this exact request |
| `replay_detected` | JTI was already consumed | Re-mint a new short-lived capability |
| `rate_limited` | Workload exceeded policy rate in shared state | Wait for reset or review rule limits |
| `state_unavailable` | Replay/revocation/rate state is unhealthy | Keep fail-closed; repair state service |
| `audit_unavailable` | Decision evidence could not be appended | Keep fail-closed; repair audit sink |

## Emergency Revocation

1. Revoke the compromised capability JTI in the distributed state store.
2. Revoke the subject if all outstanding capabilities for a workload must fail.
3. Remove the compromised key from JWKS and mark it revoked in the verifier key
   set.
4. Watch for `unknown_signing_key`, `revoked_signing_key`, and deny-rate spikes.
5. Reissue capabilities only after policy and workload identity review.

## Key Rotation

1. Add the new public key to JWKS before using it to sign.
2. Publish the updated issuer-scoped trust bundle or JWKS source.
3. Rotate signing to the new `kid`.
4. Keep the previous key available only until its last valid token expires.
5. Mark the previous key retired, then revoke/remove it after the overlap.
6. For emergency compromise, skip the overlap and revoke immediately.

## Trust-Bundle Rotation

1. Validate the issuer URL is the intended HTTPS issuer.
2. Reject duplicate issuer entries and duplicate `kid` values before rollout.
3. Deploy new public keys before signing capabilities with them.
4. Remove old keys only after their last valid capability expires, unless this
   is an emergency revocation.
5. Monitor `untrusted_issuer`, `unknown_signing_key`, and
   `revoked_signing_key` denials during the overlap.

## Policy Rotation

1. Review the JSON policy diff.
2. Run the policy evaluation harness.
3. Record the new policy hash.
4. Deploy the policy.
5. Re-mint capabilities with the new `policy_hash`.
6. Monitor `policy_hash_mismatch` denials for stale clients.

## Rollback

Prefer forward-fixing authorization policy. If rollback is necessary:

1. Confirm rollback policy hash and intended access boundary.
2. Deploy previous reviewed policy.
3. Re-mint capabilities against the rollback hash.
4. Keep replay/revocation state; do not clear it to restore access.
5. Document the incident and update evaluation cases if a missed scenario caused
   the rollback.

## Escalation

Escalate before re-enabling access if:

- state or audit failures continue after one retry window;
- a production signing key may be compromised;
- an allow decision matched an unintended rule;
- approval-required actions allowed without human approval; or
- audit logs cannot be reconciled with external anchors.
