from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from sentinel.audit import AuditLog, AuditRecord

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "spec" / "vectors"


@pytest.mark.parametrize(
    ("filename", "key"),
    [
        ("unkeyed.jsonl", None),
        ("keyed.jsonl", b"sentinel-demo-key"),
    ],
)
def test_audit_record_matches_portable_vectors(filename: str, key: bytes | None) -> None:
    records = [
        AuditRecord.model_validate_json(line)
        for line in (VECTORS / filename).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(records) == 3
    for record in records:
        assert record.compute_hash(key) == record.hash


@pytest.mark.parametrize(
    ("filename", "key"),
    [
        ("unkeyed.jsonl", None),
        ("keyed.jsonl", b"sentinel-demo-key"),
    ],
)
def test_audit_log_verifies_portable_vectors(
    tmp_path: Path,
    filename: str,
    key: bytes | None,
) -> None:
    target = tmp_path / filename
    shutil.copyfile(VECTORS / filename, target)

    assert AuditLog(target, key=key).verify() == 3
