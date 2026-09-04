"""Sentinel: governed execution, evaluation, automation, and value routing.

Every agent action passes through policy evaluation and is written to an
append-only, hash-chained audit log before execution. Versioned evaluation
cases make correctness, safety, grounding, tool use, and efficiency observable.
Offline OpenTelemetry imports connect production traces to the same strict
AgentRun contract without contacting provider endpoints. Benefit-gated
automation runs only allowlisted, high-value stability tasks and preserves
human control over identity-sensitive work. Value routing connects public proof,
private delivery boundaries, deployability, and ownership clarity.
"""

__version__ = "0.5.0"
