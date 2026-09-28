# Claims and evidence register

Every major public claim about Sentinel, with its scope, supporting test,
evidence, owner, limitation, and status. Sources: the repository README, the
Sentinel README, and the owner's GitHub profile.

**Status** uses four levels. A claim only rises to a level when its evidence
is linked.

- **Planned**: intended, not built.
- **Implemented**: code exists, but no test demonstrates the claim.
- **Tested**: an automated test demonstrates the claim in CI.
- **Observed in production**: demonstrated in a real deployment with
  operational evidence.

No claim is currently *observed in production*: Sentinel has no production
deployment or pilot (plan step 16).

CI evidence: [CI run 36326317950](https://github.com/Shawdaimarie/sentinel/actions/runs/36326317950)
on commit `822917d`, dated 2026-09-27. Owner of every row: @Shawdaimarie.
Last reviewed: 2026-09-27.

| ID | Claim | Scope | Supporting test | Evidence | Limitation | Status |
|---|---|---|---|---|---|---|
| C1 | Deny-by-default policy: nothing is permitted by omission | `policy.py`: agents, actions, budgets, domains, path prefixes | `tests/test_policy.py`, `tests/test_agents.py` | CI run above | Correctness depends on the policy the operator writes | Tested |
| C2 | Every action is audited *before* it runs | `Agent.act()` | `tests/test_agents.py`, `tests/test_audit.py` | CI run above | No test injects an audit-write failure to prove the action is then skipped; the behavior follows from call order only | Tested (ordering); audit-failure path **Implemented** |
| C3 | Audit chain detects modification, reordering, gaps, and keyed-to-unkeyed downgrade | Retained records | `tests/test_audit.py`, `tests/test_portable_spec.py` | CI run above | Does not detect tail truncation or deletion of the whole log without external anchoring | Tested |
| C4 | Governed network access: every redirect hop is re-checked; private, loopback, and link-local targets are refused | `http.py` | `tests/test_security.py` (including `test_private_address_resolution_is_denied`) | CI run above | The name is resolved during the policy check (`policy.py:74`), and the HTTP client resolves it again when connecting. A DNS answer that changes between the two (rebinding) is neither prevented nor tested. Tracked for plan step 11. | Tested (check-time resolution only) |
| C5 | OTLP JSON becomes strict `AgentRun` records with a provenance manifest | Supported semantic-convention subset | `tests/test_trace_import.py` | CI run above; [Trace Import run 36326317924](https://github.com/Shawdaimarie/sentinel/actions/runs/36326317924) | Subset of conventions; provider adapters are planned (#11) | Tested |
| C6 | Malformed IDs, cycles, ambiguous roots, and invented completeness fail closed | Trace importer | `tests/test_trace_import.py` | CI run above | Bounded input size is proposed in open PR #37, not merged | Tested |
| C7 | Configurable redaction of sensitive trace metadata | Configured keys and bounded unknown metadata | `tests/test_trace_import.py` | CI run above | Redacts configured keys, not arbitrary personal data in free text | Tested |
| C8 | Training examples are checked for schema, source, privacy, splits, and risk coverage | `data_gate.py` | `tests/test_data_gate.py` | CI run above | Checks declared metadata; does not inspect content for personal data | Tested |
| C9 | Hard safety gates cannot be outweighed by a good aggregate score; paired baseline regression | `evaluation.py` | `tests/test_evaluation.py` | CI run above | Deterministic assertions only; semantic quality needs calibrated human review (#13) | Tested |
| C10 | Audit verification in independent Python, TypeScript, and Go implementations sharing vectors | Portable profile | Portable audit conformance job | CI run above | Verifies the portable profile, not every writer configuration | Tested |
| C11 | Delivery discipline: Python 3.11 and 3.12, Ruff, strict mypy, pytest, pip-audit, CodeQL, Docker | CI | `ci.yml`, `codeql.yml` | CI run above; [CodeQL run 36326317936](https://github.com/Shawdaimarie/sentinel/actions/runs/36326317936) | One CodeQL alert is open ([#1](https://github.com/Shawdaimarie/sentinel/security/code-scanning/1)) | Tested |
| C12 | PostgreSQL evaluation history with role-separated credentials, migrations, and restore | `history` extra | `tests/test_history.py`, `tests/test_history_postgres.py` | `evaluation-history` job in the CI run above | Against a disposable CI database; no deployed instance | Tested |
| C13 | Released images are signed, vulnerability-gated, and verifiable | `release.yml` | `tests/test_release_workflow.py` | [Release run 36326317967](https://github.com/Shawdaimarie/sentinel/actions/runs/36326317967) **failed** at the gate; nothing published | The pipeline logic is tested, but no signed image exists yet | Implemented; end-to-end **unverified** (plan steps 6 and 7) |
| C14 | `scripts/verify-image.sh` verifies a published image in one command | Consumer verification | `tests/test_verify_image_script.py` | CI run above | Tested against stubbed `gh` and `docker` only | Tested (offline); live **unverified** |
| C15 | Aegis fails closed on missing identity, bad signatures, stale policy, replay, revocation, missing approval, rate limits, state failure, and audit failure | `Aegis/internal/aegis` | `authorizer_test.go` | [Aegis CI run 36326317969](https://github.com/Shawdaimarie/sentinel/actions/runs/36326317969) | Reference service; no production identity provider integration | Tested |
| C16 | Aegis approvals are separately signed, bound to subject, tool, action, resource, policy hash, and capability; they expire and are single-use | `verifyApproval` | `TestApprovalIsSeparatelySignedAndBoundToCapability` | Aegis CI run above | Arguments are not bound; there is no emergency stop (plan step 10) | Tested |
| C17 | Human-only boundaries (identity, legal, financial, hiring, confidential data, credentials, sensitive distribution) are never approved automatically | `value_router.py` | `tests/test_value_router.py` | CI run above | Classification uses declared item metadata | Tested |
| C18 | Required checks and signed commits protect `main` | Repository governance | `tests/test_release_ruleset.py` (checks that the configuration matches the jobs) | Ruleset API returns `[]` | The ruleset is committed but **not active** | Planned (plan step 5) |
| C19 | "Informed by" NIST AI RMF and OWASP AI Agent Security guidance | Design references | — | `docs/NIST_AI_RMF_CROSSWALK.md` | A design reference, not a compliance or certification claim | Not a verifiable claim (reference only) |
| C20 | Any claim about capacity, latency under load, availability, or user value | — | — | — | Not measured | Planned (plan steps 13–18) |
| C21 | The published images can be run with the commands in the README | Container usage docs | `image-smoke-test` CI job running `scripts/smoke-test-images.sh` (INSTALLING.md) | Found broken during step 7: the documented Aegis command could not start (no policy in the image) and listened only on the container loopback. Replaced by tested commands. | CI runs freshly built images; verification against a *published* digest by another person is pending (#55) | Tested (once the install-guide PR merges); live **unverified** |

## Profile claims

The profile's "Principles, and where they are enforced" table cites C1, C3,
C9, C10, C12, C15, C16, and C17. Its "Current priorities" line on signed
releases corresponds to C13, which is stated there as in progress, not
achieved.

## Maintaining this register

Update this register in the same pull request that changes a claim or its
evidence. A claim whose evidence fails, for example a red CI run or a failed
release, drops to the highest status its remaining evidence supports.
