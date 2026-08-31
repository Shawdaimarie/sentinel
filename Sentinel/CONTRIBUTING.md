# Contributing

Contributions are welcome and held to the standard the project sets for itself.

## Requirements for any change

- `ruff check`, `mypy --strict`, and `pytest` pass. CI enforces all three.
- No action can reach execution without passing `Agent.act`. A pull request that introduces a direct side effect will not be merged, regardless of its other merits.
- Every new agent capability is declared in `policy.yaml` and covered by a test that confirms it is denied when not declared.
- Public functions have docstrings that state what they do and, where it is not obvious, why.

## Style

- Precise names. `verify` verifies; it does not `check` or `handle`.
- Comments explain intent, not mechanics. If the code needs a comment to say *what* it does, rewrite the code.
- No abbreviations in identifiers that a reader outside the project would need to decode.

## Process

1. Open an issue describing the change and its motivation.
2. One concern per pull request.
3. Reference the issue and state, in the description, what boundary the change touches and how it is tested.
