"""Shared data types passed between agents."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Claim(BaseModel):
    """A factual assertion extracted from a public page."""

    text: str
    source_url: str
    evidence_urls: list[str] = Field(default_factory=list)
    audit_sequence: int


class Verdict(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNVERIFIABLE = "unverifiable"


class Verification(BaseModel):
    """The verifier's judgement on a single claim."""

    claim: Claim
    verdict: Verdict
    rationale: str
    audit_sequence: int


class ProbeResult(BaseModel):
    """Observed state of a single control."""

    target: str
    status_code: int | None
    latency_ms: float | None
    healthy: bool
    detail: str
    audit_sequence: int
