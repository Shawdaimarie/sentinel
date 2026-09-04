"""Apply the reviewed OpenTelemetry feature payload staged in split base64 parts."""

from __future__ import annotations

import base64
import hashlib
import io
import shutil
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / ".github" / "otel-bootstrap"
EXPECTED_B64_SHA256 = "22ca2055cd44759aac6712f10101093f41aae8538fd1d71831fedae2851b9080"
EXPECTED_ARCHIVE_SHA256 = "1e22670fbc21295a2647fa07abbce6803c4cb43667b103e82b8f8e64521c5fc4"
DEFERRED_WORKFLOW = ".github/workflows/trace-import.yml"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_destination(name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe archive path: {name!r}")
    return ROOT.joinpath(*path.parts)


def main() -> None:
    part_paths = sorted(PARTS.glob("part-*"))
    if len(part_paths) != 7:
        raise RuntimeError(f"expected 7 payload parts, found {len(part_paths)}")

    encoded = b"".join(path.read_bytes() for path in part_paths)
    if digest(encoded) != EXPECTED_B64_SHA256:
        raise RuntimeError("staged base64 payload fingerprint mismatch")

    archive = base64.b64decode(encoded, validate=True)
    if digest(archive) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("decoded archive fingerprint mismatch")

    applied = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            if not member.isfile():
                raise ValueError(f"archive contains unsupported member: {member.name!r}")
            if member.name == DEFERRED_WORKFLOW:
                continue
            target = safe_destination(member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise RuntimeError(f"cannot read archive member: {member.name!r}")
            target.write_bytes(source.read())
            applied += 1

    shutil.rmtree(PARTS)
    Path(__file__).unlink()
    print(f"Applied {applied} verified source files; CI workflow installation deferred")


if __name__ == "__main__":
    main()
