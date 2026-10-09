# Releasing

This repo publishes two container images through
[`.github/workflows/release.yml`](.github/workflows/release.yml):

| Image | Source | Entrypoint |
|---|---|---|
| `ghcr.io/shawdaimarie/sentinel-eval` | [`Sentinel/Dockerfile`](Sentinel/Dockerfile) | `sentinel-eval` CLI |
| `ghcr.io/shawdaimarie/aegis-authorizer` | [`Aegis/Dockerfile`](Aegis/Dockerfile) | Aegis policy/audit daemon (`:8080`) |

## Triggers

- **Push to `main`** — builds and pushes both images tagged `edge`.
- **Push a tag matching `v*.*.*`** (e.g. `v0.7.0`) — builds and pushes both
  images tagged `latest`, `X.Y`, and `X.Y.Z`.
- **Manual** — `workflow_dispatch` from the Actions tab, for a rebuild without
  a new commit. Allowed only on `main` or a version tag.

Every image is also tagged `sha-<full commit SHA>` as a human-readable pointer
to its source commit. Tags, including this one, are mutable. The digest and
its attestations are the proof.

Before anything is published, the `release-guard` job fails closed if:

- the run is not on `main` or a `v*.*.*` tag, because a signature from
  `release.yml` must never cover unreviewed branch code;
- a version tag points at a commit that is not on `main`, and so never passed
  the protected-branch checks; or
- the tag does not equal the `version` in
  [`Sentinel/pyproject.toml`](Sentinel/pyproject.toml).

No secrets need to be configured: the workflow authenticates to GHCR with the
run's own `GITHUB_TOKEN` (`packages: write` permission, scoped to this repo).

## Cutting a versioned release

1. Bump `version` in [`Sentinel/pyproject.toml`](Sentinel/pyproject.toml) and
   add an entry to [`Sentinel/CHANGELOG.md`](Sentinel/CHANGELOG.md).
2. Merge that change to `main`.
3. Tag the merge commit and push the tag:

   ```bash
   git tag v0.7.0
   git push origin v0.7.0
   ```

4. Watch the [Release Images](https://github.com/Shawdaimarie/sentinel/actions/workflows/release.yml)
   run; on success both images are available at the tags above. The run
   summary records each image's digest and source commit. Copy those into the
   release notes: the digest, not the tag, is the release's identity.

## Supply-chain evidence

### Checking a candidate before merge

[`container-preflight.yml`](.github/workflows/container-preflight.yml) builds both
Dockerfiles on every pull request and applies the same SBOM scan and severity
policy as the release workflow. It has only `contents: read` permission and does
not log in to a registry, publish images, or sign attestations.

Both workflows allow each image's scan to finish independently. Even when a
scan fails, they retain the vulnerability report and its input SBOM as artifacts.
The run summary lists active, fixable High/Critical findings with installed and
fixed versions; the scanner remains the authority for the gate result. If no
report was produced, the summary says so rather than claiming a clean scan.

For a failing candidate, update the affected base image or dependency and rerun
the preflight. Keep image digests pinned and leave the vulnerability threshold
intact. A passing preflight is evidence about that build at that time: the release
rebuilds and rescans before publication because dependencies and vulnerability
databases can change between runs.

### Evidence carried by a published image

Sentinel's central rule is that a persuasive claim never substitutes for
evidence. The same rule applies to its own artifacts. A registry tag is a
mutable pointer. It says nothing about what was built, from which commit, or by
whom. Each published image therefore carries two signed attestations bound to
its digest, the content hash that cannot change without changing the image:

| Attestation | Predicate | What it binds |
|---|---|---|
| Build provenance | [SLSA v1](https://slsa.dev/spec/v1.0/provenance) | digest → repository, commit, ref, workflow file, trigger, runner |
| SBOM | [SPDX 2.3](https://spdx.github.io/spdx-spec/v2.3/) | digest → every OS and language package in the image |

Both are signed keylessly through Sigstore with the workflow's short-lived
OIDC identity. Because this repository is public, each signature is also
recorded in Sigstore's public Rekor transparency log. No long-lived
signing key exists to leak, rotate, or revoke. The attestations are stored in
GitHub's attestation API and pushed to GHCR next to the image.

The workflow does not only produce this evidence; it checks it. Before the job
succeeds, it runs the same verification a consumer would, with `release.yml`
pinned as the only accepted signer and the run's own ref as the source. An
image that cannot be verified fails the release.

### Release order

Nothing reaches the registry until its pre-publication gates pass. Post-publish
verification must also pass before consumers promote the release. For each image:

1. **Build** into the runner's local Docker daemon only.
   Run the packaged behavior checks with synthetic inputs: Sentinel assessment
   conformance, or Aegis startup and rejection of a request without credentials.
2. **Inventory** the local image as an SPDX SBOM.
3. **Gate** on that SBOM: any high or critical vulnerability with a fix
   available fails the release. The full report is uploaded either way.
4. **Push** the exact image that was scanned.
5. **Attest** provenance and the same SBOM to the pushed digest.
6. **Verify** both attestations as a consumer would.
7. **Pull and exercise** the verified digest with the same packaged behavior
   checks. A failure leaves the run unsuccessful even if tags were already pushed.

The signed SBOM and the vulnerability decision describe the same bytes.
Consumers should use only digests from completed successful release runs. The
checks establish bounded behavior; they do not validate a customer's workload,
hosting configuration, or availability. See the
[maintenance and recovery standard](Sentinel/docs/MAINTENANCE.md).

### Threats addressed

| Threat | Control | Residual risk |
|---|---|---|
| A tag is moved to a different image | Verify by digest; deploy by digest | A consumer who deploys by tag is not protected |
| An image is pushed by hand or by another workflow | Signer pinned to `release.yml` in this repository | Compromise of the repository's own workflow |
| Unreviewed branch code is signed as a release | `release-guard` allows only `main` and version tags | An administrator bypassing branch protection |
| A version tag is placed on an unmerged commit | Tag must be an ancestor of `main` | A tag on an older `main` commit is still allowed |
| Release version and package version disagree | Tag must equal `pyproject.toml` version | Only the Sentinel package version is checked |
| A known, fixable vulnerability ships | Pre-publish gate on high and critical findings with a fix | Unfixed and lower-severity findings are reported, not blocked |
| A base image or action tag is repointed upstream | Base images pinned by digest, actions by commit SHA | Dependabot update PRs still need human review |
| Unknown contents | Signed SPDX SBOM per digest | An inventory is not a vulnerability assessment |
| These controls are quietly weakened later | `tests/test_release_workflow.py` executes the guards and asserts every invariant above | Tests constrain this repository's files, not GitHub settings |

### Vulnerability exceptions

The gate blocks on findings you can act on: high or critical severity with a
fix available. Unfixable findings do not block, because a gate nobody can pass
gets bypassed. They stay visible in the uploaded report.

To ship with a known finding, add it to [`.grype.yaml`](.grype.yaml). Give the
reason it is not exploitable or is accepted, an owner, and a review date. The
file is code-owned, so an exception is a reviewed risk decision in a PR, never
a quiet way to make the build pass.

### Verifying an image yourself

```bash
scripts/verify-image.sh ghcr.io/shawdaimarie/sentinel-eval:v0.7.0
```

The script resolves the tag to a digest, verifies the provenance and the SBOM
with `release.yml` pinned as the signer, and prints the digest reference to
deploy. It needs `gh` and `docker` with buildx.

It infers the source ref only when the tag names it: `vX.Y.Z` means
`refs/tags/vX.Y.Z` and `edge` means `refs/heads/main`. Floating tags
(`latest`, `X.Y`), `sha-` tags, and digests can come from more than one ref,
so the script refuses to guess. State what you expect:

```bash
scripts/verify-image.sh ghcr.io/shawdaimarie/sentinel-eval:latest --source-ref refs/tags/v0.7.0
```

The equivalent manual check is:

```bash
gh attestation verify oci://ghcr.io/shawdaimarie/sentinel-eval@sha256:<digest> --repo Shawdaimarie/sentinel --signer-workflow Shawdaimarie/sentinel/.github/workflows/release.yml --source-ref refs/tags/v0.7.0
```

Add `--predicate-type https://spdx.dev/Document/v2.3` to verify the SBOM. Then
deploy by digest (`image@sha256:…`), not by tag, so that what runs is exactly
what was verified.

### What this proves, and what it does not

It proves that the image with this digest was built by this repository's
`release.yml` from the recorded commit and ref on GitHub-hosted
infrastructure. It proves the build used pinned base images and workflow actions, and that the published
bytes passed the vulnerability gate. Because the attestation is bound to the
digest, any change to the image breaks verification. It also proves what
packages the image contains.

This meets [SLSA Build Level 2](https://slsa.dev/spec/v1.0/levels): hosted
build, signed provenance. It does not claim Level 3, which would require the
signing to happen in an isolated reusable workflow that the build steps cannot
influence.

It does **not** prove that the source is free of defects, that the image is
free of vulnerabilities, or that the build is bit-for-bit reproducible. Python
dependencies use version ranges and are resolved during each build; they are not
locked by this pipeline. A
vulnerability database only knows what has been disclosed. OS packages
installed at build time come from Debian's archive, which is not pinned. The
remaining hardening steps, in order:

1. Move signing into an isolated reusable workflow to reach SLSA Build
   Level 3.
2. Re-scan published digests on a schedule, so a vulnerability disclosed after
   release is surfaced, not only ones known at release time.

## First-time GHCR visibility

GitHub Container Registry packages published by `GITHUB_TOKEN` are created
**private** by default, even in a public repo. After the first successful
run, open each package's settings
(`github.com/Shawdaimarie?tab=packages`) and set visibility to public (or
enable *Inherit access from source repository*) so `docker pull` works
without authentication.
