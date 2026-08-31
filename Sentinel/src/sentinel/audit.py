"""Append-only, hash-chained audit log with optional keyed authentication.

Each record carries the digest of the previous record, so any modification or
deletion after the fact breaks the chain and is detected by ``verify``.

When a key is supplied, digests are HMAC-SHA256 rather than plain SHA-256.
The distinction matters: a plain chain can be silently recomputed by anyone
able to rewrite the file; a keyed chain cannot be recomputed without the key.
The key is read from ``SENTINEL_AUDIT_KEY`` and should be held outside the
host that writes the log — a secrets manager, a hardware token, or an
operator's possession.

This is not a substitute for shipping records to append-only external storage
in production; it is the minimum structure that makes an audit trail
meaningful on a single host.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

GENESIS_HASH = "0" * 64
KEY_ENV = "SENTINEL_AUDIT_KEY"


class AuditRecord(BaseModel):
    """A single logged event."""

    sequence: int
    timestamp: str
    agent: str
    action: str
    target: str
    allowed: bool
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)
    keyed: bool = False
    previous_hash: str
    hash: str = ""

    def compute_hash(self, key: bytes | None) -> str:
        body = self.model_dump(exclude={"hash"})
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if self.keyed:
            if key is None:
                raise AuditError(f"record {self.sequence} is keyed but no key was supplied")
            return hmac.new(key, encoded, hashlib.sha256).hexdigest()
        return hashlib.sha256(encoded).hexdigest()


class AuditError(RuntimeError):
    """Raised when the audit chain fails verification."""


def _key_from_env() -> bytes | None:
    value = os.environ.get(KEY_ENV)
    return value.encode("utf-8") if value else None


class AuditLog:
    """Append-only JSONL log with a SHA-256 or HMAC-SHA256 chain."""

    def __init__(self, path: str | Path, *, key: bytes | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._key = key if key is not None else _key_from_env()
        self._sequence, self._last_hash = self._tail()

    @property
    def keyed(self) -> bool:
        return self._key is not None

    def append(
        self,
        *,
        agent: str,
        action: str,
        target: str,
        allowed: bool,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> AuditRecord:
        record = AuditRecord(
            sequence=self._sequence + 1,
            timestamp=datetime.now(UTC).isoformat(timespec="milliseconds"),
            agent=agent,
            action=action,
            target=target,
            allowed=allowed,
            reason=reason,
            payload=payload or {},
            keyed=self.keyed,
            previous_hash=self._last_hash,
        )
        record.hash = record.compute_hash(self._key)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        self._sequence = record.sequence
        self._last_hash = record.hash
        return record

    def records(self) -> Iterator[AuditRecord]:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield AuditRecord.model_validate_json(line)

    def verify(self) -> int:
        """Walk the chain. Returns the record count; raises on any break."""
        expected_previous = GENESIS_HASH
        count = 0
        for record in self.records():
            count += 1
            if record.sequence != count:
                raise AuditError(f"sequence gap at record {count}: found {record.sequence}")
            if record.previous_hash != expected_previous:
                raise AuditError(f"chain break at record {count}: previous_hash mismatch")
            if self.keyed and not record.keyed:
                # The record must not choose the algorithm. A verifier holding a key
                # refuses unkeyed records; otherwise an attacker who rewrites the file
                # can flip ``keyed`` to false and recompute plain SHA-256 forward.
                raise AuditError(f"downgrade at record {count}: verifier is keyed, record is not")
            if not hmac.compare_digest(record.compute_hash(self._key), record.hash):
                raise AuditError(f"content tampering at record {count}: digest mismatch")
            expected_previous = record.hash
        return count

    def _tail(self) -> tuple[int, str]:
        last: AuditRecord | None = None
        for record in self.records():
            last = record
        return (last.sequence, last.hash) if last else (0, GENESIS_HASH)
