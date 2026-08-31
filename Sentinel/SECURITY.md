# Security

This document defines Sentinel's security objectives, the adversary it is designed to withstand, the trust boundaries it enforces, the controls that enforce them, and the residual risk that remains. It is written to be read by a security reviewer before deployment and by a contributor before changing anything that touches a boundary.

Every control listed under *Controls* has a corresponding test in `tests/test_security.py`. A control without a test is a claim, not a control.

The audit-chain format and verification algorithm are specified language-neutrally in [sentinel-spec](https://github.com/Shawdaimarie/sentinel-spec), with conformance vectors and independent verifiers in Python, TypeScript, and Go. Sentinel's CI checks that its own digests agree with those vectors.

---

## 1. Security objectives

In priority order:

1. **Integrity of the audit record.** Every action an agent takes — permitted or denied — is recorded before it executes, and the record cannot be altered or removed without detection.
2. **Containment of agent action.** No agent can act outside the boundaries declared in `policy.yaml`, and the boundaries in force during a run are themselves recorded.
3. **Isolation from the monitored surface.** Content retrieved from the monitored domain is treated as untrusted input and cannot redirect, expand, or subvert agent behaviour.
4. **Least privilege in the build and delivery pipeline.**

Confidentiality of retrieved content is *not* an objective: Sentinel reads public surfaces.

## 2. Adversary model

Sentinel is designed to withstand an adversary who:

- Controls any content on the monitored domain, including pages, headers, redirects, and linked evidence;
- Controls DNS responses for the monitored domain or any evidence host;
- Can read the audit log and policy file on disk, and can rewrite the audit log file (but does not hold the audit key);
- Can submit pull requests to this repository.

It is **not** designed to withstand an adversary who has arbitrary code execution on the host running Sentinel, who holds the audit key, or who has write access to `policy.yaml` in a deployed environment. See §6.

## 3. Trust boundaries

```
   ┌─────────────────────────── host ───────────────────────────┐
   │                                                            │
   │   policy.yaml ──► Policy engine ◄── every act() ──┐        │
   │   (fingerprinted)        │                        │        │
   │                          ▼ decision               │        │
   │                     Audit log ◄────────────────── Agents   │
   │                  (HMAC-SHA256 chain)               │        │
   │                          ▲                        │        │
   │   SENTINEL_AUDIT_KEY ────┘              governed_get()     │
   └────────────────────────────────────────────┼───────────────┘
                                                │  B1
                              ┌─────────────────▼──────────────────┐
                              │ monitored domain and evidence hosts │
                              │        (untrusted content)         │
                              └─────────────────┬──────────────────┘
                                                │  B2 (optional)
                              ┌─────────────────▼──────────────────┐
                              │        LLM provider (Claude)        │
                              └────────────────────────────────────┘
```

- **B1 — network.** All content crossing B1 inward is untrusted data. All requests crossing B1 outward pass policy evaluation, including each redirect hop.
- **B2 — model.** Content sent across B2 is fenced and length-bounded; the model's response is constrained to a verdict token and cannot upgrade a claim that lacks a source.
- **Audit key.** Held outside the host. Its absence downgrades the log to a plain hash chain, which `verify-audit` reports explicitly. A verifier that holds a key refuses unkeyed records: a log is entirely keyed or entirely unkeyed, and the record never chooses the algorithm that verifies it.

## 4. Threat analysis (STRIDE)

| Category | Threat | Control | Test |
|---|---|---|---|
| **Spoofing** | Lookalike host (`example.com.evil.io`) passes domain check | Suffix match requires a dot boundary | `test_domain_boundary_is_enforced` |
| | DNS rebinding to an internal address | Resolution check rejects non-global addresses; unresolvable hosts denied | `test_private_address_resolution_is_denied`, `test_loopback_and_link_local_are_denied`, `test_unresolvable_host_is_denied` |
| **Tampering** | Audit record altered or deleted | Hash chain; sequence check; `verify-audit` | `test_content_tampering_is_detected`, `test_deletion_is_detected` |
| | Audit chain re-computed after rewrite | HMAC-SHA256 with external key; re-chaining without the key fails verification | `test_keyed_chain_cannot_be_rechained_without_key` |
| | `keyed` flag flipped to false and chain recomputed with plain SHA-256 | Verifier holding a key rejects any unkeyed record (downgrade refused) | `test_keyed_verifier_rejects_downgrade_to_unkeyed` |
| | Policy substituted between review and run | Policy SHA-256 recorded at run start; `--policy-sha256` refuses a mismatch | `test_policy_fingerprint_pinning` |
| **Repudiation** | Agent acts without a record | `Agent.act` writes the decision before dispatch; no other execution path | `test_allowed_action_is_logged_then_executed`, `test_denied_action_is_logged_and_raises` |
| **Information disclosure** | Reporter writes outside `reports/` | Path prefix and traversal checks; absolute paths denied | `test_path_traversal_is_denied`, `test_reporter_writes_only_within_allowed_path` |
| | Credentials leaked via URL | URLs with userinfo denied | `test_credentials_in_url_are_denied` |
| **Denial of service** | Unbounded requests per run | Per-agent per-run budgets; denials do not consume budget | `test_per_run_budget_is_enforced`, `test_denied_actions_do_not_consume_budget` |
| | Redirect loop | Hop limit of 5 | `test_redirect_loop_is_bounded` |
| | Oversized or binary response | 2 MiB body limit; textual content types only | `test_non_textual_content_is_rejected` |
| **Elevation of privilege** | Redirect from allowed host to foreign host | Redirects not followed automatically; each hop is a policy-evaluated action | `test_redirect_to_foreign_host_is_denied_and_logged` |
| | Non-HTTP scheme (`file:`, `ftp:`) | Scheme allow-list | `test_non_http_schemes_are_denied` |
| | Prompt injection via crawled content | Source fenced and truncated; delimiter collisions neutralised; output constrained; absent source cannot be overridden | `test_verifier_prompt_fences_untrusted_source` |
| | Undeclared agent or action | Default deny | `test_default_is_deny_for_undeclared_agent`, `test_action_outside_allowed_set_is_denied` |

## 5. Controls in the delivery pipeline

- **Workflow permissions** are `contents: read` by default; CodeQL is granted `security-events: write` only.
- **Static analysis**: `ruff`, `mypy --strict`, and CodeQL on every push and pull request, and weekly on schedule.
- **Dependency audit**: `pip-audit` on every push; Dependabot for pip and GitHub Actions weekly.
- **Type strictness** is a security control here: the policy engine's inputs and outputs are typed, and `mypy --strict` rejects untyped paths into it.

## 6. Residual risk and production hardening

The following are *not* mitigated by this repository and must be addressed by the deployment.

| Risk | Required mitigation |
|---|---|
| Deletion of the entire audit file, or truncation of its tail | Ship records to append-only external storage (object lock, transparency log, or a WORM sink) as they are written. The chain alone cannot detect removal of trailing records; see [sentinel-spec §5.2](https://github.com/Shawdaimarie/sentinel-spec/blob/main/SPEC.md) |
| Compromise of the audit key | Store in a secrets manager or HSM; rotate; never on the writing host's disk |
| Modification of `policy.yaml` in place | Version-control the policy; require review; sign it and pin the fingerprint in the deployment |
| Host compromise | Run in a minimal, non-root container with no outbound egress except to declared domains and the LLM provider; read-only filesystem except `reports/` and the audit sink |
| Extraction blind spots | Claims without digits, or presented in images, are not examined; treat coverage as partial |
| Evidence authority | *Supported* means the quantity appears in a linked page, not that the page is authoritative; evidence-quality assessment is future work |
| LLM misjudgement | The model can produce a false *supported* on paraphrased claims; its rationale is logged for review; disable `--llm` where this is unacceptable |

## 7. Supported versions

| Version | Supported |
|---|---|
| `main` | Yes |
| Tagged releases < 1.0 | Latest minor only |

## 8. Reporting a vulnerability

Open a **private security advisory** on this repository (Security → Advisories → Report a vulnerability). Do not open a public issue.

Commitments:

- Acknowledgement within **3 business days**.
- Initial assessment and severity (CVSS 3.1) within **10 business days**.
- Fix or documented mitigation for High and Critical findings within **30 days** of assessment; coordinated disclosure thereafter.
- Credit in the advisory and release notes unless anonymity is requested.

Findings in this reference implementation that would apply to any deployment built on it are in scope. Findings that require an adversary outside §2 are welcome but will be recorded as residual risk rather than fixed.
