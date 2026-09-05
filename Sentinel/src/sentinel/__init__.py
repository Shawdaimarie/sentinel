"""Sentinel: governed execution, evaluation, data gates, automation, routing, and capsules.

Every agent action passes through policy evaluation and is written to an
append-only, hash-chained audit log before execution. Versioned evaluation cases
make correctness, safety, grounding, tool use, and efficiency observable.
Offline OpenTelemetry imports connect production traces to the same strict
AgentRun contract without contacting provider endpoints. Training-data quality
gates validate dataset structure, source notes, privacy posture, split hygiene,
and risk coverage before post-training or public benchmark claims. Benefit-gated
automation runs only allowlisted, high-value stability tasks and preserves human
control over identity-sensitive work. Value routing connects public proof,
private delivery boundaries, deployability, and ownership clarity. Deployment
capsules add hashed manifests for proof and delivery assets.
"""

__version__ = "0.6.0"
