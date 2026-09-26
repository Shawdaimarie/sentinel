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

### Threats addressed

| Threat | Control | Residual risk |
|---|---|---|
| A tag is moved to a different image | Verify by digest; deploy by digest | A consumer who deploys by tag is not protected |
| An image is pushed by hand or by another workflow | Signer pinned to `release.yml` in this repository | Compromise of the repository's own workflow |
| Unreviewed branch code is signed as a release | `release-guard` allows only `main` and version tags | An administrator bypassing branch protection |
| A version tag is placed on an unmerged commit | Tag must be an ancestor of `main` | A tag on an older `main` commit is still allowed |
| Release version and package version disagree | Tag must equal `pyproject.toml` version | Only the Sentinel package version is checked |
| Unknown contents | Signed SPDX SBOM per digest | An inventory is not a vulnerability assessment |

### Verifying an image yourself

Resolve the tag to a digest, then verify the digest:

```bash
docker buildx imagetools inspect ghcr.io/shawdaimarie/sentinel-eval:latest --format '{{.Manifest.Digest}}'
```

```bash
gh attestation verify oci://ghcr.io/shawdaimarie/sentinel-eval@sha256:<digest> --repo Shawdaimarie/sentinel --signer-workflow Shawdaimarie/sentinel/.github/workflows/release.yml --source-ref refs/tags/v0.7.0
```

`--source-ref` confirms the image was built from the release tag you expect.
Use `refs/heads/main` for an `edge` image. Add
`--predicate-type https://spdx.dev/Document/v2.3` to verify the SBOM instead
of the provenance. Then deploy by digest (`image@sha256:…`), not by tag, so
that what runs is exactly what was verified.

### What this proves, and what it does not

It proves that the image with this digest was built by this repository's
`release.yml`, from the recorded commit and ref, on GitHub-hosted
infrastructure. Because the attestation is bound to the digest, any change to
the image breaks verification. It also proves what packages the image
contains.

This meets [SLSA Build Level 2](https://slsa.dev/spec/v1.0/levels): hosted
build, signed provenance. It does not claim Level 3, which would require the
signing to happen in an isolated reusable workflow that the build steps cannot
influence.

It does **not** prove that the source is free of defects, that dependencies
are free of known vulnerabilities, or that the build is reproducible. Base
images (`python:3.12-slim`, `golang:1.23`) and third-party actions are
referenced by tag, not digest, so they are trusted inputs rather than verified
ones. The next hardening steps, in order:

1. Pin base images and actions by digest, with Dependabot keeping them current.
2. Scan the SBOM for known vulnerabilities and block releases on
   high-severity findings.
3. Move signing into an isolated reusable workflow to reach SLSA Build
   Level 3.

## First-time GHCR visibility

GitHub Container Registry packages published by `GITHUB_TOKEN` are created
**private** by default, even in a public repo. After the first successful
run, open each package's settings
(`github.com/Shawdaimarie?tab=packages`) and set visibility to public (or
enable *Inherit access from source repository*) so `docker pull` works
without authentication.
