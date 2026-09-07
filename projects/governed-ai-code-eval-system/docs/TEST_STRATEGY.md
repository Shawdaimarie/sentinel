# Test Strategy

## Objective

The system should prove that the public application, evaluator package, security posture, and reviewer-facing documentation are all release-ready before any deployment or portfolio update.

## Test Matrix

| Layer | What Is Tested | Gate |
| --- | --- | --- |
| Site build | React, TypeScript, Vinext production build, static assets, and routing. | `pnpm run build` |
| Site quality | JavaScript and TypeScript lint checks. | `pnpm run lint` |
| Application workflow | Browser-based evaluator state, evidence controls, finding classification, calibration, high-value method alignment, score, promotion gate, and JSONL rendering. | `pnpm run build` plus manual review |
| Release assurance | Required files exist and source does not contain real credential patterns. | `pnpm run assurance` |
| Evaluator logic | Rule detection, AI boundary checks, data-quality checks, severity, evidence levels, risk index, and promotion gates. | `python3 -m unittest discover -s packages/evaluator/tests` |
| Model comparison | Candidate ranking by promotion gate, score, severity, and finding count. | `python3 -m unittest discover -s packages/evaluator/tests` |
| Evaluator automation | JSONL review output remains machine-readable for downstream use. | `PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval packages/evaluator/examples/risky_candidate.py --jsonl` |
| Calibration audit | Model-comparison reports remain exportable as line-oriented audit evidence. | `PYTHONPATH=packages/evaluator/src python3 -c "from governed_ai_code_eval import calibration_report_to_jsonl, compare_candidate_reviews; report = compare_candidate_reviews('calibration proof', [('safe', 'def ok():\n    return 1\n'), ('risky', 'result = eval(user_input)\n')], tests_present=True, threat_model_present=True, performance_budget_present=True); assert 'calibration_summary' in calibration_report_to_jsonl(report)"` |
| Scenario coverage | Sanitized universal workflow examples remain runnable and client-neutral. | `PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --scenario-library` |
| Universal support | Supported review surfaces and active rule count remain exportable. | `PYTHONPATH=packages/evaluator/src python3 -m governed_ai_code_eval --list-surfaces` |
| Python integrity | Evaluator source and tests compile successfully. | `python3 -m compileall packages/evaluator/src packages/evaluator/tests` |
| Publication safety | Public copy excludes client-specific names, restricted links, account identifiers, and unsupported endorsement claims. | Text scan before publish |

## Required Local Release Sequence

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

## CI Expectations

Every pull request and push to `main` should run the web verification gate and the evaluator verification gate. A failure in either gate blocks release.

## Manual Review Expectations

- Confirm the live deployment audience matches the intended sharing level.
- Confirm all claims are supported by files, tests, or deployed output.
- Confirm external links are expected and reviewer-safe.
- Confirm sample cases, scenario-library records, and support-surface records remain sanitized.
- Confirm the application workspace renders editable code, evidence controls, calibration, high-value methods, score, risk index, findings, promotion gate, and JSONL output.
- Confirm no private access, account, or platform details are included.
