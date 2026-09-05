# Dataset Card: Sentinel Agent Safety Examples

## Summary

This JSONL dataset contains synthetic training and evaluation examples for
tool-using AI-agent safety, grounding, privacy, human approval, cost control,
regulated-workflow boundaries, and coding-agent review.

## Intended Use

Use this dataset to test Sentinel's Training Data Quality Gate and to provide a
small public proof base for future AI-training experiments. The examples are
intended for evaluation design, data-quality validation, baseline measurement,
and controlled post-training experiments.

## Non-Goals

This dataset does not prove that any model or agent is broadly safe. It does
not provide legal, medical, financial, hiring, or compliance advice. It does
not contain private client material, real personal data, credentials, account
data, or assessment answers.

## Source

All examples are synthetic. They were written to represent documented risk
classes such as prompt injection, unauthorized tool use, secret exposure,
fabricated evidence, missing citations, missing human approval, cost runaway,
retry loops, privacy boundaries, and unsupported production claims.

## Privacy And Release Status

The dataset is designed for public proof:

- personal data: not included;
- credentials: not included;
- private client data: not included;
- account-bound information: not included;
- public release: allowed for every included row.

## Splits

Rows are assigned to `train`, `validation`, and `test` splits. Split assignment
is illustrative for the v0.1 dataset and should be reviewed before any
post-training experiment.

## Known Limitations

- The examples are synthetic and small.
- The dataset is not a red-team benchmark by itself.
- It does not represent all industries, jurisdictions, languages, or user
  populations.
- It tests declared example quality, not learned model behavior.
- A production dataset would require broader sourcing, bias review, external
  privacy review, and repeated evaluation.

## Responsible Expansion

Future versions should add more diverse task families, source quality labels,
model-output pairs, reviewer annotations, difficulty levels, and repeated-trial
metadata while preserving the public/private boundary.
