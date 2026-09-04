# Contributing

Contributions are welcome and held to the standard the project sets for itself.

## Requirements for any change

- `ruff check src tests`, `mypy src`, and `pytest -q` pass. CI enforces all
  three on Python 3.11 and 3.12.
- The deterministic `sentinel-eval` release gate passes whenever agent behavior
  or evaluation logic changes.
- No action can reach execution without passing `Agent.act`. A pull request
  that introduces a direct side effect will not be merged, regardless of its
  other merits.
- Every new agent capability is declared in `policy.yaml` and covered by a test
  confirming that it is denied when undeclared.
- Any change to audit serialization, fields, digest modes, or verification
  order updates `spec/SPEC.md`, the normative vectors, Sentinel's conformance
  tests, and the independent Python, TypeScript, and Go verifiers in the same
  pull request.
- Public functions have docstrings that state what they do and, where it is not
  obvious, why.
- Security-impacting changes update `SECURITY.md`, including residual risk.

## Local verification

```bash
make quality
make test
make compare

python -m unittest discover -s verifiers/python -p "test_*.py" -v

cd verifiers/typescript
tsc -p tsconfig.json
node dist/test.js

cd ../go
go test ./...
```

## Style

- Use precise names. `verify` verifies; it does not `check` or `handle`.
- Comments explain intent, not mechanics. If code needs a comment to say what
  it does, rewrite the code.
- Avoid abbreviations that a reader outside the project would need to decode.
- Preserve deterministic output and explicit failure behavior.
- Do not present example-fixture performance as a production model result.

## Process

1. Open an issue describing the change and its motivation.
2. Keep one concern per pull request.
3. State which trust boundary or release criterion the change affects.
4. Include tests and evaluation evidence before requesting review.
5. Merge only after CI, CodeQL, conformance, and container gates are green.
