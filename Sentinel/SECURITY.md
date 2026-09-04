# Security

This document defines Sentinel's security objectives, the adversary it is
designed to withstand, the trust boundaries it enforces, the controls that
enforce them, and the residual risk that remains. It is written for a security
reviewer before deployment and for contributors changing any boundary.

Every control listed under *Controls* has a corresponding test in
`tests/test_security.py`. A control without a test is a claim, not a control.

The audit-chain format and verification algorithm are specified
language-neutrally in the
[`sentinel.audit.v1-portable` profile](spec/SPEC.md), with normative vectors
under [`spec/vectors/`](spec/vectors/) and independent verifiers in Python,
TypeScript, and Go under [`verifiers/`](verifiers/). Sentinel's CI checks that
its own Python implementation and all three independent implementations agree
with those vectors.

---

## 1. Security objectives

In priority order:

1. **Integrity of retained audit records.** Every permitted or denied action is
   recorded before execution, and modification, deletion in the middle,
   reordering, sequence gaps, and keyed-to-unkeyed downgrade are detected.
2. **Containment of agent action.** No agent can act outside the boundaries
   declared in `policy.yaml`, and the policy fingerprint in force is recorded.
3. **Isolation from the monitored surface.** Retrieved content is untrusted and
   cannot expand permissions, redirect outside policy, or subvert control flow.
4. **Least privilege in the build and delivery pipeline.**
5. **Independent audit verification.** Audit evidence can be checked without
   trusting Sentinel's writer implementation or Python runtime.

Completeness of the audit stream is not established by the chain alone. Tail
truncation or deletion of the entire file requires external digest anchoring;
see §6 and the portable profile's production boundary.

Confidentiality of retrieved content is *not* an objective: Sentinel reads
public surfaces.

## 2. Adversary model

Sentinel is designed to withstand an adversary who:

- controls any content on the monitored domain, including pages, headers,
  redirects, and linked evidence;
- controls DNS responses for the monitored domain or an evidence host;
- can read the audit log and policy file on disk and rewrite the audit file,
  but does not hold the audit key;
- can submit pull requests to the repository; or
- attempts to substitute an unkeyed chain for a keyed chain.

It is **not** designed to withstand an adversary who has arbitrary code
execution on the host running Sentinel, holds the audit key, can change the
reviewed policy in a deployed environment, controls every external audit
anchor, or can suppress the complete log before anchoring. See §6.

## 3. Trust boundaries

```text
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
                              │        (untrusted content)           │
                              └─────────────────┬──────────────────┘
                                                │  B2 (optional)
                              ┌─────────────────▼──────────────────┐
                              │        LLM provider (Claude)        │
                              └─────────────────────────────────────┘

 audit JSONL ──► Python verifier ─┐
                TypeScript verifier ├─► same normative final digest
                Go verifier ───────┘
```

- **B1 — network.** All content crossing B1 inward is untrusted data. All
  requests crossing B1 outward pass policy evaluation, including each redirect
  hop.
- **B2 — model.** Content sent across B2 is fenced and length-bounded; the
  model's response is constrained to a verdict token and cannot upgrade a
  claim that lacks a source.
- **Audit key.** Held outside the host. Its absence downgrades the log to a
  plain hash chain, which `verify-audit` reports explicitly. A verifier holding
  a key refuses every unkeyed record; the record never chooses the algorithm
  that the verifier trusts.
- **Independent verifiers.** Python, TypeScript, and Go implementations consume
  the same portable profile and normative vectors. Agreement reduces
  implementation coupling but does not establish log completeness.

## 4. Threat analysis (STRIDE)

| Category | Threat | Control | Test or evidence |
|---|---|---|---|
| **Spoofing** | Lookalike host (`example.com.evil.io`) passes domain check | Suffix match requires a dot boundary | `test_domain_boundary_is_enforced` |
| | DNS rebinding to an internal address | Resolution check rejects non-global addresses; unresolvable hosts denied | `test_private_address_resolution_is_denied`, `test_loopback_and_link_local_are_denied`, `test_unresolvable_host_is_denied` |
| **Tampering** | Audit record altered or deleted in the middle | Hash chain, sequence check, `verify-audit` | `test_content_tampering_is_detected`, `test_deletion_is_detected` |
| | Audit chain recomputed after rewrite | HMAC-SHA256 with an external key | `test_keyed_chain_cannot_be_rechained_without_key` |
| | `keyed` flipped to false and chain recomputed with SHA-256 | Verifier holding a key rejects any unkeyed record | `test_keyed_verifier_rejects_downgrade_to_unkeyed` and portable conformance tests |
| | Writer implementation disagrees with the documented format | Normative vectors checked by Sentinel plus independent Python, TypeScript, and Go verifiers | `test_portable_spec.py` and `portable-audit-conformance` CI job |
| | Policy substituted between review and run | Policy SHA-256 recorded; `--policy-sha256` refuses mismatch | `test_policy_fingerprint_pinning` |
| **Repudiation** | Agent acts without a record | `Agent.act` writes the decision before dispatch; no other execution path | `test_allowed_action_is_logged_then_executed`, `test_denied_action_is_logged_and_raises` |
| **Information disclosure** | Reporter writes outside `reports/` | Path prefix and traversal checks; absolute paths denied | `test_path_traversal_is_denied`, `test_reporter_writes_only_within_allowed_path` |
| | Credentials leaked through URL userinfo | URLs with userinfo denied | `test_credentials_in_url_are_denied` |
| **Denial of service** | Unbounded requests per run | Per-agent budgets; denials do not consume budget | `test_per_run_budget_is_enforced`, `test_denied_actions_do_not_consume_budget` |
| | Redirect loop | Hop limit of five | `test_redirect_loop_is_bounded` |
| | Oversized or binary response | 2 MiB body limit; textual content types only | `test_non_textual_content_is_rejected` |
| **Elevation of privilege** | Redirect from allowed to foreign host | Redirects are manual; every hop is evaluated | `test_redirect_to_foreign_host_is_denied_and_logged` |
| | Non-HTTP scheme (`file:`, `ftp:`) | Scheme allow-list | `test_non_http_schemes_are_denied` |
| | Prompt injection through crawled content | Source fenced and truncated; delimiter collisions neutralized; output constrained; absent source cannot be overridden | `test_verifier_prompt_fences_untrusted_source` |
| | Undeclared agent or action | Default deny | `test_default_is_deny_for_undeclared_agent`, `test_action_outside_allowed_set_is_denied` |

## 5. Controls in the delivery pipeline

- **Workflow permissions** are `contents: read` by default; CodeQL receives
  `security-events: write` only.
- **Static analysis** runs `ruff`, strict `mypy`, and CodeQL on pushes and pull
  requests; CodeQL also runs weekly.
- **Dependency audit** runs `pip-audit` on every push; Dependabot checks Python
  and GitHub Actions dependencies weekly.
- **Behavioral release gate** executes the versioned agent-evaluation suite and
  rejects safety, pass-rate, or baseline regressions.
- **Portable conformance gate** compiles/runs independent Python, TypeScript,
  and Go verifiers against the same keyed and unkeyed vectors.
- **Container gate** builds a non-root image with bounded registry retries.
- **Diagnostic preservation** uploads reports and logs even when a gate fails.
- **Type strictness** is treated as a security control: strict typing rejects
  untyped paths into the policy and evaluation boundaries.

## 6. Residual risk and production hardening

The following are *not* mitigated by this repository and must be addressed by
the deployment.

| Risk | Required mitigation |
|---|---|
| Deletion of the entire audit file or truncation of its tail | Stream records to independently controlled append-only storage and periodically anchor the final digest; see [`spec/SPEC.md` §8](spec/SPEC.md#8-production-boundary) |
| Compromise of the audit key | Store it in a secrets manager or HSM, limit use, rotate through an explicit chain boundary, and never write it to the audit host's disk |
| Modification of `policy.yaml` in place | Version-control and review policy, sign it, and pin its fingerprint in deployment |
| Host compromise | Run as non-root with minimal filesystem access and outbound egress restricted to declared domains and approved providers |
| Verifier monoculture | Retain cross-language CI and independently review canonicalization changes; do not accept one implementation as the sole oracle |
| Unsupported portable values | Keep payloads inside the safe-integer/no-float profile or version the specification before introducing new value semantics |
| Extraction blind spots | Claims without digits or claims embedded in images are not examined; treat coverage as partial |
| Evidence authority | *Supported* means the quantity appears in a linked page, not that the page is authoritative; add evidence-quality assessment for consequential use |
| LLM misjudgment | A model can incorrectly support a paraphrased claim; log its rationale and disable semantic review where this is unacceptable |
| Evaluation incompleteness | Deterministic cases measure encoded assertions only; add domain-specific red-team cases, repeated trials, calibrated human review, and production monitoring |

## 7. Supported versions

| Version | Supported |
|---|---|
| `main` | Yes |
| Tagged releases below 1.0 | Latest minor only |

## 8. Reporting a vulnerability

Open a **private security advisory** on this repository through Security →
Advisories → Report a vulnerability. Do not open a public issue.

Commitments:

- Acknowledgment within **3 business days**.
- Initial assessment and severity (CVSS 3.1) within **10 business days**.
- Fix or documented mitigation for High and Critical findings within **30 days**
  of assessment, followed by coordinated disclosure.
- Credit in the advisory and release notes unless anonymity is requested.

Findings in this reference implementation that would apply to a deployment are
in scope. Findings requiring an adversary outside §2 are welcome but may be
recorded as residual risk rather than treated as a defect in this reference
implementation.
