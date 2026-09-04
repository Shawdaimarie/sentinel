"""Sentinel: governed execution and deterministic evaluation for AI agents.

Every agent action passes through policy evaluation and is written to an
append-only, hash-chained audit log before execution. Versioned evaluation
cases make correctness, safety, grounding, tool use, and efficiency observable
in local development and CI.
"""

__version__ = "0.2.0"
