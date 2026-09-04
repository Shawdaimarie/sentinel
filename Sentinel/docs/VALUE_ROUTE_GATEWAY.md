# Value Route Gateway

The Value Route Gateway connects Sentinel's technical controls to a practical
employment and delivery question: **which work is valuable, evidenced, secure,
deployable, and safe to present externally?**

It exists because more output is not the same as more value. A professional AI
engineering project should show that work can be prioritized, routed, protected,
reviewed, and shipped without weakening trust.

## Routing dimensions

Every item is scored across five dimensions:

| Dimension | Purpose |
|---|---|
| Value | The item improves a real business, engineering, evaluation, or portfolio decision. |
| Evidence | The item is supported by source, tests, reports, cases, metrics, or a stated assumption. |
| Security | The item does not expose secrets, sensitive data, uncontrolled side effects, or weak boundaries. |
| Deployment | The item can be run, reviewed, published, piloted, or handed off with clear next steps. |
| Rights clarity | Ownership, attribution, public-proof status, and private-work boundaries are clear. |

## Route lanes

| Lane | Meaning |
|---|---|
| Deployable | Strong value, evidence, security, deployment readiness, and rights clarity. |
| Pilot | Useful and safe enough for a bounded pilot, but not yet a durable delivery pattern. |
| Human review | Valuable, but requires written review before use because the work touches a human-only boundary. |
| Reserved hold | The work may be valuable, but ownership or reuse terms are not clear enough for distribution. |
| Reject | A hard blocker exists, such as weak security or attempted distribution of sensitive data. |

## Human-only boundaries

The router does not automate or approve work involving:

- identity verification;
- legal documents;
- financial decisions;
- hiring assessments or interview responses;
- confidential client data;
- private account credentials; or
- external distribution of sensitive data.

Those decisions remain human-controlled even when the surrounding analysis is
automated.

## Public proof versus private value

Sentinel can be public proof of technical ability. Public proof should contain
source code, documentation, tests, examples, evidence reports, limits, and clear
ownership attribution.

Private value should remain separated from public proof. That includes client
workflows, sensitive data, business terms, private deployment configurations,
account access, and any asset intended for paid delivery rather than general
public inspection.

## Employment signal

This gateway makes the project easier for a technical reviewer or hiring manager
to interpret. It shows that Shawdai Marie can:

1. identify valuable work;
2. refuse unsafe work;
3. separate public evidence from private delivery;
4. produce reproducible reports;
5. maintain human approval boundaries; and
6. connect AI engineering output to business-ready decisions.

## Local execution

```bash
sentinel-value-router \
  --items examples/value_route_items.json \
  --json-out reports/automation/value_routes.json \
  --markdown-out reports/automation/value_routes.md \
  --min-score 0.70
```

The command returns nonzero if an item is rejected or falls below the configured
minimum value score.
