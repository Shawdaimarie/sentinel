# First run: verify an installed Sentinel package

This offline example imports a synthetic trace, checks its expected behavior,
and proves that a forbidden action and malformed input are rejected. No API key,
live agent, database, or provider account is needed.

Use Python 3.11 or 3.12. From a terminal on macOS or Linux:

```bash
git clone https://github.com/Shawdaimarie/sentinel.git
cd sentinel
python3 -m venv .package-venv
.package-venv/bin/python -m pip wheel --no-deps --wheel-dir dist ./Sentinel
.package-venv/bin/python -m pip install dist/sentinel-*.whl
.package-venv/bin/python -m pip check
.package-venv/bin/python Sentinel/scripts/check_install.py --fixtures Sentinel/examples/otel
```

The final output begins `PASS: Sentinel` and confirms valid, unsafe, and malformed
cases. A failure exits nonzero with diagnostics. The check runs the installed
commands in a temporary directory, removes its output afterward, and rejects
editable installations so a source checkout cannot hide packaging mistakes.

Installation downloads declared Python dependencies. The verification itself
uses only the versioned synthetic fixture and does not request network data.
Passing it establishes this example's behavior, not production readiness or
performance. The package-install workflow repeats the check on Python 3.11/3.12.

For inspectable output files and a step-by-step explanation, use the
[OTLP example](../examples/otel/README.md). For database setup and its separate
credentials and migration requirements, read [evaluation history](EVALUATION_HISTORY.md).

If this check fails, report your operating system, Python version, exact commit,
command and sanitized diagnostic. Never include credentials or private traces.
