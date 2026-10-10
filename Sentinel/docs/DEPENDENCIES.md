# Reproducing the container's Python dependencies

The Sentinel container uses reviewed package versions and SHA-256 checksums in
`requirements-runtime.txt` and `requirements-build.txt`. Rebuilding a commit
cannot silently select a newly published Python package. Missing pins, unavailable
wheels, and mismatched checksums stop the build; source distributions are refused.

The first runtime lock preserves all 12 dependency versions installed by
[release 38070886518](https://github.com/Shawdaimarie/sentinel/actions/runs/38070886518),
from source `905d3a61e4f6340b3dd9f9f7cb713d3ee42ad422`. The build tools are
explicitly selected in `requirements-build.in`; the generated build lock includes
their transitive dependencies. The pinned base image supplies the bootstrap pip.

## What is covered

The Dockerfile verifies downloaded build tools and runtime wheels against the
locks. It builds Sentinel with those tools, without build isolation or dependency
resolution, then installs from the local wheel directory with no index access.
The locally built Sentinel wheel is installed separately with `--no-deps`, followed
by `pip check`, so its declared requirements must be satisfied by the lock.

This covers the Python 3.12 container's default runtime and build dependencies.
Development tools and optional `history`/`llm` extras are separate, unlocked
environments. The package's declared Python 3.11+ compatibility ranges remain in
`pyproject.toml`; this lock is not a promise of identical resolution on every
Python version or platform. Published images still target Linux amd64.

This does not make the whole image bit-for-bit reproducible, certify package
safety, or freeze vulnerability information. Base images, OS contents, build
timestamps, and the build platform also matter. Continue using verified image
digests to reproduce an already published environment, and retain the release
SBOM and scan results. The vulnerability gate and scheduled image rescans remain
necessary.

## Check a candidate

From the repository root with Python 3.12:

```bash
python3.12 scripts/check-locked-install.py
```

The check creates temporary builder and runtime environments. Only the initial
tool installation and wheel downloads use a package index. It then builds and
installs without an index, checks the installed versions and dependency metadata,
rejects modified wheel bytes and a missing transitive pin, and runs the installed
20-case synthetic assessment from outside the checkout. Failure exits nonzero;
temporary environments and reports are removed. These are synthetic checks, not
customer or provider validation. Required Python 3.12 quality CI runs this check
before installing the separate development dependencies. Container preflight also
builds and scans the actual image; release jobs exercise its packaged behavior.

## Review and update a lock

From `Sentinel/`, use a separate Python 3.12 environment:

```bash
python3.12 -m venv .lock-venv
.lock-venv/bin/python -m pip install 'pip==26.2.1' 'pip-tools==7.6.2'
.lock-venv/bin/pip-compile --generate-hashes --allow-unsafe \
  --no-emit-index-url --no-emit-trusted-host --pip-args='--only-binary=:all:' \
  --output-file=requirements-runtime.txt pyproject.toml
.lock-venv/bin/pip-compile --generate-hashes --allow-unsafe \
  --no-emit-index-url --no-emit-trusted-host --pip-args='--only-binary=:all:' \
  --output-file=requirements-build.txt requirements-build.in
```

Without upgrade options, pip-compile reuses compatible existing pins. To update
one runtime dependency deliberately, add `--upgrade-package NAME` to its compile
command. For a build tool, edit its pin in `requirements-build.in`, then regenerate
the build lock. Review all resulting transitive changes and hashes together.
The generator itself is a maintainer tool, not part of a released runtime.

Hashes are collected from the package index during generation, so review is the
trust decision; checksums prevent subsequent substitution, not malicious code
already present in an approved release. Existing Dependabot pip reviews and
published-image scans provide update signals. An update is incomplete until the
locks, package requirements, installed check, required CI, and container security
preflight agree. Do not bypass hashes or the vulnerability gate to pass an update.

See pip's [secure installation guidance](https://pip.pypa.io/en/stable/topics/secure-installs/)
and [pip-tools documentation](https://pip-tools.readthedocs.io/en/stable/) for the
underlying mechanisms. Keep generator and Python version changes reviewable.
