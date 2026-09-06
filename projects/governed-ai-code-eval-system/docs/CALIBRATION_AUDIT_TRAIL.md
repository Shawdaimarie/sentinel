# Calibration Audit Trail

## Purpose

The calibration audit trail preserves model-comparison decisions so repeated AI evaluation work can be reviewed over time. It turns one-time candidate ranking into reusable evidence for AI engineering, code-agent evaluation, and secure model-output review.

## What The Application Stores

The live application stores calibration snapshots locally in the browser. It does not send records to a server and does not store candidate source code.

Each snapshot contains:

- Review name.
- Timestamp.
- Winning candidate.
- Score spread.
- Consensus signal.
- Calibration weights.
- Candidate ranks, scores, and gates.

## Why It Matters

AI-sector evaluation work increasingly depends on traceability: reviewers need to show not only which model output won, but why it won and what tradeoffs were accepted. A local audit trail supports that proof without adding unnecessary account, database, or data-retention risk.

## Operating Standard

Use the audit trail when:

- Comparing two or more model-generated candidates.
- Adjusting review weights for safety, correctness, data reliability, or operations.
- Capturing reviewer decision evidence before updating GitHub, Handshake, or a portfolio entry.
- Preparing examples for future dashboard or pull-request integration.

## Export Standard

The browser app can copy a compact audit JSON record. The Python package can emit calibration JSONL through `calibration_report_to_jsonl()`.

Keep exports sanitized. Do not include private source code, confidential prompts, account details, restricted links, or proprietary task text in public artifacts.

## Claim Boundary

Accurate positioning:

This system includes a local calibration audit trail for preserving model-comparison decisions and reviewer evidence.

Do not describe the audit trail as regulated compliance storage, official certification, or external approval unless those controls are separately implemented and verified.
