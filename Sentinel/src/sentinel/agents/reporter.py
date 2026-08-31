"""Reporter agent.

Compiles verifications and probe results into a Markdown report. Every
finding cites the audit sequence number of the action that produced it, so a
reader can trace any line of the report back to the logged evidence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agents.base import Agent
from sentinel.models import ProbeResult, Verdict, Verification


class Reporter(Agent):
    name = "reporter"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.register("fs.write", self._write)

    @staticmethod
    def _write(target: str, payload: dict[str, Any]) -> Path:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload["content"], encoding="utf-8")
        return path

    def report(
        self,
        verifications: list[Verification],
        probes: list[ProbeResult],
        audit_path: Path,
        output_dir: str = "reports/",
        failures: list[str] | None = None,
    ) -> Path:
        now = datetime.now(UTC)
        content = self.render(verifications, probes, audit_path, now, failures or [])
        target = f"{output_dir}{now:%Y-%m-%d}.md"
        _, path = self.act("fs.write", target, content=content)
        return Path(path)

    @staticmethod
    def render(
        verifications: list[Verification],
        probes: list[ProbeResult],
        audit_path: Path,
        now: datetime,
        failures: list[str] | None = None,
    ) -> str:
        failures = failures or []
        counts = {v: sum(1 for x in verifications if x.verdict == v) for v in Verdict}
        unhealthy = [p for p in probes if not p.healthy]

        lines = [
            f"# Sentinel report — {now:%Y-%m-%d}",
            "",
            f"Generated {now.isoformat(timespec='seconds')}. "
            f"Audit log: `{audit_path}`. Every finding cites its audit sequence.",
            "",
            "## Summary",
            "",
            f"- Claims examined: {len(verifications)}",
            f"- Supported: {counts[Verdict.SUPPORTED]}",
            f"- Unsupported: {counts[Verdict.UNSUPPORTED]}",
            f"- Unverifiable: {counts[Verdict.UNVERIFIABLE]}",
            f"- Controls probed: {len(probes)}; outside policy: {len(unhealthy)}",
            f"- Pages that could not be retrieved: {len(failures)}",
            "",
            "## Claims",
            "",
            "| # | Verdict | Claim | Rationale | Audit |",
            "|---|---------|-------|-----------|------:|",
        ]
        for i, v in enumerate(verifications, 1):
            claim = v.claim.text.replace("|", "\\|")
            lines.append(
                f"| {i} | {v.verdict.value} | {claim} | {v.rationale} | {v.audit_sequence} |"
            )

        lines += [
            "",
            "## Controls",
            "",
            "| Target | Status | Latency (ms) | State | Audit |",
            "|--------|-------:|-------------:|-------|------:|",
        ]
        for p in probes:
            status = p.status_code if p.status_code is not None else "—"
            latency = f"{p.latency_ms:.0f}" if p.latency_ms is not None else "—"
            lines.append(f"| {p.target} | {status} | {latency} | {p.detail} | {p.audit_sequence} |")

        if failures:
            lines += ["", "## Retrieval failures", ""]
            lines += [f"- {f}" for f in failures]

        lines += [
            "",
            "## Method",
            "",
            "A claim is *supported* only when a linked source contains the asserted quantity. "
            "*Unsupported* means no source is linked or the source does not contain it. "
            "*Unverifiable* means a source is linked but could not be retrieved. "
            "Controls are compared against thresholds declared in `policy.yaml`.",
            "",
        ]
        return "\n".join(lines)
