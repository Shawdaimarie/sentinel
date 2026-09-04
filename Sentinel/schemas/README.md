# Evaluation schemas

These JSON Schemas document the two portable input contracts consumed by
`sentinel-eval`:

- [`eval-case.schema.json`](eval-case.schema.json) — versioned expectations for
  one behavior;
- [`agent-run.schema.json`](agent-run.schema.json) — an observable run artifact
  containing output, tool trace, evidence, latency, and cost.

The Python implementation remains the normative validator for this release.
`SuiteReport` and `ComparisonReport` JSON output schemas can be generated from
the Pydantic models when an integration needs them:

```python
import json
from sentinel.evaluation import ComparisonReport, SuiteReport

print(json.dumps(SuiteReport.model_json_schema(), indent=2))
print(json.dumps(ComparisonReport.model_json_schema(), indent=2))
```

Keeping the input contracts language-neutral makes it possible to capture runs
from Python, TypeScript, Go, Java, C#, Rust, or external trace-processing
systems without coupling the evaluated system to Sentinel's runtime.
