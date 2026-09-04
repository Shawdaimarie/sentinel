from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from verify import VerificationError, verify

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "spec" / "vectors"


class PortableVerifierTests(unittest.TestCase):
    def test_accepts_unkeyed_vector(self) -> None:
        count, final_hash = verify(VECTORS / "unkeyed.jsonl")
        manifest = json.loads((VECTORS / "manifest.json").read_text())
        self.assertEqual(count, 3)
        self.assertEqual(final_hash, manifest["files"]["unkeyed.jsonl"]["final_hash"])

    def test_accepts_keyed_vector(self) -> None:
        count, final_hash = verify(VECTORS / "keyed.jsonl", b"sentinel-demo-key")
        manifest = json.loads((VECTORS / "manifest.json").read_text())
        self.assertEqual(count, 3)
        self.assertEqual(final_hash, manifest["files"]["keyed.jsonl"]["final_hash"])

    def test_keyed_vector_requires_key(self) -> None:
        with self.assertRaisesRegex(VerificationError, "requires a key"):
            verify(VECTORS / "keyed.jsonl")

    def test_keyed_verifier_rejects_unkeyed_downgrade(self) -> None:
        with self.assertRaisesRegex(VerificationError, "refused downgrade"):
            verify(VECTORS / "unkeyed.jsonl", b"sentinel-demo-key")

    def test_changed_record_is_rejected(self) -> None:
        lines = (VECTORS / "unkeyed.jsonl").read_text().splitlines()
        record = json.loads(lines[1])
        record["reason"] = "rewritten after approval"
        lines[1] = json.dumps(record, separators=(",", ":"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered.jsonl"
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(VerificationError, "content digest mismatch"):
                verify(path)

    def test_deleted_middle_record_is_rejected(self) -> None:
        lines = (VECTORS / "unkeyed.jsonl").read_text().splitlines()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deleted.jsonl"
            path.write_text("\n".join([lines[0], lines[2]]) + "\n")
            with self.assertRaisesRegex(VerificationError, "expected sequence 2"):
                verify(path)


if __name__ == "__main__":
    unittest.main()
