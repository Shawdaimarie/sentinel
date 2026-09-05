# Governed AI Code Evaluation System

Live private deployment: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

## Summary

The Governed AI Code Evaluation System is an assurance-backed AI engineering project for reviewing frontier coding-agent outputs through security, correctness, reliability, performance, and evidence-quality gates.

It supports software engineering, AI infrastructure, and model-evaluation work by treating AI-generated code as useful but untrusted until it has passed clear controls.

## Implementation Status

The deployed source package now includes a runnable evaluator, an implementation pipeline view, sanitized case studies, a security policy, a threat model, a test strategy, and a value-exposure plan.

This GitHub reference is intentionally concise: it gives reviewers the live project link, the system value, the evidence stack, and the verification standard without exposing private work or unsupported claims.

## Why This Belongs With Sentinel

Sentinel is positioned around governed multi-agent systems, continuous verification, and sourced accountability. This project extends that same principle into code-agent evaluation: model outputs should be reviewed, classified, and promoted only when the evidence trail is strong enough.

## Evidence Stack

- Deployable React/Vinext site presenting the system surface.
- Runnable Python evaluator packaged under `packages/evaluator` in the deployed source package.
- Unit-tested rule detection for security, reliability, evidence quality, and promotion gates.
- Severity rubric for critical, high, medium, low, and informational issues.
- Promotion gates for security blockers, required changes, missing evidence, performance follow-up, and human approval.
- Sanitized case studies covering unsafe execution, unreliable inference integration, and missing evidence.
- Security policy, threat model, test strategy, and deployment notes.
- Enterprise assurance review covering claim accuracy, client-neutrality, private-by-default deployment, and repeatable release gates.
- Handshake-ready project entry for AI engineering and AI infrastructure roles.

## Assurance Standard

This project is designed to read like serious enterprise and research-grade software evidence without claiming external certification or institutional endorsement.

Assurance controls include:

- Client-neutral public wording.
- No confidential platform details or private account identifiers.
- No production secrets or credentials required for the site.
- Private-by-default deployment posture.
- Repeatable assurance, lint, production build, Python unit-test, and evaluator compilation gates.
- Claims tied to visible files, tests, review artifacts, or deployed surfaces.

Reference alignment:

- NIST Secure Software Development Framework: https://csrc.nist.gov/pubs/sp/800/218/final
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- OWASP Application Security Verification Standard: https://owasp.org/www-project-application-security-verification-standard/
- CISA Secure by Design: https://www.cisa.gov/securebydesign

## Skills Demonstrated

- AI engineering
- AI infrastructure
- Code-agent evaluation
- LLM application review
- Secure software development
- Model-output adjudication
- Threat modeling
- Technical writing
- Risk classification
- Test and build verification
- CI release gating
- Governance and audit evidence
- Claim accuracy and client-neutral communication

## Verification

The deployed source was verified on September 5, 2026 with:

```bash
pnpm run assurance
pnpm run lint
pnpm run build
pnpm run build
python3 -m unittest discover -s packages/evaluator/tests
python3 -m compileall packages/evaluator/src packages/evaluator/tests
```

The release also passed a current-file scan and a local Git-history scan for client-specific terms before deployment.

## Next Upgrade

Expand the evaluator with additional sanitized scenarios for model training, inference services, MLOps pipelines, prompt-injection boundaries, dependency risk, logging hygiene, and machine-readable review output for pull-request comments.
