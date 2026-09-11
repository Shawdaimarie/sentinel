# Release safeguards

The desired GitHub configuration is versioned in
[`main.json`](../../.github/rulesets/main.json). Committing this file does **not**
activate protection. A repository administrator must apply it in GitHub and
verify the effective rules before issue #29 can be considered complete.

## Protection policy

The ruleset targets `main`, requires pull requests and current passing checks,
blocks force pushes and branch deletion, requires verified commit signatures,
and requires review conversations to be resolved. It has no bypass actors.

The initial single-maintainer policy requires zero independent approvals.
This makes PRs and their evidence mandatory without preventing the owner from
merging their own work. It does not claim independent human review. When a
second qualified maintainer is available, change the approval count to one and
enable last-push approval in a reviewed configuration update.

Required contexts are **job names**, not workflow titles:

| Workflow | Required contexts |
| --- | --- |
| CI | `quality-and-evaluation (3.11)`, `quality-and-evaluation (3.12)`, `Portable audit conformance`, `container-build` |
| Aegis CI | `aegis-go`, `aegis-container` |
| Trace Import | `otlp-to-evaluation` |
| CodeQL | `Analyze python`, `Analyze go` |
| Stability Automation | `stability` |

All contexts are bound to GitHub Actions (app ID 15368), verified against
the repository's check-run API. There is currently no workflow named
"Universal Verification"; the independent runtime verifiers run in
`Portable audit conformance`. Do not require a nonexistent check.

Required workflows run for every pull request, including documentation-only
changes. Do not add path filters or conditional skips to these jobs. Change
job names and the ruleset together, and confirm the new names in a successful
PR run before updating the live ruleset.

## Activation

1. Let the safeguards PR finish all ten required checks, including `stability`.
   Confirm the check names and that they originate from GitHub Actions.
2. Inspect existing repository and inherited rulesets first. Update the matching
   ruleset if one exists instead of creating a duplicate.
3. In repository Settings → Rules → Rulesets, import `main.json` using
   **New ruleset → Import a ruleset**, or apply the same payload through the
   [GitHub rulesets API](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset)
   with repository Administration write access.
4. Confirm enforcement is **Active**, the target is `refs/heads/main`, and
   the bypass list is empty. Read back the saved rules and compare them with
   the versioned file. Importing a file alone is not evidence of enforcement.
5. Confirm GitHub's merge panel blocks an incomplete or failing required check
   and an out-of-date branch. Use a disposable PR for failure testing; never
   probe protection by force pushing or deleting `main`.
6. Use signed branch commits or a GitHub-verified merge path. Verify the actual
   resulting commit signature; an unsigned local commit does not become
   signed merely because tests passed. Do not rewrite existing `main` history.
7. Record the ruleset URL, activation time, tested PR and resulting commit SHA
   in issue #29. Close it only after enforcement has been verified.

The managed GitHub connector cannot administer rulesets. If it is the only
available connection, prepare and test the configuration and leave activation
explicitly pending for a repository administrator.

## Release procedure

1. Open a focused PR linked to an issue. Update the branch against current
   `main`, resolve conflicts, and let the checks rerun.
2. Inspect failed diagnostics and evaluation reports. A green fixture-based
   check demonstrates its covered cases, not production safety.
3. Review dependency upgrades in their existing Dependabot PRs. Handle major
   upgrades separately and verify compatibility before merging.
4. Merge only with all required contexts passing and all discussions resolved.
5. Verify the resulting `main` commit and its checks. Record the commit SHA,
   dependency versions and evaluation evidence with the release.

## Recovery and exceptions

Prefer a revert PR through the same checks. For a GitHub Actions outage, hold
the release rather than representing missing checks as successful.

If an emergency requires a temporary ruleset change, the repository owner
records the incident, exact setting, rationale, approver, expiry, affected
commit and compensating verification. Restore the versioned policy immediately
afterward and verify it by reading the live rules. Administrators can still
edit rulesets; an empty bypass list does not remove that administrative power.

## Next milestone

After release enforcement is verified, implement evaluation history under
issue #12: versioned PostgreSQL migrations, digest-keyed idempotent imports,
read-only release comparison, and an exercised backup/restore path. Keep this
work in Sentinel and preserve the current evaluator contract.
