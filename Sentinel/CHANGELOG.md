# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-08-31

### Security

- `verify-audit` now rejects a keyed-to-unkeyed downgrade. Previously the
  `keyed` flag inside each record selected the verification algorithm, so an
  attacker able to rewrite the log could flip it to `false` on every record,
  recompute plain SHA-256 forward, and pass keyed verification. A verifier
  holding a key now refuses any unkeyed record. Found while writing
  [sentinel-spec](https://github.com/Shawdaimarie/sentinel-spec); covered by
  `test_keyed_verifier_rejects_downgrade_to_unkeyed` and spec vector 10.

### Changed

- A log is now entirely keyed or entirely unkeyed. Introducing a key requires
  starting a new log file.

### Added

- The audit-chain format is specified language-neutrally in sentinel-spec,
  with conformance vectors and verifiers in Python, TypeScript, and Go.
  `README.md`, `ARCHITECTURE.md`, and `SECURITY.md` link to it.

## [0.1.0] - 2026-08-29

Initial implementation.
