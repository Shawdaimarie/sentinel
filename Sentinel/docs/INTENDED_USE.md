# Intended use

What Sentinel and Aegis are for, who should use them, what they must refuse,
and where responsibility sits. A reviewer should be able to use this page to
predict what the system will do and when it will say no.

This page describes the design intent. Where behavior is enforced, it links
the enforcing code or test. Anything described as an assumption has not been
measured.

## Intended users

| User | Uses Sentinel to |
|---|---|
| Engineers building tool-using AI agents | Bound agent actions with declarative policy and record every decision before execution |
| Evaluation and release owners | Gate a candidate agent or model release on deterministic correctness, safety, grounding, latency, cost, and baseline regression |
| Platform and security reviewers | Verify audit chains independently and inspect why an action was allowed or denied |
| Dataset owners preparing post-training work | Block weak, unlabelled, or privacy-sensitive training examples before use |
| Operators of agent-to-tool infrastructure (Aegis) | Decide whether a workload identity may use a tool, action, and resource now |

Sentinel is not intended for end users of an AI product, or for anyone
without the authority to change the policy it enforces.

## Supported workflows

1. **Governed execution.** An orchestrator runs agents (crawler, verifier,
   prober, reporter) under one policy. Every `act()` is checked by the
   [policy engine](../ARCHITECTURE.md#policy-engine-policypy) and written to the
   audit log *before* it runs.
2. **Release evaluation.** `sentinel-eval` scores candidate runs against
   versioned cases and a paired baseline. It fails the release on any hard
   safety failure, whatever the aggregate score.
3. **Trace import.** `sentinel-import-otel` normalizes supported
   OpenTelemetry traces into evaluation records offline and marks incomplete
   traces explicitly.
4. **Evaluation history.** `sentinel-history` stores minimized reports in
   PostgreSQL with separate reader and writer roles, and answers read-only
   queries.
5. **Data gating.** `sentinel-data-gate` checks training examples for schema,
   source notes, privacy posture, and split hygiene.
6. **Value routing.** `sentinel-value-router` classifies work items and holds
   anything that touches a human-only boundary.
7. **Tool authorization (Aegis).** Aegis verifies a signed capability and
   policy for each tool call, and denies when any check cannot complete.

## Expected workload

These are **planning assumptions**, not measurements. Step 13 of the
improvement plan replaces them with acceptance criteria that are set before
any benchmark runs. Until then, no capacity claim is made.

| Dimension | Assumption |
|---|---|
| Deployment | One team, one environment, a single host per component |
| Evaluation | Up to a few thousand cases per suite, run per release candidate |
| Release cadence | Several candidate evaluations per day |
| Trace import | Files processed one at a time, within the importer's input bounds |
| Aegis | Interactive agent traffic from a small number of workloads |

## Prohibited uses

Sentinel and Aegis must not be used:

- as the **sole** safety or compliance control for a consequential system; a
  passing report is evidence for a human reviewer, not a certification;
- to make or approve decisions in its declared
  [human-only boundaries](VALUE_ROUTE_GATEWAY.md#human-only-boundaries):
  identity verification, legal documents, financial decisions, hiring
  assessments, confidential client data, private credentials, or external
  distribution of sensitive data;
- to monitor, profile, or score individual people;
- to execute financial transactions, trades, or transfers;
- against systems the operator is not authorized to test or monitor; or
- with production secrets or personal data in fixtures, examples, or CI.

## When the system refuses

Each item below is a denial or a failed gate, not a warning.

| Situation | Behavior | Enforced in |
|---|---|---|
| Agent or action not declared in policy | Deny, with a recorded reason | `policy.py`; `tests/test_policy.py` |
| Per-run action budget exhausted | Deny | `policy.py` |
| HTTP target outside the domain boundary, or a private, loopback, or link-local address | Deny, and every redirect hop is re-checked | `http.py`; `tests/test_security.py` |
| Filesystem target outside an allowed prefix, or path traversal | Deny | `policy.py` |
| Audit record cannot be written | The action does not run | `agents/base.py` |
| Audit chain altered, reordered, or downgraded from keyed to unkeyed | Verification fails | `audit.py`; portable verifiers |
| Candidate release has any hard safety failure | Release gate fails, whatever the aggregate score | `evaluation.py`; `tests/test_evaluation.py` |
| Trace missing spans or malformed | Marked partial or rejected; absence is never treated as success | `trace_import.py`; `tests/test_trace_import.py` |
| Aegis: missing identity, invalid signature, stale policy hash, replayed capability, revoked principal, missing approval, exhausted rate limit, state-store failure, or audit failure | Deny | `Aegis/internal/aegis/authorizer.go`; `authorizer_test.go` |
| Work touches a human-only boundary | Routed to human review, never approved automatically | `value_router.py`; `tests/test_value_router.py` |

## Actions that require human approval

| Action | Approval mechanism today | Gap (tracked in plan step 10) |
|---|---|---|
| Any Aegis rule marked `require_approval` (for example, promoting a deployment) | A separately signed approval, verified per request. It is bound to the subject, tool, action, resource, policy hash, and the exact capability token, and it expires and can be used once (`verifyApproval`; `TestApprovalIsSeparatelySignedAndBoundToCapability`) | The call's arguments are not bound. Emergency stop, and limits on actions already running, are not defined |
| Changing `policy.yaml` or an Aegis policy bundle | A reviewed pull request (CODEOWNERS) | Branch protection is not yet active (plan step 5) |
| Releasing a candidate that passed the gate | A human release owner decides; the gate never deploys | No recorded approval artifact yet |
| Work in a human-only boundary | A person decides; the router only holds the item | — |
| Accepting a known vulnerability in a release | A justified, code-owned entry in `.grype.yaml` | — |
| Publishing AI-generated financial content (financial-content gate, #40) | Even the best outcome routes to a human release decision | Pending merge |

## Boundaries of responsibility

| Sentinel is responsible for | The operator is responsible for |
|---|---|
| Enforcing the policy it is given, and denying by default | Writing a correct policy, and reviewing changes to it |
| Recording each decision before execution | Protecting the audit key and anchoring digests externally |
| Detecting alteration of retained audit records | Detecting deletion of an entire log, until anchoring ships |
| Failing a release on a hard safety failure | Choosing which cases represent their risks |
| Reporting evidence with sources | Deciding what to do with that evidence |
| Refusing when a check cannot complete | Running the system with production-grade identity, secrets, and monitoring |

Sentinel does not establish the safety of the agent it governs. It limits and
records what that agent can do, and it makes failures visible.

## Reporting and challenging an error

Report a suspected security issue privately, following
[SECURITY.md](../SECURITY.md#8-reporting-a-vulnerability). Report an incorrect
allow, deny, or evaluation result as a GitHub issue. Include the audit sequence
number or report ID, so the decision can be traced and reviewed by a person.
