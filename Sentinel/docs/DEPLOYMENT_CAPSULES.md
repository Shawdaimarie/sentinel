# Deployment Capsules

Deployment Capsules connect Sentinel's technical proof to a deployable,
protected, reviewer-readable unit of value. A capsule is not a zip file and it
is not a legal shield by itself. It is a manifest-backed control layer that
answers a practical question:

> What exactly is ready to show, pilot, hand off, or hold back?

## Why this exists

Strong public proof helps with hiring, interviews, and technical credibility.
Private delivery value helps with paid work. Mixing the two creates risk:
public proof can accidentally expose private value, client material, account
data, implementation terms, or assessment content.

A capsule keeps the boundary explicit.

## Capsule dimensions

Every capsule is scored by:

| Dimension | Meaning |
|---|---|
| Value | The capsule supports a real hiring, engineering, delivery, or business decision. |
| Evidence | The capsule is backed by files, hashes, tests, docs, workflows, or reports. |
| Security | The capsule excludes secrets, sensitive data, uncontrolled side effects, and weak boundaries. |
| Deployability | The capsule can be reviewed, piloted, reused, or handed off with clear next steps. |
| Rights clarity | Authorship, license expression, reuse limits, and private/public boundaries are explicit. |

## Status labels

| Status | Meaning |
|---|---|
| Ready | Safe to present or use under the stated terms. |
| Review | Potentially valuable but missing evidence, deployment clarity, or rights maturity. |
| Blocked | Do not publish, reuse, or hand off until blockers are resolved. |

## Public proof versus private delivery

Public proof should include:

- repository code;
- documentation;
- example fixtures;
- tests;
- CI evidence;
- clear limits; and
- attribution.

Private delivery should exclude from the public repository:

- client-specific integrations;
- private business terms;
- credentials and account data;
- tax, identity, and background-check material;
- hiring assessment responses; and
- non-public implementation prepared for a paying client or employer.

## Rights and licensing reality

A license and manifest create evidence and terms. They do not physically prevent
copying of a public file. Practical protection comes from combining visible
authorship, commit history, license terms, private handling of valuable delivery
material, written contracts for paid work, and legal advice when appropriate.

The default capsule examples make repository code available under the repository
license while keeping brand identity, client work, private deployment details,
and commercial delivery material reserved.

## Local execution

From `Sentinel/`:

```bash
sentinel-capsule \
  --capsules examples/deployment_capsules.json \
  --root . \
  --json-out reports/capsules/deployment_capsules.json \
  --markdown-out reports/capsules/deployment_capsules.md \
  --min-score 0.68
```

Or:

```bash
make capsules
```

The command hashes declared files, reports missing required assets, applies
security and rights gates, and returns nonzero when a capsule is blocked or falls
below the configured minimum score.

## What this signals to reviewers

This layer demonstrates that Shawdai Marie can:

1. build technical proof;
2. separate public evidence from private delivery value;
3. preserve authorship and rights clarity;
4. hash and report evidence;
5. reject sensitive-data exposure;
6. connect software output to deployable business value; and
7. keep high-risk human decisions outside automation.

That is the kind of communication, governance, and engineering discipline that
makes AI systems easier to trust and easier to hire against.
