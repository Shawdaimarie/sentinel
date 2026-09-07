# Governed AI Code Evaluation System

Live application: https://governed-ai-code-eval-system.shawdaimarie.chatgpt.site

This project is a deployable, assurance-backed proof system for advancement in AI engineering, AI infrastructure, software engineering, and coding.

It is built to show practical technical readiness: the ability to evaluate model-generated code across common engineering surfaces, compare candidate outputs, preserve calibration decisions, identify risks, produce runnable evidence, maintain release hygiene, and communicate engineering judgment clearly.

The current evidence posture is **top-tier candidate readiness**: strong enough for serious technical review, while leaving official approval, certification, or ranking to external reviewers and credentialing bodies.

It presents a governed review system that evaluates AI-generated code through seven reviewer lenses:

- Security
- Correctness
- Data quality
- Reliability
- Performance
- Maintainability
- Evidence quality

## What It Demonstrates

- A clear promotion gate for model-generated software.
- An interactive application workspace for reviewing candidate code, toggling evidence controls, and producing reviewer-ready JSONL output.
- Executable coding proof through a Python evaluator, model-comparison engine, universal scenario library, tests, and structured output.
- Security-first review habits for generated code.
- High-value method alignment for AI research systems, cybersecurity governance, software/platform engineering, and data-quality evaluation tooling.
- Evidence-backed technical judgment, not just broad AI claims.
- Portfolio-ready framing for AI engineering and infrastructure roles.
- A deployment-ready web surface built with React, Vinext, Tailwind, and Sites.
- A browser-based evaluator that mirrors the governed review flow with scored findings, risk index, evidence level, and promotion decision.
- A packaged Python evaluator with unit tests and sample review artifacts.
- Sanitized case studies, a threat model, a test strategy, and a security policy for reviewer confidence.
- Machine-readable JSONL evaluator output for future CI, audit-log, dashboard, universal-support, and calibration integrations.
- Prompt-injection, sensitive logging, model-output validation, SQL boundary, release-script, and container-hardening checks for stronger AI infrastructure readiness.
- Model Calibration Lab for ranking candidate outputs by security, correctness, data reliability, and operational readiness.
- Local calibration audit trail for saving reviewer decisions, weights, rankings, score spread, and decision gates without storing candidate source code.
- Scenario evidence library covering model training, inference services, MLOps pipelines, agent tooling, TypeScript/JavaScript APIs, SQL/data access, shell release scripts, and container runtimes.
- Universal support matrix covering Python, TypeScript/JavaScript, SQL/data access, shell/release scripts, container images, infrastructure policy, AI/ML workflows, and agent tooling.
- A release hygiene cadence, advancement roadmap, and opportunity operating process for sustained growth.
- A governed approval rubric that separates evidence-backed readiness from external certification or endorsement.
- Accurate, client-neutral claims supported by repeatable release gates.

## Current Proof Signals

- Deployed Sites version: `14`.
- Source commit: `49c4bc0546cbd5c360a8c516ca18db4273363e4e`.
- Evaluator tests: `14` passing.
- Scenario coverage: `8` universal workflows.
- Supported review surfaces: `8`.
- Review signal posture: `32` active signals.
- Sample JSONL output: `16` records across summary, metadata, and findings.
- Verification date: September 7, 2026.

## Verification

The final source has been checked with:

```bash
pnpm run assurance
pnpm run lint
pnpm run build
pnpm run build
```

The companion evaluator was checked with:

```bash
python3 -m unittest discover -s packages/evaluator/tests
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
PYTHONPATH=packages/evaluator/src python3 -c "from governed_ai_code_eval import calibration_report_to_jsonl, compare_candidate_reviews; report = compare_candidate_reviews('calibration proof', [('safe', 'def ok():\n    return 1\n'), ('risky', 'result = eval(user_input)\n')], tests_present=True, threat_model_present=True, performance_budget_present=True); assert 'calibration_summary' in calibration_report_to_jsonl(report)"
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --scenario-library
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --list-surfaces
python3 -m compileall packages/evaluator/src packages/evaluator/tests packages/evaluator/examples
```

## Core Proof Assets

- Runnable Evaluator Package
- Interactive Application Workspace
- Sanitized Case Study Library
- Security Policy And Threat Model
- Test Strategy And CI Gate
- Research-Grade Evaluation Protocol
- Structured Output Schema
- Model Calibration Protocol
- Calibration Audit Trail
- Scenario Evidence Library
- Universal Support Matrix
- Release Hygiene Cadence
- Advancement Roadmap
- Opportunity Operating Process
- Advancement Language Guide
- Governed Approval Rubric
- High-Value Method Alignment
- Value Exposure Plan
- Enterprise Assurance Review
- Handshake Project Entry
- Deployment And Security Notes
- Application User Guide

## Positioning

This system is strongest for roles and projects involving:

- Software engineering and coding assessment
- AI code review
- Coding-agent evaluation
- AI model-output adjudication
- Comparative model-output calibration
- LLM application engineering
- Secure AI infrastructure
- Governed agentic systems
- Technical QA for frontier coding models
