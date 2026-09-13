# Sole-owner engineering review

@Shawdaimarie is the sole reviewer. The objective is rigorous, repeatable judgment,
not a claim of equivalence to another maintainer or a guaranteed profile score.

## Review the problem first

Identify who encounters the problem and reproduce it when practical. State the
expected and actual behavior. Check that the patch solves one logical problem
and does not introduce unrelated changes. Read the diff, including configuration,
dependencies, generated artifacts, and tests; a summary is not the diff.

## Review the implementation and evidence

1. **Correctness:** trace the normal path and important failure paths. Confirm the
   test would catch the original defect. Check boundaries, malformed input,
   duplicate requests, concurrency, and partial failure where applicable.
2. **Security and authority:** identify who may perform each action, where inputs
   cross trust boundaries, and whether denial occurs before side effects. Review
   secrets, logging, dependency changes, and workflow permissions explicitly.
3. **Compatibility:** inspect command, schema, API, and migration changes. Explain
   impact on existing users and any deprecation or migration path.
4. **Measured tradeoffs:** require repeatable measurements for performance claims,
   including workload, environment, variation, and costs. Avoid conclusions from
   a single synthetic score.
5. **Recovery:** identify how to revert or recover without losing trusted data.
   Destructive migrations require a tested backup/restore path.
6. **Evidence:** inspect required check results on the current head SHA. Distinguish
   passed tests, skipped tests, source inspections, and untested live behavior.
   A green build does not resolve an unexplained design or security concern.

Mark an item not applicable only with a reason. Hold changes with unresolved
high-impact risks, failed required checks, or unsupported claims. Prefer a smaller
patch when the reasoning cannot be evaluated confidently.

## Record your decision

The human owner completes this record in the PR after review. An assistant may
prepare links and questions but must not impersonate the owner or fill an approval.

```text
Reviewed head SHA: <full commit SHA>
Problem and expected result: <summary>
Evidence inspected: <checks, reproduction, measurements>
Security and compatibility findings: <findings or justified N/A>
Recovery path: <revert or tested recovery>
Remaining limits: <what is not verified>
Decision: <hold / request changes / approve merge of this SHA>
```

Any push invalidates the prior decision. Use the expected-head SHA on a delegated
merge. Release publication and deployment are separate decisions.

## Enforcement boundary

GitHub cannot count an author's own approving review. The proposed rules require
PRs and passing checks but zero formal approvals; they do not enforce this record
or prove a human operated the account. Preserve sole-owner control of credentials,
review write-capable apps and collaborators, and avoid automatic merging. Do not
call this independent review or a cryptographic proof of human authorization.

This approach adapts problem descriptions, logically scoped patches, quantified
tradeoffs, and responses to review from the
[Linux contribution guide](https://docs.kernel.org/process/submitting-patches.html).
It keeps Sentinel's own workflow and the owner's chosen review model.
