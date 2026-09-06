# Model Calibration Protocol

## Purpose

This protocol turns the project from a single-output review tool into a comparative AI evaluation system. It defines how multiple model-generated implementations are scored, ranked, and advanced without treating any model output as automatically trustworthy.

## AI-Sector Standard

The calibration layer is aligned to the current AI-sector need for testing, evaluation, verification, validation, security review, and controlled deployment. It supports the NIST AI Risk Management Framework, the NIST Generative AI Profile, and OWASP GenAI security guidance without claiming external certification or endorsement.

## Calibration Inputs

Each candidate output should include:

- Candidate identifier.
- Candidate code or implementation artifact.
- Intended task or requirement.
- Test evidence.
- Threat-model note.
- Performance or resource budget.
- Reviewer notes for known constraints.

## Weighted Criteria

| Criterion | Default Weight | What It Measures |
| --- | ---: | --- |
| AI security boundary | 35% | Tool scope, secret handling, prompt-injection resistance, sensitive logging, and unsafe execution control. |
| Task correctness | 25% | Requirement fit, edge cases, error paths, and deterministic behavior. |
| Data reliability | 20% | Schema validation, generated-output handling, provenance, and reproducible review records. |
| Operational readiness | 20% | Timeouts, resource limits, observability, rollback readiness, and evidence maturity. |

## Decision Gates

| Gate | Meaning |
| --- | --- |
| `Advance to review` | Strong enough to move forward with human review and final acceptance checks. |
| `Calibrate with notes` | Promising output, but reviewer should inspect the gap before promotion. |
| `Data-quality hold` | Output may be useful, but generated or remote data handling is not sufficiently validated. |
| `Security hold` | Security boundary is too weak for advancement. |
| `Remediation required` | Candidate needs material rework before it can compete. |

## Consensus Gap

| Gap | Trigger | Required Action |
| --- | --- | --- |
| High separation | 25 or more points between top and bottom candidates, or a security-blocked candidate. | Select the top candidate only after documenting why lower-ranked outputs failed. |
| Medium separation | 12 to 24 points between candidates. | Keep the top candidate, but preserve reviewer notes and tradeoffs. |
| Human tie-break | Fewer than 12 points between candidates. | Use a second reviewer, additional tests, or a more specific scenario before selecting a winner. |

## Evidence Output

The Python evaluator exposes `compare_candidate_reviews()` for reusable model comparison. The browser application exposes a Model Calibration Lab where review weights can be adjusted and candidate rankings update immediately.

The browser application also provides a local calibration audit trail. Saved snapshots remain in the browser and preserve only review metadata: review name, timestamp, winning candidate, score spread, confidence signal, rubric weights, candidate ranks, weighted scores, and decision gates.

The Python package can emit calibration JSONL with `calibration_report_to_jsonl()` so comparison decisions can be attached to CI evidence, portfolio records, reviewer packets, or internal quality logs.

The expected proof trail is:

1. Run individual governed reviews.
2. Compare candidates using the weighted rubric.
3. Record winner, score spread, consensus gap, and decision.
4. Save a local calibration snapshot when the decision should be preserved.
5. Keep JSONL output and reviewer notes as evidence.
6. Promote only when the top candidate clears safety, correctness, data-quality, and operational gates.

## Claim Boundary

Accurate positioning:

This project demonstrates AI-sector calibration readiness through comparative model-output review, weighted scoring, local audit snapshots, calibration JSONL, security boundary checks, data-quality controls, evaluator tests, and reviewer-safe documentation.

Do not claim official benchmark leadership, clearance, certification, or institutional approval unless a qualified external reviewer grants it separately.

## Sources

- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST Generative AI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- OWASP GenAI LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
