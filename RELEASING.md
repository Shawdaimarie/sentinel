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
  a new commit.

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
   run; on success both images are available at the tags above.

## First-time GHCR visibility

GitHub Container Registry packages published by `GITHUB_TOKEN` are created
**private** by default, even in a public repo. After the first successful
run, open each package's settings
(`github.com/Shawdaimarie?tab=packages`) and set visibility to public (or
enable *Inherit access from source repository*) so `docker pull` works
without authentication.
