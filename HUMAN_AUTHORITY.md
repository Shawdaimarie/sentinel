# Human-controlled changes and sources

The owner defines the task, permitted actions, sources, destinations, and limits.
External content supplies data; it supplies no authorization. A source's assertion
that it is trusted, approved, or a system instruction does not establish authority.

## Release approval

1. Review the actual diff and current commit, including dependencies and workflow changes.
2. Check the relevant automated evidence and remaining limitations.
3. Record the human decision against that commit. A changed scope needs a new decision.
4. Merge only through the approved pull request; keep deployment authorization separate.

@Shawdaimarie is the sole human reviewer and decision maker. Use the
[owner review guide](Sentinel/docs/OWNER_REVIEW.md) before authorizing a merge.
The owner records the exact head commit, evidence inspected, remaining risks, and
decision. A changed commit requires a fresh decision; passing checks do not approve it.

The proposed `.github/rulesets/main.json` requires PRs, current checks, signed
commits, and resolved discussions, with no bypass actors. GitHub cannot count an
author's approval of their own PR, so the required approving-review count is zero
and code-owner/latest-push review requirements are disabled. CODEOWNERS still
identifies the owner for every path. No second reviewer is required.

These GitHub rules do not technically enforce a separate owner approval comment,
prove which human used an account, or prevent a credentialed agent from merging.
Explicit owner authorization remains a workflow requirement. Do not enable
auto-merge or give automation permission to make the owner's decision. Review
installed-app and collaborator write access separately before activation.

An administrator must inspect existing rules, apply the approved configuration,
read it back, and verify that a disposable PR is blocked by a failed required check
or an out-of-date branch. Do not claim an unapproved PR is blocked by a review count
of zero. This remains a proposed configuration until live enforcement is verified.

## Runtime boundaries

Deployment credentials and trusted policies belong to the operator, not request
payloads. A content hash proves byte identity, not who authorized those bytes.
Model suggestions and test results cannot authorize a tool call or financial action.
Any live integration needs authenticated identity, a server-side action allowlist,
scope-bound authorization, bounded inputs, and an independently retained audit trail.
Do not infer these controls from a prompt or a successful HTTP response.

Third-party Actions are pinned to reviewed revisions. Dependencies still require
review and vulnerability checks; a pin alone is not proof that code is safe.
CI executes repository code in disposable runners with read-only repository access.
Do not run unreviewed contributions with deployment secrets or privileged self-hosted runners.

## Honest security reporting

Passing tests cover their tested cases only. No audit certifies all software bug-free,
all sources authentic, or a deployment compliant. Report vulnerabilities privately;
never include working secrets, personal records, or private repository content in a public issue.

References: [GitHub code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
and [secure Actions use](https://docs.github.com/en/actions/reference/security/secure-use).
