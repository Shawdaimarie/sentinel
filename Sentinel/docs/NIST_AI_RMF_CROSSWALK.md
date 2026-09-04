# NIST AI RMF crosswalk

This document is an engineering crosswalk, not a certification or a claim of
formal NIST conformance. It shows where Sentinel provides concrete artifacts
that can support an organization's broader AI risk-management process.

References:

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)
- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)

## GOVERN

| Practice | Sentinel evidence |
|---|---|
| Make risk responsibilities and controls explicit | `policy.yaml`, versioned eval cases, code review through pull requests |
| Preserve accountability | Every proposed action is logged before execution with agent, target, decision, and reason |
| Establish release criteria | CI thresholds for score, pass rate, safety pass rate, and regression tolerance |
| Document residual risk | `SECURITY.md`, report interpretation boundary, and case-study limitations |

## MAP

| Practice | Sentinel evidence |
|---|---|
| Identify context and intended use | Each eval case contains a named task and tags |
| Identify affected systems and trust boundaries | `ARCHITECTURE.md` and `SECURITY.md` |
| Identify foreseeable misuse and failure modes | Prompt injection, secret access, PII leakage, unbounded retries, unauthorized payment, and database mutation cases |
| Distinguish risk classes | Tag slices for security, privacy, grounding, governance, reliability, and regulated workflows |

## MEASURE

| Practice | Sentinel evidence |
|---|---|
| Define observable metrics | Correctness, safety, grounding, tool use, latency, cost, and action budgets |
| Test before release | Deterministic suite invoked by GitHub Actions |
| Compare over time | Paired baseline/candidate regression report |
| Preserve measurement provenance | SHA-256 input fingerprints and complete JSON reports |
| Expose subgroup or scenario performance | Tag-level slice summaries |

## MANAGE

| Practice | Sentinel evidence |
|---|---|
| Block unacceptable behavior | Forbidden actions and prohibited disclosures are hard failures |
| Require human oversight for consequential actions | `approval.request` evaluation pattern and deny-by-default policy |
| Bound resource use | Per-agent budgets, retry limits, latency limits, and cost limits |
| Respond to failures | Failing cases and regression reasons are retained in reports rather than averaged away |
| Support independent review | Human-readable Markdown, machine-readable JSON, security tests, and explicit limitations |

## Coverage boundary

Sentinel does not provide organizational governance, legal review, end-user
impact assessment, production incident response, or domain-specific validation
by itself. Those responsibilities remain with the deploying organization. The
crosswalk identifies supporting engineering evidence only.
