# Governed AI Code Evaluation System

Live application deployment: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

GitHub project package: [`projects/governed-ai-code-eval-system/README.md`](./governed-ai-code-eval-system/README.md)

## Summary

The Governed AI Code Evaluation System is a deployable application and public GitHub project package for advancement in AI engineering, AI infrastructure, software engineering, code-agent evaluation, and hands-on coding readiness.

It treats AI-generated code as useful but untrusted until it passes governed review. The system turns candidate code and evidence into scored findings, required actions, a promotion decision, machine-readable JSONL output, and comparative model-calibration evidence.

Current posture: **top-tier candidate readiness**. This means the project has strong inspectable evidence for serious technical review while keeping official ranking, certification, clearance, approval, or endorsement separate unless granted by an external authority.

## Latest AI-Sector Upgrade

The current release adds a model-calibration layer for comparing multiple candidate outputs. This moves the project beyond single-output review into AI-sector evaluation work where the reviewer must rank model responses, justify tradeoffs, and decide whether the leading candidate can advance.

New capabilities include:

- Model Calibration Lab in the live app with adjustable weights for AI security boundary, task correctness, data reliability, and operational readiness.
- Python `compare_candidate_reviews()` helper for ranking multiple model-generated candidates.
- Consensus-gap signal that separates clear winners from human tie-break situations.
- Calibration protocol aligned with NIST AI RMF, NIST Generative AI Profile, and OWASP GenAI security guidance.
- Verification workflow check for model-comparison calibration.

## High-Value Method Layer

The project maps its proof to technology lanes with strong demand signals:

- AI research and evaluation systems: deterministic model-output review, structured findings, comparative calibration, and repeatable evaluator tests.
- Secure AI and cybersecurity governance: unsafe execution checks, secret hygiene, prompt-injection boundaries, sensitive-log controls, and threat-model discipline.
- Software and platform engineering: typed application workflow, repeat production builds, release hygiene, and promotion gates.
- Data quality and model-evaluation tooling: JSONL records, schema-validation expectations, and data-quality findings for generated or remote output.
- Executive technical review posture: claim boundaries, evidence ownership, and clear separation between readiness evidence and external credentialing.

## Application Upgrade

The live project includes an interactive application workspace with:

- Editable candidate-code review input.
- Evidence controls for tests, threat model, and performance budget.
- Scored readiness and risk index.
- Governed findings across security, correctness, data quality, reliability, performance, maintainability, and evidence quality.
- Promotion gate such as `Security Blocker`, `Remediation Required`, `Evidence Hold`, `Approve With Notes`, or `Promotion Ready`.
- Model Calibration Lab for comparing candidate model outputs.
- JSONL output suitable for CI comments, audit logs, dashboards, and model-comparison reports.

## Evidence Stack

- Live React/Vinext application presenting the governed review workflow.
- Browser-based evaluator with editable code, evidence controls, findings, score, risk index, JSONL output, and model calibration.
- Runnable Python evaluator packaged in the deployed source state.
- Reusable model-comparison calibration helper.
- Machine-readable JSONL schema for automation and audit use.
- Unit-tested rule detection for security, correctness, reliability, performance, data quality, promotion gates, structured output, and calibration ranking.
- Advanced AI-risk checks for prompt-injection bypass phrases, sensitive logging, unsafe parsing of model output, unsafe execution, secret-like values, YAML/pickle deserialization, and missing network timeouts.
- Sanitized case studies covering unsafe execution, unreliable integration, and missing evidence.
- Security policy, threat model, test strategy, deployment notes, structured-output schema, model calibration protocol, high-value method alignment, and governed approval rubric.
- Handshake-ready project entry for AI engineering, AI infrastructure, software engineering, and coding evaluation roles.

## Current Proof Signals

- Deployed Sites version: `11`.
- Source commit: `217c7492ba74458e17c732568612b71863e7ec4b`.
- Evaluator tests: `9` passing.
- Sample governed review output: `14` findings across security, correctness, reliability, performance, and data quality.
- Calibration proof: safer candidate ranked first with high consensus separation.
- Release quality gates: assurance, lint, production build twice, Python unit tests, JSONL evaluator output, model-calibration proof command, Python compile check, clean publication scan.

## Assurance Standard

This project is designed to read like serious enterprise and research-grade software evidence without claiming external certification or institutional endorsement.

Assurance controls include:

- Client-neutral public wording.
- No confidential platform details or private account identifiers.
- No production secrets or credentials required for the site.
- Private-by-default deployment posture.
- Repeatable assurance, lint, production build, Python unit-test, JSONL output, calibration, and evaluator compilation gates.
- Claims tied to visible files, tests, review artifacts, or deployed surfaces.

Reference alignment:

- NIST Secure Software Development Framework: https://csrc.nist.gov/pubs/sp/800/218/final
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST Generative AI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- OWASP GenAI LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
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
PYTHONPATH=packages/evaluator/src python3 -c "from governed_ai_code_eval import compare_candidate_reviews; report = compare_candidate_reviews('calibration proof', [('safe', 'def ok():\n    return 1\n'), ('risky', 'result = eval(user_input)\n')], tests_present=True, threat_model_present=True, performance_budget_present=True); assert report.winner == 'safe'"
python3 -m compileall packages/evaluator/src packages/evaluator/tests packages/evaluator/examples
```

The release also passed a current-file scan for client-specific terms before deployment and GitHub publication.

## Public Market Sources

- U.S. Bureau of Labor Statistics, Computer and Information Systems Managers: https://www.bls.gov/ooh/management/computer-and-information-systems-managers.htm
- U.S. Bureau of Labor Statistics, Computer and Information Research Scientists: https://www.bls.gov/ooh/computer-and-information-technology/computer-and-information-research-scientists.htm
- U.S. Bureau of Labor Statistics, Software Developers, Quality Assurance Analysts, and Testers: https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm
- U.S. Bureau of Labor Statistics, Information Security Analysts: https://www.bls.gov/ooh/computer-and-information-technology/information-security-analysts.htm
- U.S. Bureau of Labor Statistics, Fastest Growing Occupations: https://www.bls.gov/ooh/fastest-growing.htm

## Next Four-Step Advancement Loop

1. Add sanitized comparison scenarios for model training, inference services, MLOps pipelines, and agent tools.
2. Add calibration history so repeated model comparisons can be reviewed over time.
3. Connect JSONL and calibration output to automated pull-request summaries or a lightweight dashboard.
4. Refresh GitHub, Handshake, portfolio, and application language only when deployed evidence improves.
