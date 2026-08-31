"""Orchestrator.

Runs the agents in sequence — crawl, verify, probe, report — sharing one
policy instance (so per-run budgets are enforced across agents) and one
audit log (so the run is a single, contiguous chain).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import httpx

from sentinel.agents import Crawler, Prober, Reporter, Verifier
from sentinel.audit import AuditLog
from sentinel.http import RetrievalError
from sentinel.models import ProbeResult, Verification
from sentinel.policy import Policy, PolicyViolationError


@dataclass
class RunResult:
    report_path: Path | None
    verifications: list[Verification] = field(default_factory=list)
    probes: list[ProbeResult] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def run(
    *,
    policy_path: Path,
    audit_path: Path,
    pages: list[str],
    controls: list[str],
    use_llm: bool = False,
    policy_sha256: str | None = None,
) -> RunResult:
    policy = Policy.load(policy_path, expected_sha256=policy_sha256)
    audit = AuditLog(audit_path)
    result = RunResult(report_path=None)

    # Bind this run to the exact policy that governs it.
    audit.append(
        agent="orchestrator",
        action="policy.load",
        target=str(policy_path),
        allowed=True,
        reason="run start",
        payload={"sha256": policy.fingerprint, "audit_keyed": audit.keyed},
    )

    crawler = Crawler(policy, audit)
    verifier = Verifier(policy, audit, use_llm=use_llm)
    prober = Prober(policy, audit)
    reporter = Reporter(policy, audit)

    try:
        for page in pages:
            try:
                for claim in crawler.crawl(page):
                    result.verifications.append(verifier.verify(claim))
            except PolicyViolationError as exc:
                result.violations.append(str(exc))
            except (httpx.HTTPError, RetrievalError) as exc:
                result.failures.append(
                    f"{page}: {exc.__class__.__name__}: {str(exc).splitlines()[0]}"
                )

        for control in controls:
            try:
                result.probes.append(prober.probe(control))
            except PolicyViolationError as exc:
                result.violations.append(str(exc))

        try:
            result.report_path = reporter.report(
                result.verifications, result.probes, audit_path, failures=result.failures
            )
        except PolicyViolationError as exc:
            result.violations.append(str(exc))
    finally:
        crawler.close()
        verifier.close()
        prober.close()

    return result
