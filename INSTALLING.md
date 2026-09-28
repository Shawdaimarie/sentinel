# Installing a released image

How to get a Sentinel or Aegis release you can trust, check that it works, and
recover if something goes wrong. The run commands here are the ones CI
executes on every pull request (`image-smoke-test` job), so they are tested,
not illustrative.

## 1. Requirements

| Tool | Version | Used for |
|---|---|---|
| Docker with buildx | 24 or newer | Resolving digests and running images |
| [GitHub CLI](https://cli.github.com) | 2.49 or newer | Verifying attestations |
| curl, bash | any recent | The smoke test |
| A clone of this repository | the release tag | Example configuration and the scripts below |

```bash
git clone --branch v0.7.0 https://github.com/Shawdaimarie/sentinel.git
```

```bash
cd sentinel
```

Use the tag that matches the image version you are installing.

## 2. Verify before you run

Never run an image you have not verified. The script resolves the tag to its
digest and checks the signed build provenance and SBOM against this
repository's release workflow and the release tag:

```bash
scripts/verify-image.sh ghcr.io/shawdaimarie/sentinel-eval:v0.7.0
```

```bash
scripts/verify-image.sh ghcr.io/shawdaimarie/aegis-authorizer:v0.7.0
```

Each prints the verified reference in the form `image@sha256:…`. Use those
digest references from here on, never the tag. A tag can be moved; a digest
cannot. See [RELEASING.md](RELEASING.md#supply-chain-evidence) for what
verification proves and what it does not.

## 3. Smoke-test the verified images

```bash
bash scripts/smoke-test-images.sh ghcr.io/shawdaimarie/sentinel-eval@sha256:<digest> ghcr.io/shawdaimarie/aegis-authorizer@sha256:<digest>
```

It passes only if:

- `sentinel-eval` runs the bundled example suite to a passing release gate,
  inside a read-only container, as its non-root user;
- Aegis loads its configuration, answers its discovery endpoints, and
  **refuses** an authorization request that carries no capability (HTTP 403).

## 4. Run

### sentinel-eval

It runs on a read-only filesystem. Mount your inputs read-only, and run as
your own user so it can write reports to a directory you own:

```bash
mkdir -p reports
```

```bash
docker run --rm --read-only --tmpfs /tmp --user "$(id -u):$(id -g)" -v "$PWD/Sentinel/examples:/workspace/examples:ro" -v "$PWD/reports:/workspace/reports" ghcr.io/shawdaimarie/sentinel-eval@sha256:<digest> --cases examples/eval_cases.jsonl --runs examples/eval_runs.jsonl
```

It prints a one-line summary ending in `gate=PASS` or `gate=FAIL` and writes
`reports/evaluation.md` and `reports/evaluation.json`. It exits non-zero when
the gate fails. Run `--help` for every option.

### aegis-authorizer

Aegis ships with **no policy or keys**. It refuses to start without explicit
configuration, which is deliberate. Supply a policy and a trust bundle, give
it a writable directory for its audit and replay-state logs, and bind it to
the host's loopback interface only:

```bash
docker run --rm --read-only -v "$PWD/Aegis/examples:/config:ro" -v aegis-data:/data -p 127.0.0.1:8080:8080 ghcr.io/shawdaimarie/aegis-authorizer@sha256:<digest> --policy /config/policy.json --trust-bundle /config/trust_bundle.json --audit-log /data/aegis-decisions.jsonl --state-log /data/aegis-state.jsonl --listen 0.0.0.0:8080
```

- `--listen 0.0.0.0:8080` is required *inside* the container so that the port
  mapping can reach it. `-p 127.0.0.1:8080:8080` keeps it off other hosts.
  Expose it more widely only behind authentication and TLS.
- The container runs as UID 65532. The image's `/data` directory belongs to
  that user, so a named volume such as `aegis-data` inherits the right
  ownership. If you bind-mount a host directory instead, make it writable by
  UID 65532. Keep the volume persistent: it holds the decision audit log and
  the replay and revocation state.
- The example files are synthetic and cannot sign capabilities. Replace them
  with your own policy and trusted issuers before real use.

## 5. Compatibility

| Item | Supported |
|---|---|
| Platform | `linux/amd64` only. On Apple Silicon, Docker runs it under emulation, which is slower. |
| sentinel-eval runtime | Python 3.14 in the image; the package supports Python 3.11+ |
| Aegis | Static Go binary on an empty (`scratch`) base; no shell in the image |
| Configuration | Match the repository tag to the image version. Example files may change between versions. |
| Evaluation history | The PostgreSQL schema is versioned by its migrations; see [EVALUATION_HISTORY.md](Sentinel/docs/EVALUATION_HISTORY.md) |

## 6. Recovery

| Situation | What to do |
|---|---|
| `verify-image.sh` fails | **Do not run the image.** Check that you passed the right tag and source ref. If it still fails, report it privately following [SECURITY.md](SECURITY.md). |
| Smoke test fails on a verified image | Do not deploy it. Open an issue with the script output and the digest. |
| A new release misbehaves | Roll back by deploying the previous **verified digest**. Keep the digest of every release you deploy; the Release Images run summary lists it. |
| Aegis will not start | Run the same command with `--check-config`. It prints the first configuration error and exits without serving. |
| Aegis state or audit volume lost | Replay protection and revocations recorded in the state log are lost with it. Restore the volume from backup before serving traffic, and treat any gap in the audit chain as an incident. |
| Evaluation history database lost | Follow the restore procedure in [EVALUATION_HISTORY.md](Sentinel/docs/EVALUATION_HISTORY.md). |

## Status of this guide

The run and smoke-test commands are exercised by CI against freshly built
images on every pull request. End-to-end verification against a *published*
release by someone other than the maintainer is tracked in
[#55](https://github.com/Shawdaimarie/sentinel/issues/55) and is not yet
complete.
