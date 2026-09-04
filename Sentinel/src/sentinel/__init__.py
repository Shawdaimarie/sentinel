"""Sentinel: governed execution, evaluation, and trace normalization.

Every agent action passes through policy evaluation and is written to an
append-only, hash-chained audit log before execution. Versioned evaluation
cases make correctness, safety, grounding, tool use, and efficiency observable.
Offline OpenTelemetry imports connect production traces to the same strict
AgentRun contract without contacting provider endpoints.
"""

__version__ = "0.3.0"
