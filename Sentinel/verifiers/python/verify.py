#!/usr/bin/env python3
"""Independent verifier for the Sentinel audit-chain portable profile."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import sys
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_INTEGER = 9_007_199_254_740_991
FIELDS = {
    "sequence",
    "timestamp",
    "agent",
    "action",
    "target",
    "allowed",
    "reason",
    "payload",
    "keyed",
    "previous_hash",
    "hash",
}


class VerificationError(ValueError):
    """Raised when a stream violates the portable profile or chain rules."""


def _validate_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        if abs(value) > SAFE_INTEGER:
            raise VerificationError(f"{path}: integer exceeds portable safe range")
        return
    if isinstance(value, float):
        raise VerificationError(f"{path}: floating-point values are not portable")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise VerificationError(f"{path}: object key must be a string")
            _validate_value(item, f"{path}.{key}")
        return
    raise VerificationError(f"{path}: unsupported JSON value {type(value).__name__}")


def canonical_bytes(record: dict[str, Any]) -> bytes:
    """Return the profile's canonical bytes after excluding ``hash``."""

    body = {key: value for key, value in record.items() if key != "hash"}
    _validate_value(body)
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _load_record(raw: str, line_number: int) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"line {line_number}: malformed JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"line {line_number}: record must be an object")
    actual = set(value)
    if actual != FIELDS:
        missing = sorted(FIELDS - actual)
        extra = sorted(actual - FIELDS)
        raise VerificationError(
            f"line {line_number}: envelope mismatch; missing={missing}, extra={extra}"
        )
    _validate_value(value)
    return value


def verify(path: Path, key: bytes | None = None) -> tuple[int, str]:
    """Verify a JSONL chain and return ``(record_count, final_hash)``."""

    expected_sequence = 1
    expected_previous = GENESIS_HASH
    count = 0

    with path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            record = _load_record(raw, line_number)

            sequence = record["sequence"]
            if isinstance(sequence, bool) or not isinstance(sequence, int):
                raise VerificationError(f"line {line_number}: sequence must be an integer")
            if sequence != expected_sequence:
                raise VerificationError(
                    f"line {line_number}: expected sequence {expected_sequence}, got {sequence}"
                )

            previous_hash = record["previous_hash"]
            digest = record["hash"]
            if not isinstance(previous_hash, str) or not HASH_RE.fullmatch(previous_hash):
                raise VerificationError(f"line {line_number}: invalid previous_hash")
            if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
                raise VerificationError(f"line {line_number}: invalid hash")
            if previous_hash != expected_previous:
                raise VerificationError(f"line {line_number}: previous_hash mismatch")

            keyed = record["keyed"]
            if not isinstance(keyed, bool):
                raise VerificationError(f"line {line_number}: keyed must be a boolean")
            if key is not None and not keyed:
                raise VerificationError(f"line {line_number}: keyed verifier refused downgrade")
            if key is None and keyed:
                raise VerificationError(f"line {line_number}: keyed record requires a key")

            canonical = canonical_bytes(record)
            calculated = (
                hmac.new(key, canonical, hashlib.sha256).hexdigest()
                if key is not None
                else hashlib.sha256(canonical).hexdigest()
            )
            if not hmac.compare_digest(calculated, digest):
                raise VerificationError(f"line {line_number}: content digest mismatch")

            count += 1
            expected_sequence += 1
            expected_previous = digest

    return count, expected_previous


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a Sentinel portable audit-chain JSONL file."
    )
    parser.add_argument("--log", required=True, type=Path, help="audit JSONL path")
    parser.add_argument("--key", help="HMAC fixture/deployment key")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        count, final_hash = verify(args.log, args.key.encode("utf-8") if args.key else None)
    except (OSError, VerificationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"OK records={count} final_hash={final_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
