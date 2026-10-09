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

## Remaining engineering work

Track published-digest vulnerability rescans, fully locked Python build inputs,
isolated signing, expanded platform coverage, and independent reproduction as
separate improvements. Current scans describe disclosed findings at build time.
Prioritize work using actual deployment needs and failure evidence rather than
claiming that any release is permanently secure or maintenance-free.
