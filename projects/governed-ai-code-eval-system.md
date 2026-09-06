# Governed AI Code Evaluation System

Live application deployment: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

GitHub project package: [`projects/governed-ai-code-eval-system/README.md`](./governed-ai-code-eval-system/README.md)

## Summary

The Governed AI Code Evaluation System is a deployable application and public GitHub project package for advancement in AI engineering, AI infrastructure, software engineering, code-agent evaluation, and hands-on coding readiness.

It treats AI-generated code as useful but untrusted until it passes governed review. The system turns candidate code and evidence into scored findings, required actions, a promotion decision, machine-readable JSONL output, comparative model-calibration evidence, a local calibration audit trail, and a sanitized AI/ML scenario evidence library.

Current posture: **top-tier candidate readiness**. This means the project has strong inspectable evidence for serious technical review while keeping official ranking, certification, clearance, approval, or endorsement separate unless granted by an external authority.

## Latest AI-Sector Upgrade

The current release adds a Scenario Evidence Library for realistic AI/ML engineering review workflows. This moves the project beyond one sample and proves broader evaluator coverage across model training, inference services, MLOps pipelines, and agent tooling.

New capabilities include:

- Four sanitized AI/ML workflow scenarios with expected governed findings.
- New evaluator controls for evaluation-data leakage, mutable model and image aliases, model lifecycle risk, unseeded training splits, and runtime dependency installation.
- Python `scenario_evidence_library()` and `review_scenario_library()` helpers.
- Command-line scenario export through `python -m governed_ai_code_eval --scenario-library`.
- Updated unit tests, CI workflow, app metrics, and project documentation.

## High-Value Method Layer

The project maps its proof to technology lanes with strong demand signals:

- AI research and evaluation systems: deterministic model-output review, AI/ML scenario coverage, structured findings, comparative calibration, audit-ready decision evidence, and repeatable evaluator tests.
- Secure AI and cybersecurity governance: unsafe execution checks, secret hygiene, prompt-injection boundaries, sensitive-log controls, runtime dependency checks, and threat-model discipline.
- Software and platform engineering: typed application workflow, repeat production builds, release hygiene, promotion gates, artifact-pinning discipline, and lifecycle review.
- Data quality and model-evaluation tooling: JSONL records, schema-validation expectations, data-leakage detection, and data-quality findings for generated or remote output.
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
- Scenario Evidence Library section showing model training, inference service, MLOps, and agent-tool review coverage.
- JSONL output suitable for CI comments, audit logs, dashboards, and model-comparison reports.

## Evidence Stack

- Live React/Vinext application presenting the governed review workflow.
- Browser-based evaluator with editable code, evidence controls, findings, score, risk index, JSONL output, model calibration, local audit snapshots, and scenario evidence.
- Runnable Python evaluator packaged in the deployed source state.
- Reusable model-comparison calibration helper and calibration JSONL export.
- Reusable scenario library helper and scenario review export.
- Machine-readable JSONL schema for automation and audit use.
- Unit-tested rule detection for security, correctness, reliability, performance, data quality, promotion gates, structured output, calibration ranking, calibration audit export, and scenario coverage.
- Advanced AI-risk checks for prompt-injection bypass phrases, sensitive logging, unsafe parsing of model output, unsafe execution, secret-like values, runtime dependency installation, unsafe YAML/pickle deserialization, missing network timeouts, mutable artifact aliases, and training-data leakage.
- Sanitized case studies and scenario evidence covering unsafe execution, unreliable integration, missing evidence, model training, inference, MLOps, and agent-tool failure modes.
- Security policy, threat model, test strategy, deployment notes, structured-output schema, model calibration protocol, calibration audit trail, scenario evidence library, high-value method alignment, and governed approval rubric.
- Handshake-ready project entry for AI engineering, AI infrastructure, software engineering, and coding evaluation roles.

## Current Proof Signals

- Deployed Sites version: `13`.
- Source commit: `782825fce0fa0eb60470733a2c3d24f41ee8cadf`.
- Evaluator tests: `12` passing.
- Scenario coverage: `4` AI/ML workflows.
- Evaluator rule posture: `23` active review signals across default and contextual findings.
- Sample governed review output: `15` JSONL records across summary and findings.
- Calibration proof: safer candidate ranked first with high consensus separation.
- Audit proof: calibration report emits `calibration_summary` and ranked `calibration_candidate` JSONL records.
- Scenario proof: scenario export covers model training, inference service, MLOps pipeline, and agent tooling.
- Release quality gates: assurance, lint, production build twice, Python unit tests, JSONL evaluator output, calibration audit proof command, scenario-library export, Python compile check, clean publication scan.

## Assurance Standard

This project is designed to read like serious enterprise and research-grade software evidence without claiming external certification or institutional endorsement.

Assurance controls include:

- Client-neutral public wording.
- No confidential platform details or private account identifiers.
- No production secrets or credentials required for the site.
- Sanitized scenario records with synthetic code examples.
- Local-first calibration snapshots that do not send records to a server and do not store candidate source code.
- Private-by-default deployment posture.
- Repeatable assurance, lint, production build, Python unit-test, JSONL output, calibration, audit-export, scenario-library, and evaluator compilation gates.
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
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --scenario-library
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

1. Preserve JSONL evaluator, calibration, and scenario-library output as stable automation evidence.
2. Add reviewer notes and dashboard-ready summaries to scenario evidence.
3. Connect evaluator output to automated pull-request summaries or a lightweight project dashboard.
4. Refresh GitHub, Handshake, portfolio, and application language only when deployed evidence improves.
