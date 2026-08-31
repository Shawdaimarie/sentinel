"""Policy engine.

The policy is a declarative document (see ``policy.yaml``) that states, for
each agent, which actions it may take, against which targets, and how many
times per run. The engine evaluates a proposed action against that document
and returns a decision with a stated reason. The default decision is deny.

The engine is deliberately small. Its value is that it is the *only* place
boundaries are decided, which makes those boundaries inspectable.
"""

from __future__ import annotations

import hashlib
import ipaddress
import socket
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field

Resolver = Callable[[str], list[str]]


class AgentPolicy(BaseModel):
    """Boundaries for a single agent."""

    purpose: str
    allowed_actions: list[str]
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    allow_private_networks: bool = False
    max_actions_per_run: int = Field(gt=0)
    thresholds: dict[str, Any] = Field(default_factory=dict)


class PolicyDocument(BaseModel):
    """The full policy as loaded from disk."""

    version: int
    defaults: dict[str, Literal["allow", "deny"]]
    agents: dict[str, AgentPolicy]


class Decision(BaseModel):
    """The outcome of evaluating a proposed action."""

    allowed: bool
    agent: str
    action: str
    target: str
    reason: str


class PolicyViolationError(RuntimeError):
    """Raised when an agent attempts an action the policy denies."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        super().__init__(
            f"{decision.agent} denied {decision.action} on {decision.target}: {decision.reason}"
        )


class PolicyIntegrityError(RuntimeError):
    """Raised when a loaded policy does not match its pinned fingerprint."""


def _system_resolver(host: str) -> list[str]:
    return sorted({str(info[4][0]) for info in socket.getaddrinfo(host, None)})


class Policy:
    """Evaluates proposed actions against a policy document.

    A ``Policy`` instance holds per-run counters, so one instance should be
    created per orchestrator run. ``fingerprint`` is the SHA-256 of the policy
    file as loaded, recorded in the audit log so a run can be tied to the
    exact boundaries that governed it.
    """

    def __init__(
        self,
        document: PolicyDocument,
        *,
        fingerprint: str = "",
        resolver: Resolver = _system_resolver,
    ) -> None:
        self.document = document
        self.fingerprint = fingerprint
        self._resolver = resolver
        self._counts: Counter[str] = Counter()

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        expected_sha256: str | None = None,
        resolver: Resolver = _system_resolver,
    ) -> Policy:
        raw_bytes = Path(path).read_bytes()
        fingerprint = hashlib.sha256(raw_bytes).hexdigest()
        if expected_sha256 is not None and fingerprint != expected_sha256.lower():
            raise PolicyIntegrityError(
                f"policy fingerprint {fingerprint} does not match pinned {expected_sha256}"
            )
        document = PolicyDocument.model_validate(yaml.safe_load(raw_bytes))
        return cls(document, fingerprint=fingerprint, resolver=resolver)

    def evaluate(self, agent: str, action: str, target: str) -> Decision:
        """Return a decision for the proposed action. Does not record it."""
        agent_policy = self.document.agents.get(agent)
        if agent_policy is None:
            return self._deny(agent, action, target, "agent is not declared in policy")

        if action not in agent_policy.allowed_actions:
            return self._deny(agent, action, target, "action is not in allowed_actions")

        if self._counts[agent] >= agent_policy.max_actions_per_run:
            return self._deny(agent, action, target, "max_actions_per_run exceeded")

        if action.startswith("http."):
            reason = self._check_http_target(agent_policy, target)
            if reason:
                return self._deny(agent, action, target, reason)

        if action.startswith("fs."):
            if not any(target.startswith(p) for p in agent_policy.allowed_paths):
                return self._deny(agent, action, target, "path not in allowed_paths")
            if ".." in Path(target).parts or Path(target).is_absolute():
                return self._deny(agent, action, target, "path traversal is not permitted")

        return Decision(allowed=True, agent=agent, action=action, target=target, reason="permitted")

    def _check_http_target(self, agent_policy: AgentPolicy, target: str) -> str | None:
        """Return a denial reason for an HTTP target, or None if acceptable."""
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"}:
            return f"scheme {parsed.scheme!r} is not permitted"
        if parsed.username or parsed.password:
            return "credentials in URL are not permitted"
        host = parsed.hostname or ""
        if not any(_host_matches(host, d) for d in agent_policy.allowed_domains):
            return f"host {host!r} not in allowed_domains"

        if not agent_policy.allow_private_networks:
            try:
                addresses = self._resolver(host)
            except OSError:
                return f"host {host!r} could not be resolved"
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if not ip.is_global:
                    return f"host {host!r} resolves to non-global address {address}"
        return None

    def record(self, decision: Decision) -> None:
        """Count an allowed action against the agent's per-run budget."""
        if decision.allowed:
            self._counts[decision.agent] += 1

    def thresholds(self, agent: str) -> dict[str, Any]:
        agent_policy = self.document.agents.get(agent)
        return dict(agent_policy.thresholds) if agent_policy else {}

    @staticmethod
    def _deny(agent: str, action: str, target: str, reason: str) -> Decision:
        return Decision(allowed=False, agent=agent, action=action, target=target, reason=reason)


def _host_matches(host: str, allowed: str) -> bool:
    """True if ``host`` is ``allowed`` or a subdomain of it."""
    host, allowed = host.lower(), allowed.lower()
    return host == allowed or host.endswith("." + allowed)
