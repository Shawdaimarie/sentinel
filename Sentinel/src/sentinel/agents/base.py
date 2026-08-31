"""Base agent.

An agent proposes actions; it does not execute them directly. ``Agent.act``
evaluates the proposal against policy, writes the decision to the audit log,
and only then dispatches to the registered executor. A denied action raises
``PolicyViolationError`` and is still logged, so refusals are as visible as
successes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sentinel.audit import AuditLog, AuditRecord
from sentinel.policy import Policy, PolicyViolationError

Executor = Callable[[str, dict[str, Any]], Any]


class Agent:
    """Governed actor. Subclasses set ``name`` and use ``act`` for every effect."""

    name: str = "agent"

    def __init__(self, policy: Policy, audit: AuditLog) -> None:
        self.policy = policy
        self.audit = audit
        self._executors: dict[str, Executor] = {}

    def register(self, action: str, executor: Executor) -> None:
        """Bind an action name to the function that performs it."""
        self._executors[action] = executor

    def act(self, action: str, target: str, **payload: Any) -> tuple[AuditRecord, Any]:
        """Evaluate, log, then execute. Returns the audit record and the result."""
        decision = self.policy.evaluate(self.name, action, target)
        record = self.audit.append(
            agent=self.name,
            action=action,
            target=target,
            allowed=decision.allowed,
            reason=decision.reason,
            payload=payload,
        )
        if not decision.allowed:
            raise PolicyViolationError(decision)
        self.policy.record(decision)

        executor = self._executors.get(action)
        if executor is None:
            raise RuntimeError(f"{self.name} has no executor registered for {action}")
        return record, executor(target, payload)
