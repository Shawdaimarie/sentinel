"""Sentinel: a governed multi-agent system for continuous verification.

Every agent action passes through a policy evaluation and is written to an
append-only, hash-chained audit log before execution. There is no unaudited
code path.
"""

__version__ = "0.1.1"
