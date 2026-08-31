from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sentinel.agents import Reporter
from sentinel.agents.base import Agent
from sentinel.audit import AuditLog
from sentinel.models import Claim, ProbeResult, Verdict, Verification
from sentinel.policy import Policy, PolicyViolationError


class Echo(Agent):
    name = "crawler"

    def __init__(self, policy: Policy, audit: AuditLog) -> None:
        super().__init__(policy, audit)
        self.register("http.get", lambda target, payload: f"fetched {target}")


def test_allowed_action_is_logged_then_executed(policy: Policy, audit: AuditLog) -> None:
    record, result = Echo(policy, audit).act("http.get", "https://essentialdigitalsolution.com/")
    assert result == "fetched https://essentialdigitalsolution.com/"
    assert record.allowed and record.sequence == 1
    assert audit.verify() == 1


def test_denied_action_is_logged_and_raises(policy: Policy, audit: AuditLog) -> None:
    with pytest.raises(PolicyViolationError):
        Echo(policy, audit).act("http.get", "https://example.com/")
    records = list(audit.records())
    assert len(records) == 1 and not records[0].allowed


def test_reporter_writes_only_within_allowed_path(policy: Policy, audit: AuditLog, tmp_path: Path):
    reporter = Reporter(policy, audit)
    with pytest.raises(PolicyViolationError):
        reporter.report([], [], audit.path, output_dir=str(tmp_path) + "/")


def test_report_cites_audit_sequences() -> None:
    claim = Claim(text="Uptime of 99.99% over 12 months.", source_url="https://x", audit_sequence=7)
    verification = Verification(
        claim=claim, verdict=Verdict.UNSUPPORTED, rationale="no evidence", audit_sequence=7
    )
    probe = ProbeResult(
        target="https://x",
        status_code=200,
        latency_ms=120.0,
        healthy=True,
        detail="within thresholds",
        audit_sequence=9,
    )
    text = Reporter.render(
        [verification], [probe], Path("audit.jsonl"), datetime(2026, 8, 29, tzinfo=UTC)
    )
    assert "| 1 | unsupported |" in text and "| 7 |" in text
    assert "| 9 |" in text


def test_crawler_extracts_claims_at_block_boundaries(policy: Policy, audit: AuditLog) -> None:
    from sentinel.agents.crawler import _QUANTITY, _SENTENCE_SPLIT, _TextExtractor

    parser = _TextExtractor()
    parser.feed(
        "<title>Site</title><h1>Assurance</h1><p>Uptime of 99.99% held. See the "
        '<a href="https://x/e">report</a>.</p><p>No numbers here.</p>'
    )
    text = " ".join(parser.chunks)
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    claims = [s for s in sentences if _QUANTITY.search(s)]
    assert claims == ["Uptime of 99.99% held."]
    assert parser.links == ["https://x/e"]
