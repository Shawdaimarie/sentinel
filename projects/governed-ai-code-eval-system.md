# Governed AI Code Evaluation System

Live application deployment: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

GitHub project package: [`projects/governed-ai-code-eval-system/README.md`](./governed-ai-code-eval-system/README.md)

## Summary

The Governed AI Code Evaluation System is now a deployable application and public GitHub project package for advancement in AI engineering, AI infrastructure, software engineering, code-agent evaluation, and hands-on coding readiness.

It treats AI-generated code as useful but untrusted until it passes security, correctness, reliability, performance, maintainability, and evidence-quality gates. The system turns that review into scored findings, required actions, a promotion decision, and machine-readable JSONL output.

## Application Upgrade

The live project now includes an interactive application workspace with:

- Editable candidate-code review input.
- Evidence controls for tests, threat model, and performance budget.
- Scored readiness and risk index.
- Categorized governed findings.
- Promotion gate such as `Security Blocker`, `Remediation Required`, `Evidence Hold`, `Approve With Notes`, or `Promotion Ready`.
- JSONL output suitable for CI comments, audit logs, dashboards, and model-comparison reports.

## Why This Belongs With Sentinel

Sentinel is positioned around governed AI systems, continuous verification, and sourced accountability. This project extends that principle into code-agent evaluation: model outputs should be reviewed, classified, and promoted only when the evidence trail is strong enough.

## Evidence Stack

- Live React/Vinext application presenting the governed review workflow.
- Browser-based evaluator with editable code, evidence controls, findings, score, risk index, and JSONL output.
- Runnable Python evaluator packaged in the deployed source state.
- Machine-readable JSONL schema for automation and audit use.
- Unit-tested rule detection for security, reliability, evidence quality, promotion gates, and structured output.
- Sanitized case studies covering unsafe execution, unreliable integration, and missing evidence.
- Security policy, threat model, test strategy, deployment notes, structured-output schema, and governed approval rubric.
- Release hygiene cadence, advancement roadmap, advancement language guide, opportunity operating process, and value-exposure plan.
- Handshake-ready project entry for AI engineering, AI infrastructure, software engineering, and coding evaluation roles.

## Governed Ranking Readiness

Current posture: **top-tier candidate readiness**.

That means the project has strong evidence for serious technical review, not that an external party has officially ranked, certified, cleared, or approved it. The ranking signal is based on inspectable proof and accurate claim boundaries.

## Assurance Standard

This project is designed to read like serious enterprise and research-grade software evidence without claiming external certification or institutional endorsement.

Assurance controls include:

- Client-neutral public wording.
- No confidential platform details or private account identifiers.
- No production secrets or credentials required for the site.
- Private-by-default deployment posture.
- Repeatable assurance, lint, production build, Python unit-test, JSONL output, and evaluator compilation gates.
- Claims tied to visible files, tests, review artifacts, or deployed surfaces.

Reference alignment:

- NIST Secure Software Development Framework: https://csrc.nist.gov/pubs/sp/800/218/final
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- OWASP Application Security Verification Standard: https://owasp.org/www-project-application-security-verification-standard/
- CISA Secure by Design: https://www.cisa.gov/securebydesign

## Verification

The application release was verified on September 5, 2026 with:

```bash
pnpm run assurance
pnpm run lint
pnpm run build
pnpm run build
python3 -m unittest discover -s packages/evaluator/tests
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
python3 -m compileall packages/evaluator/src packages/evaluator/tests
```

The release also passed a current-file scan for client-specific terms before deployment and GitHub publication.

## Next Four-Step Advancement Loop

1. Add additional sanitized scenarios for model training, inference services, MLOps pipelines, and agent tools.
2. Expand evaluator rules for prompt-injection boundaries, dependency risk, logging hygiene, and resource budgets.
3. Connect JSONL review output to automated pull-request summaries or a lightweight dashboard.
4. Refresh GitHub, Handshake, portfolio, and application language only when the deployed evidence improves.
