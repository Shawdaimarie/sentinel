# First run: verify an installed Sentinel package

This offline example imports a synthetic trace, checks its expected behavior,
and confirms that an observed forbidden action and malformed input are rejected
by the evaluator and importer. No API key, live agent, database, or provider
account is needed. The example does not execute or prevent a live tool action.

Use Python 3.11 or 3.12. From a terminal on macOS or Linux:

```bash
git clone https://github.com/Shawdaimarie/sentinel.git
cd sentinel
python3 --version
python3 -m venv .package-venv
.package-venv/bin/python -m pip wheel --no-deps --wheel-dir dist ./Sentinel
.package-venv/bin/python -m pip install dist/sentinel-*.whl
.package-venv/bin/python -m pip check
.package-venv/bin/python Sentinel/scripts/check_install.py --fixtures Sentinel/examples/otel
```

Confirm that `python3 --version` reports 3.11 or 3.12 before creating the
environment; use your explicit `python3.11` or `python3.12` command if necessary.
Start with a fresh clone and wheel directory to avoid mixing package versions.

The final output begins `PASS: Sentinel` and confirms valid, unsafe, and malformed
cases. It checks the report's passing gate, the specific forbidden-action failure,
and the absence of output for malformed input. A failure exits nonzero with
diagnostics. The check runs the installed
commands in a temporary directory, removes its output afterward, and rejects
editable installations so a source checkout cannot hide packaging mistakes.

Installation downloads declared Python dependencies. The verification itself
uses only the versioned synthetic fixture and does not request network data.
Passing it establishes this example's behavior, not production readiness or
performance. The package-install workflow repeats the check on Python 3.11/3.12.
This source installation resolves declared dependency ranges. For the separately
locked Python 3.12 container inputs, see [dependency verification](DEPENDENCIES.md).
For published images and their signatures, see [release verification](../../RELEASING.md).

For inspectable output files and a step-by-step explanation, use the
[OTLP example](../examples/otel/README.md). For database setup and its separate
credentials and migration requirements, read [evaluation history](EVALUATION_HISTORY.md).
The [20-case assessment](../examples/reliability_assessment/README.md) provides a
larger labeled synthetic suite and persistent evidence files.

If this check fails, report your operating system, Python version, exact commit,
command and sanitized diagnostic. Never include credentials or private traces.
