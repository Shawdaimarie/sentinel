# Installing and recovering container releases

Use a verified image digest, configuration from its source commit, and storage
that survives container replacement. Sentinel evaluates synthetic traces offline;
Aegis authorizes capabilities and records decisions. Publishing their images does
not create a hosted service.

For a Python installation without Docker, start with the
[wheel-based first-run guide](Sentinel/docs/FIRST_RUN.md).

## 1. Choose a successful release

Requirements: Docker with buildx and a running engine, Git, Bash, curl, Python 3,
and [GitHub CLI](https://cli.github.com/) 2.49 or newer for attestation verification.
Published images target `linux/amd64`; an ARM host needs compatible emulation.
The Sentinel image uses Python 3.12. Aegis is a static Go binary in a `scratch`
image with no shell, running as UID/GID `65532:65532`.

Open a successful [Release Images run](https://github.com/Shawdaimarie/sentinel/actions/workflows/release.yml).
Record its source commit and the image digests from its summary. Check that the
vulnerability gate, attestation verification, and published-image smoke checks
passed. A tag such as `edge` can move, including while another release runs.

```bash
git clone https://github.com/Shawdaimarie/sentinel.git
cd sentinel
```

Check out the source commit recorded by that release before using its examples
and scripts. Set `SENTINEL_IMAGE` and `AEGIS_IMAGE` to the full recorded references,
each in the form `ghcr.io/shawdaimarie/NAME@sha256:DIGEST`. The commands below
deliberately require those variables to be set.

## 2. Verify and pull the exact digests

For a release from `main`:

```bash
bash scripts/verify-image.sh "${SENTINEL_IMAGE:?Set the recorded Sentinel digest reference}" --source-ref refs/heads/main
bash scripts/verify-image.sh "${AEGIS_IMAGE:?Set the recorded Aegis digest reference}" --source-ref refs/heads/main
docker pull --platform linux/amd64 "$SENTINEL_IMAGE"
docker pull --platform linux/amd64 "$AEGIS_IMAGE"
```

For a tagged release, use its actual `refs/tags/v...` source ref instead. The
verifier checks signed build provenance and the SBOM against this repository's
release workflow and the supplied source **ref**. It does not enforce a particular
source commit: retain the successful run's commit-to-digest record alongside the
verification output. See [supply-chain evidence](RELEASING.md#supply-chain-evidence)
for the scope and limits of these checks. Stop if verification fails.

## 3. Test the packaged behavior

From the matching checkout, with a Docker engine that can run `linux/amd64`:

```bash
bash scripts/smoke-image.sh sentinel-eval "$SENTINEL_IMAGE"
bash scripts/smoke-image.sh aegis-authorizer "$AEGIS_IMAGE"
```

The checks run non-root containers with read-only root filesystems, dropped
capabilities, and no new privileges. Sentinel runs the bundled 20-case synthetic
assessment without network access. The Aegis check creates a fresh Docker volume,
sends a request without credentials, and requires an `invalid_token` denial with
an audit sequence and hash. It removes the container, starts a new one on the same
volume, and verifies that the first record remains and the second links to it.
A denial caused by `audit_unavailable` fails the check.

The smoke script removes only the containers and fresh test volume it creates.
It does not use an application volume. CI also builds the prior layout without
the writable `/data` directory and requires the check to reject its audit failure.
These checks exercise missing-credential denials and audit continuity, not valid
capability authorization, replay-state persistence, backup restoration, or a
production identity integration.

## 4. Run Sentinel or a local Aegis example

For Sentinel inputs, durable report output, and the synthetic-data boundary, use
the [published-container assessment instructions](Sentinel/examples/reliability_assessment/README.md#run-the-published-container).

Aegis needs an explicit policy, trusted public keys, and durable storage for both
audit and replay/revocation state. The following is a local synthetic example.
Choose a new volume name for a first installation; `aegis-data` below is an example,
not a request to overwrite an existing installation.

```bash
docker volume create aegis-data
docker run -d --name aegis-local --platform linux/amd64 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$PWD/Aegis/examples,dst=/examples,readonly" \
  --mount type=volume,src=aegis-data,dst=/data \
  -p 127.0.0.1:8080:8080 \
  "${AEGIS_IMAGE:?Set the verified Aegis digest reference}" \
  --policy /examples/policy.json --jwks /examples/jwks.json \
  --audit-log /data/decisions.jsonl --state-log /data/state.jsonl \
  --listen 0.0.0.0:8080
curl --silent --show-error -H 'Content-Type: application/json' \
  -d '{}' http://127.0.0.1:8080/v1/authorize
```

Expect HTTP 403, `allowed: false`, `reason: "invalid_token"`, a positive
`audit_sequence`, and an `audit_hash`. HTTP 403 alone does not prove the audit write
succeeded. The example keys are synthetic public keys; they provide no private
key for signing capabilities. Follow the [Aegis configuration guide](Aegis/README.md)
to configure real issuers and policies before handling real requests.

The service listens on all interfaces inside the container so Docker can reach
it, while the host mapping is loopback-only. Keep broader access behind the
authentication and TLS controls of the environment in which you operate it.

### Storage ownership and replacement

The image contains `/data` owned by `65532:65532` with mode `0750`. A fresh empty
named volume inherits that directory's ownership through Docker's default volume
initialization. See [Docker volume behavior](https://docs.docker.com/engine/storage/volumes/).
Do not use `volume-nocopy` for this initialization.

An existing volume or bind mount retains its own ownership; updating the image
does not repair it. If it is not writable by UID/GID 65532, stop the service, make
a protected backup, and have the operator correct that specific storage path's
ownership. Do not make it world-writable, run Aegis as root, or delete the logs to
work around the failure. Use only one Aegis process per pair of file logs.

To replace the local example, stop and remove `aegis-local`, then rerun its command
with the same volume and a newly verified compatible digest. Removing a container
does not remove its named volume. Do not run `docker volume rm` or volume-pruning
commands against the application data.

## 5. Recover deliberately

| Symptom | Action |
| --- | --- |
| Verification fails | Check the digest, repository, source ref, and successful release record. Do not run the unverified image. Follow [SECURITY.md](SECURITY.md) for a suspected integrity issue. |
| Packaged smoke check fails | Keep the previous working release. Report the digest and sanitized output; exclude keys, credentials, and real user data. |
| Configuration fails to load | Inspect container logs. `--check-config` validates configuration and reads existing state; it does **not** prove that a future audit/state write can succeed. |
| Denial says `audit_unavailable` | Treat logging as unavailable, not a successful policy test. Check volume ownership, free space, and audit integrity before serving traffic. |
| New image regresses behavior | Stop it, preserve both logs, verify the previous digest, and check its compatibility with the stored configuration and state before replacement. |
| Audit or state storage is lost or damaged | Stop serving requests and restore a consistent protected backup of both logs and configuration. Lost replay/revocation state and audit gaps require investigation. Do not silently start empty logs. |
| Evaluation-history database is lost | Follow the separate [history-store backup and restore guidance](Sentinel/docs/EVALUATION_HISTORY.md). |

Keep a deployment record with the verified digest, source commit, configuration
version, backup location, and operator. Rehearse restoration before relying on
this service: container replacement continuity is not a disaster-recovery test.

## Verification status

CI exercises the shared packaged checks on pull requests; the release workflow
also runs them against the published, attestation-verified digests. A successful
run is evidence for those specific checks. Independent installation by someone
other than the maintainer remains tracked in
[#55](https://github.com/Shawdaimarie/sentinel/issues/55); automated checks do not
complete that external validation.
