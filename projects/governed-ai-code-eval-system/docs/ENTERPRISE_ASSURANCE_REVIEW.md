# Enterprise Assurance Review

## Assurance Position

This project is designed as a high-trust, client-neutral proof system for AI engineering, AI infrastructure, and code-agent evaluation. It does not claim certification, government clearance, or endorsement by any named institution. It does provide a clear evidence trail that can be reviewed by technical, security, and hiring stakeholders.

## Release Confidence

| Area | Control | Evidence |
| --- | --- | --- |
| Claims | Public copy avoids client names, private access details, and unsupported affiliation language. | Text scan and GitHub search completed. |
| Source integrity | Deployment is tied to a committed source state. | Clean local repository and saved deployment version. |
| Build reliability | Production build must pass twice before publish. | Repeat build gate completed. |
| Evaluator reliability | Python evaluator tests and compilation must pass before release. | Unit test and compile gates. |
| Scenario coverage | Universal workflow scenarios must remain runnable and sanitized. | Scenario evidence library and unit tests. |
| Universal support | Review surfaces and active rule count must remain inspectable. | Universal support matrix and support-surface export. |
| Model calibration | Candidate outputs can be compared and ranked with documented decision gates. | Calibration lab, comparison helper, protocol, and local audit trail. |
| Automation readiness | Machine-readable evaluator output must stay deterministic. | JSONL output gate and schema documentation. |
| Static security | No production secrets or credentials are required by the site. | Assurance scan and deployment notes. |
| Access posture | Default deployment remains private until deliberate public sharing is selected. | Owner-only private publish. |
| AI governance | Model output is treated as untrusted until reviewed. | Severity rubric, evidence levels, and promotion gates. |
| Audit readiness | Evidence is preserved in reusable docs, structured records, and local calibration snapshots instead of private chat or platform screenshots. | GitHub package, Handshake entry, calibration audit trail, and deployment notes. |

## Standards Alignment

This project is aligned to the intent of recognized secure-software and AI-risk practices:

- NIST Secure Software Development Framework: secure development practices, vulnerability reduction, and supplier communication.
- NIST AI Risk Management Framework: govern, map, measure, and manage AI risks throughout the system lifecycle.
- NIST Generative AI Profile: risk actions and documentation practices for generative AI systems.
- OWASP Application Security Verification Standard: security-control verification as a measurable basis for trust.
- OWASP GenAI LLM Top 10: prompt injection, sensitive disclosure, supply chain, and agency risks for LLM applications.
- CISA Secure by Design: producer ownership, secure defaults, transparency, and accountability.

## Clearance-Oriented Evidence Rules

- Do not include client names, confidential platform links, internal messages, private datasets, account identifiers, or screenshots from restricted systems.
- Do not claim certification, clearance, institutional endorsement, or production equivalence without documented proof.
- Do not store real credentials, API keys, tokens, or private keys in source control.
- Do preserve sanitized evidence of reasoning, testing, risk classification, and decision quality.
- Do keep promotion decisions tied to observable findings and explicit acceptance criteria.

## Verification Gate

Before each public or reviewer-facing release:

```bash
pnpm run assurance
pnpm run lint
pnpm run build
pnpm run build
python3 -m unittest discover -s packages/evaluator/tests
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl
PYTHONPATH=packages/evaluator/src python3 -c "from governed_ai_code_eval import calibration_report_to_jsonl, compare_candidate_reviews; report = compare_candidate_reviews('calibration proof', [('safe', 'def ok():\n    return 1\n'), ('risky', 'result = eval(user_input)\n')], tests_present=True, threat_model_present=True, performance_budget_present=True); assert 'calibration_summary' in calibration_report_to_jsonl(report)"
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --scenario-library
PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --list-surfaces
python3 -m compileall packages/evaluator/src packages/evaluator/tests packages/evaluator/examples
```

Blocking conditions:

- Any real credential or private key pattern appears in source.
- Client-specific or confidential details appear in public-facing materials.
- Build, lint, or assurance checks fail.
- The deployment audience is broader than intended.
- A claim cannot be backed by a file, test, review note, or deployed artifact.

## Reviewer Takeaway

The system is built to show disciplined engineering judgment: verify before promoting, block unsafe model output, preserve audit evidence, and keep public materials accurate, client-neutral, and security-aware.
