# AI release reliability assessment

## Customer and problem

For a software team shipping one tool-using AI workflow: determine whether a
specific candidate change meets agreed behavioral requirements, and make the
supporting evidence easy to review and rerun.

The first engagement is a bounded pilot. The customer problem, delivery effort,
and willingness to pay must be validated before setting a price or promising
ongoing service. The existing synthetic demonstration establishes an inspection
path; it is not a customer result or certification.

## Proposed scope

- One workflow, one trace export format supported by the importer, and one
  candidate/baseline pair where paired records exist.
- Up to 20 agreed deterministic scenarios covering relevant task requirements,
  telemetry gaps, retries, forbidden actions, and operational budgets.
- A reproducible input inventory, evaluation configuration, findings report,
  prioritized remediation list, and operator handoff.
- One small remediation or integration, selected after findings and bounded by
  a written delivery-hours limit. Larger changes require revised scope.

Customer-approved sanitized exports or synthetic examples are required. Record
who approved use, permitted fields, storage location, access, retention,
deletion date, and whether anything may be published. Do not collect production
credentials or send customer traces to a model provider as part of this pilot.

## Acceptance criteria

Before work starts, customer and engineer agree the target behavior, cases,
failure consequences, thresholds, effort cap, fee, and delivery date.

1. Another engineer can reproduce the assessment with documented inputs and
   dependencies; missing inputs remain explicit findings.
2. Every agreed case has an observed outcome and supporting evidence.
3. Forbidden actions and incomplete or errored runs cannot be hidden by a high
   aggregate score. Unsupported claims remain limitations.
4. A delivered fix includes a before/after replay and a regression test.
5. The handoff includes operational limits, remaining risks, and a correction
   contact/process; customer acceptance is recorded separately from test results.

## Measurement plan

Measure the same workflow before and after using a recorded procedure:

| Measure | Evidence to collect |
|---|---|
| Review effort | Timed review tasks, sample size, and reviewer context |
| Failure detection | Agreed labeled examples, misses, and false alarms |
| Trace completeness | Observed missing fields and unsupported conventions |
| Operating burden | Setup time, delivery hours, maintenance and support hours |
| Runtime and cost | Recorded workload, versions, hardware, and billing basis |

Report synthetic fixture results, customer observations, and independent
reproductions separately. Publish a case study only with customer approval and
the supporting measurements.

## Discovery questions

- What was the last AI change your team could not confidently approve, and why?
- What evidence is reviewed today, by whom, and how long does it take?
- Which failure would be costly enough to justify an assessment?
- Can that failure be represented by an observable, permitted test case?
- Who owns the buying decision, data permission, and technical acceptance?
- What existing tool or process should this integrate with?

## Commercial decision

Quote only after reviewing a permitted sample and estimating all delivery and
support effort. Track collected payment, direct costs, operating costs, and
owner time. Offer recurring reviews only when releases create recurring work
that the customer values. Stop or revise the offer when demand or economics do
not support it.

## Exclusions

The pilot excludes production deployment, live model training, autonomous
account actions, blanket fairness or safety certification, penetration testing,
legal compliance opinions, and unlimited support. The customer retains release
authority. No outreach, purchase, deployment, or contract is executed by this
proposal.
