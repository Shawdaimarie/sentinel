# Governed AI Code Evaluation System

Live application deployment: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

GitHub project package: [`projects/governed-ai-code-eval-system/README.md`](./governed-ai-code-eval-system/README.md)

## Summary

The Governed AI Code Evaluation System is a deployable application and public GitHub project package for advancement in AI engineering, AI infrastructure, software engineering, code-agent evaluation, and hands-on coding readiness.

It treats AI-generated code as useful but untrusted until it passes governed review. The system turns candidate code and evidence into scored findings, required actions, a promotion decision, machine-readable JSONL output, comparative model-calibration evidence, and a local calibration audit trail.

Current posture: **top-tier candidate readiness**. This means the project has strong inspectable evidence for serious technical review while keeping official ranking, certification, clearance, approval, or endorsement separate unless granted by an external authority.

## Latest AI-Sector Upgrade

The current release adds a calibration audit trail for preserving model-comparison decisions over time. This moves the project beyond one-time candidate ranking into stronger AI-sector evaluation work where reviewers can show which output won, why it won, what weights were used, and what decision gate applied.

New capabilities include:

- Local Audit Trail in the live app for saving calibration snapshots in the browser.
- Copyable audit JSON with review name, timestamp, winner, score spread, confidence signal, rubric weights, candidate ranks, weighted scores, and gates.
- Python `calibration_report_to_jsonl()` helper for machine-readable model-comparison evidence.
- Updated CI workflow check for calibration audit export.
- New Calibration Audit Trail documentation with storage, export, and claim-boundary rules.

## High-Value Method Layer

The project maps its proof to technology lanes with strong demand signals:

- AI research and evaluation systems: deterministic model-output review, structured findings, comparative calibration, audit-ready decision evidence, and repeatable evaluator tests.
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
- Local Audit Trail for preserving model-comparison snapshots in the browser without storing candidate source code.
- JSONL output suitable for CI comments, audit logs, dashboards, and model-comparison reports.

## Evidence Stack

- Live React/Vinext application presenting the governed review workflow.
- Browser-based evaluator with editable code, evidence controls, findings, score, risk index, JSONL output, model calibration, and local audit snapshots.
- Runnable Python evaluator packaged in the deployed source state.
- Reusable model-comparison calibration helper and calibration JSONL export.
- Machine-readable JSONL schema for automation and audit use.
- Unit-tested rule detection for security, correctness, reliability, performance, data quality, promotion gates, structured output, calibration ranking, and calibration audit export.
- Advanced AI-risk checks for prompt-injection bypass phrases, sensitive logging, unsafe parsing of model output, unsafe execution, secret-like values, YAML/pickle deserialization, and missing network timeouts.
- Sanitized case studies covering unsafe execution, unreliable integration, and missing evidence.
- Security policy, threat model, test strategy, deployment notes, structured-output schema, model calibration protocol, calibration audit trail, high-value method alignment, and governed approval rubric.
- Handshake-ready project entry for AI engineering, AI infrastructure, software engineering, and coding evaluation roles.

## Current Proof Signals

- Deployed Sites version: `12`.
- Source commit: `9a398ed4659bd2999dc9dbe8a7bcb47db672fd98`.
- Evaluator tests: `10` passing.
- Sample governed review output: `14` findings across security, correctness, reliability, performance, and data quality.
- Calibration proof: safer candidate ranked first with high consensus separation.
- Audit proof: calibration report emits `calibration_summary` and ranked `calibration_candidate` JSONL records.
- Release quality gates: assurance, lint, production build twice, Python unit tests, JSONL evaluator output, calibration audit proof command, Python compile check, clean publication scan.

## Assurance Standard

This project is designed to read like serious enterprise and research-grade software evidence without claiming external certification or institutional endorsement.

Assurance controls include:

- Client-neutral public wording.
- No confidential platform details or private account identifiers.
- No production secrets or credentials required for the site.
- Local-first calibration snapshots that do not send records to a server and do not store candidate source code.
- Private-by-default deployment posture.
- Repeatable assurance, lint, production build, Python unit-test, JSONL output, calibration, audit-export, and evaluator compilation gates.
- Claims tied to visible files, tests, review artifacts, or deployed surfaces.

Reference alignment:

- NIST Secure Software Development Framework: https://csrc.nist.gov/pubs/sp/800/218/final
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST Generative AI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- OWASP GenAI LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- OWASP Application Security Verification Standard: https://owasp.org/www-project-application-security-verification-standard/
- CISA Secure by Design: https://www.cisa.gov/securebydesign

## Verification

The application release was verified on September 6, 2026 with:

```bash
pnpm run assurance
pnpm run lint
pnpm run build
pnpm run build
python3 -m unittest discover -s packages/evaluator/tests
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
PYTHONPATH=packages/evaluator/src python3 -c "from governed_ai_code_eval import calibration_report_to_jsonl, compare_candidate_reviews; report = compare_candidate_reviews('calibration proof', [('safe', 'def ok():\n    return 1\n'), ('risky', 'result = eval(user_input)\n')], tests_present=True, threat_model_present=True, performance_budget_present=True); assert report.winner == 'safe'; assert 'calibration_summary' in calibration_report_to_jsonl(report)"
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
2. Extend local calibration snapshots with reviewer notes and dashboard-ready summaries.
3. Connect JSONL and calibration output to automated pull-request summaries or a lightweight dashboard.
4. Refresh GitHub, Handshake, portfolio, and application language only when deployed evidence improves.
