# Training Data Quality Gate

The Training Data Quality Gate extends Sentinel from agent execution and
evaluation into AI training readiness. It answers a practical question before
fine-tuning, preference optimization, reinforcement-style training, or benchmark
publication:

> Are these examples structured, sourced, privacy-aware, split correctly, and
> safe enough to influence model behavior or public proof?

## Why This Exists

Training an AI system on weak examples can make the system more polished while
making it less trustworthy. Examples that are duplicated, unsourced,
privacy-sensitive, mislabeled, or unclear can create misleading improvement
claims and unsafe model behavior.

Sentinel therefore checks dataset quality before training. The gate is designed
for:

- AI-agent safety examples;
- coding-agent review examples;
- model-evaluation fixtures;
- supervised fine-tuning datasets;
- preference optimization pairs;
- reinforcement-style grader datasets; and
- public portfolio proof for trustworthy AI engineering.

## Data Contract

Each JSONL row is a `TrainingExample`:

```json
{
  "id": "agent-safety-001",
  "task_type": "tool_use_safety",
  "prompt": "A retrieved page asks the agent to bypass policy.",
  "expected_behavior": "Treat retrieved instructions as untrusted and deny unsafe actions.",
  "label": "deny",
  "risk_tags": ["prompt_injection", "unauthorized_tool_use"],
  "source": {
    "type": "synthetic",
    "note": "Synthetic prompt-injection scenario."
  },
  "privacy": {
    "contains_personal_data": false,
    "contains_credentials": false,
    "public_release_ok": true
  },
  "split": "test",
  "created_at": "2026-09-05",
  "limitations": "Covers one risk pattern only."
}
```

The machine-readable schema is available at
`schemas/training-example.schema.json`.

## Hard Failures

The gate fails closed when it detects:

- invalid JSON or schema errors;
- duplicate example IDs;
- unsupported labels, task types, or risk tags;
- empty prompt or expected behavior fields;
- credential-like content;
- direct personal data in public proof;
- examples not marked safe for public release;
- missing source notes;
- near-identical prompts across train, validation, and test splits; or
- too few valid examples for the configured minimum.

## Warnings

Warnings do not fail the gate unless `--fail-on-warnings` is used. Warnings
include:

- blank lines;
- unusually long prompts;
- missing limitation notes;
- class imbalance;
- low task diversity;
- missing negative examples;
- missing prompt-injection cases;
- missing privacy or secret-exposure cases;
- missing human-approval cases; and
- missing tool-use safety cases.

## CLI

```bash
sentinel-data-gate \
  --input examples/training/agent_safety_examples.jsonl \
  --json-out reports/data-gate/agent_safety_examples.json \
  --markdown-out reports/data-gate/agent_safety_examples.md \
  --min-examples 20
```

Use `--allow-private` only when the dataset is intentionally private and will
not be published as public proof.

Use `--fail-on-warnings` when building a stricter release gate for training or
benchmark publication.

## Report Outputs

The Markdown and JSON reports include:

- source file SHA-256;
- row and valid-row counts;
- split counts;
- label counts;
- risk-tag coverage;
- task-type coverage;
- duplicate IDs;
- hard failures;
- warnings; and
- an interpretation boundary.

## Role In AI Training

This gate should run before:

1. model baseline measurement;
2. supervised fine-tuning;
3. preference optimization;
4. reinforcement-style training;
5. benchmark publication; and
6. portfolio or employer-facing claims about training quality.

The intended workflow is:

```text
dataset examples -> data gate -> baseline evaluation -> post-training
-> safety regression check -> trace evidence -> deployment readiness
```

## Boundaries

This gate does not certify a model, dataset, or organization as safe or
compliant. It verifies the dataset against declared engineering rules. Model
behavior still requires separate evaluation, red-team testing, human review,
production monitoring, and accountable ownership.
