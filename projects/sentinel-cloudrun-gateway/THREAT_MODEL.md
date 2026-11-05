# SENTINEL threat model

Status: local synthetic demonstration. Scope does not include production identity, a deployed cloud boundary, or resistance to compromised host/database administrators.

## Protected assets and actors

Assets: customer-record fields, tenant membership, permitted tool actions, approvals, capability secrets and nonces, idempotency state, audit records and evaluation artifacts. Actors: authenticated agent/user, tenant administrator, untrusted document author, gateway process, database, local operator.

The attacker may control user requests, retrieved documents, model output/tool-call proposals, a tenant user token, HTTP body encoding, timing and request concurrency. They may try to alter tenant/resource IDs, call unknown tools, substitute arguments after approval, replay capabilities, or use another actor's approval. The demonstration assumes the gateway process, local host and PostgreSQL service are not compromised. Local demo tokens are known fixtures; no real data or production authority is present.

## Authorization invariants

1. Actor and tenant come only from gateway-recognized identity configuration, not tool arguments.
2. Tool allowlist, strict argument schema, per-request size, identifier and note bounds, and per-actor rate limit are enforced server-side.
3. Customer queries always include the authenticated tenant. Unknown and foreign resources do not return record content.
4. An update proposal creates a pending action; only a tenant admin can approve. The approval record retains the original payload and record version.
5. A signed short-lived capability binds approval id, actor, tenant, canonical action digest, expected record version, expiry and unique nonce. Execution accepts no caller-supplied action body.
6. The owner must present the capability. Execution locks the approval and record, checks state/expiry/version, updates and consumes the approval, writes idempotency and audit rows in one database transaction.
7. Repeated idempotency key for the same actor/tenant/approval returns the original response. A second key cannot spend an already consumed capability.
8. Retrieved text is labeled untrusted; it cannot set identity, tenant, policy or approval. The deterministic demo returns the poisoned document and separately uses only the user-proposed exact action.
9. Denied authenticated actions and recognized-identity malformed/oversized requests are recorded in that tenant's audit chain. Requests with missing/unknown credentials have no verified tenant and are not attributed to one.

## Audit integrity and assumptions

Events are appended by application code and linked per tenant using SHA-256 over a canonical serialization, with a PostgreSQL advisory lock serializing appends. Verification checks the tenant's full retained chain. This detects content/order edits unless an attacker can rewrite all events and the trusted head together. The current head is stored in the same database; there is no external anchor, WORM store, signature service or privileged DBA exclusion. The chain is not tamper-proof. The local database is ephemeral and not a production audit archive.

## Reversible updates

Execution returns the prior note and includes it in the audit event. Restoration is a new update proposal against the current version and requires a new independent approval. This preserves the same boundary on the reverse action and prevents an old snapshot from silently overwriting newer data.

## Out of scope

Host/root compromise, database superuser collusion, stolen signing key, malicious authorized approver, allowed-output data exfiltration, denial of service beyond the local request/rate bounds, model reliability, unknown dependency defects, prompt-injection detection efficacy, production OIDC/JWT correctness, cloud IAM/network design, external storage retention, backup recovery and deployment rollback.
