from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.audit import GENESIS_HASH, AuditError, AuditLog


def _append(log: AuditLog, n: int) -> None:
    for i in range(n):
        log.append(agent="t", action="a", target=f"target-{i}", allowed=True, reason="ok")


def test_chain_starts_at_genesis_and_verifies(audit: AuditLog) -> None:
    _append(audit, 3)
    records = list(audit.records())
    assert records[0].previous_hash == GENESIS_HASH
    assert audit.verify() == 3


def test_chain_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    _append(AuditLog(path), 2)
    _append(AuditLog(path), 2)
    assert AuditLog(path).verify() == 4


def test_content_tampering_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    _append(AuditLog(path), 3)
    lines = path.read_text().splitlines()
    record = json.loads(lines[1])
    record["allowed"] = False
    lines[1] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(AuditError, match="tampering"):
        AuditLog(path).verify()


def test_deletion_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    _append(AuditLog(path), 3)
    lines = path.read_text().splitlines()
    del lines[1]
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(AuditError):
        AuditLog(path).verify()
