# Maintenance and user value

Sentinel helps engineers inspect an AI workflow before approving a change.
Its value is evidence they can reproduce, findings they can act on, and an
explicit boundary between observed behavior and claims that remain unproven.
It is a reference implementation with synthetic demonstrations. There is no
availability SLA, blanket safety certification, or promise of indefinite support.

## Ownership and support

The repository owner, Shawdaimarie, is the current maintainer. Use
[GitHub issues](https://github.com/Shawdaimarie/sentinel/issues) for reproducible
bugs and feature proposals. Follow [SECURITY.md](../SECURITY.md) for sensitive
reports; never attach credentials or unsanitized customer traces to public issues.
Response times and production support require a separate agreement.

The maintainer reviews existing weekly Dependabot proposals and stability
results, addresses actionable vulnerabilities, and checks release failures.
Once each month, review open defects, dependency/runtime support, documentation,
user feedback, and the cost of maintaining each feature. This cadence is an
operating plan; it is not a staffed monitoring or incident-response service.
Add a second qualified maintainer before promising coverage one person cannot
sustain. Keep independent review status explicit.

## Upgrade and compatibility

- Use immutable image digests and archive the matching source commit, signed
  provenance, SBOM, scan report, fixture definitions, and evaluation output.
  GitHub Actions artifacts expire; copy evidence needed for your retention period.
- `edge` follows main. Promote a reviewed digest into your environment only after
  replaying representative, permitted cases and exercising your integration.
- Python 3.11 and 3.12 are tested in CI. Published images currently target
  Linux amd64. Other runtimes and architectures have no claimed test coverage.
- Read [CHANGELOG.md](../CHANGELOG.md) before upgrading. Incomplete or errored
  runs now fail even when the weighted score is high; this deliberately tightens
  acceptance. Resolve missing telemetry or defects before approving a release.
- Treat suite/report schema identifiers as contracts. Preserve older evidence;
  review labels, thresholds, parser changes, and dependency changes together.
  A major schema change needs a new identifier and a documented migration.
- Base images and Actions use pinned references. Python dependency ranges still
  resolve at build time. Reuse a verified image digest to replay the same installed
  environment; rebuilding the same source is not a bit-for-bit guarantee.

## Release and recovery

PR checks cover quality, database behavior, cross-language audit verification,
security analysis, trace import, and packaged runtime behavior. Release jobs scan
the exact local image before pushing, verify signed provenance and SBOM, then
pull and smoke-test the published digest. A failed step means the release is
incomplete even if a tag already exists. Consumers must inspect the completed
run and verify the digest before promotion. See [RELEASING.md](../../RELEASING.md).

Before promotion, record the previous verified digest and configuration. Keep
that artifact available. If behavior regresses, stop promotion and preserve the
failed evidence. For the offline CLI, replay the same approved inputs with the
previous version in a separate output directory; compare failures and metadata.
For a running Aegis service, restore the prior compatible image/configuration
through the host's deployment process, preserving replay/revocation state and
audit logs. Do not erase state to make a rollback start. Database changes need
their own backup, compatibility, and restore check before an image rollback.
Submit the corrective or revert PR through the same protected checks.

These changes do not perform a database migration. The existing PostgreSQL
integration job exercises migrations and restore, but it does not verify any
customer's backups. A hosted deployment still needs an accountable operator,
TLS/access controls, persistent storage, monitoring, and a tested recovery path.

## Evidence of real value

Start with one consenting team and one release decision. Record its current
review time, known missed failures, setup cost, and support effort. Agree the
case set and success criteria before changing the workflow. Then compare the
same tasks after integration, including false alarms and maintenance burden.
Keep synthetic results separate from customer results and publish only with
permission. Use the [assessment proposal](RELIABILITY_ASSESSMENT_OFFER.md).

Continue only if the evidence shows useful failure detection or reduced review
effort without unacceptable operational cost. Revise or remove features that
users do not need. Income depends on customer demand, useful delivery, and sound
economics; test results alone establish none of those outcomes.

## Published image rescanning

[Published Image Rescan](../../.github/workflows/published-image-rescan.yml)
checks both current `edge` images weekly on Monday at 09:43 UTC, on manual
dispatch, and when a pull request changes the rescan or verification controls.
GitHub schedules are best effort; inspect the actual run time. This is a bounded
maintenance check, not continuous monitoring or an incident-response SLA.

The workflow resolves each tag once, verifies the resulting immutable digest's
provenance and SPDX attestation against `release.yml` and `refs/heads/main`,
then inventories those published bytes. It does not rebuild, run, sign, or
publish an image. The newly generated inventory is scan evidence, not a new
signed SBOM. No Docker Hub base-image pull is needed for this check.

The scanner requires a successful database update check and a database no older
than five days. The existing gate remains: active High/Critical findings with
an available fix fail the job, using the reviewed `.grype.yaml` exceptions.
The report records scanner and database metadata. Verification, download, or
scanner failures also fail the run; missing evidence is never a clean result.
See the [Grype configuration reference](https://oss.anchore.com/docs/reference/grype/configuration/)
for database validation behavior.

For a failed run, distinguish a confirmed vulnerability from an unavailable
registry, expired/stale database, or failed verification before choosing a fix.
Preserve the subject digest, verification log, inventory, and full scan report
from the `published-rescan-*` artifacts (30-day retention). Check package,
installed version, fix availability, and applicability before preparing a
corrective PR. Keep the release and branch gates intact. A retry is appropriate
only after a transient service failure has cleared; it does not fix a finding.

These scans cover the two current Linux amd64 `edge` digests, not every historical
release or a customer's deployed digest. Deployment owners must track their
own retained versions. A successful result is dated evidence against the
available vulnerability data, not a guarantee that an image is permanently safe.

## Remaining engineering work

Track fully locked Python build inputs, isolated signing, expanded platform
coverage, and independent reproduction as separate improvements. Release scans
describe build-time findings; published-image rescans provide later snapshots.
Prioritize work using actual deployment needs and failure evidence rather than
claiming that any release is permanently secure or maintenance-free.
