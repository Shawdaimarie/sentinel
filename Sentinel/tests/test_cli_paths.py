"""CLI artifact destinations must never destroy source evidence or each other."""

from pathlib import Path

import pytest

from sentinel.eval_cli import main as evaluate
from sentinel.trace_cli import main as import_trace


@pytest.mark.parametrize("destination", ["--output", "--manifest"])
@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
def test_import_preserves_input(
    tmp_path: Path, destination: str, alias: str,
) -> None:
    source = tmp_path / "source.json"
    original = Path("examples/otel/agent_trace.json").read_bytes()
    source.write_bytes(original)
    target = source
    if alias != "direct":
        target = tmp_path / "alias.json"
        if alias == "symlink":
            target.symlink_to(source)
        else:
            target.hardlink_to(source)
    output, manifest = tmp_path / "runs.jsonl", tmp_path / "manifest.json"
    args = ["--input", str(source), "--output", str(output), "--manifest", str(manifest)]
    args[args.index(destination) + 1] = str(target)
    assert import_trace(args) == 2
    assert source.read_bytes() == original
    assert not output.exists()
    assert not manifest.exists()


def test_import_rejects_colliding_artifacts(tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    assert import_trace([
        "--input", "examples/otel/agent_trace.json",
        "--output", str(target), "--manifest", str(target),
    ]) == 2
    assert not target.exists()


@pytest.mark.parametrize("source_name", ["cases", "runs", "baseline-runs"])
@pytest.mark.parametrize("destination", ["--report", "--json-out", "--comparison-json"])
def test_evaluation_preserves_all_inputs(
    tmp_path: Path, source_name: str, destination: str,
) -> None:
    sources = {}
    for name, fixture in [
        ("cases", "eval_cases.jsonl"), ("runs", "eval_runs.jsonl"),
        ("baseline-runs", "baseline_runs.jsonl"),
    ]:
        sources[name] = tmp_path / fixture
        sources[name].write_bytes((Path("examples") / fixture).read_bytes())
    originals = {path: path.read_bytes() for path in sources.values()}
    outputs = [tmp_path / name for name in ["report.md", "report.json", "comparison.json"]]
    args = [item for name, path in sources.items() for item in ["--" + name, str(path)]]
    for flag, path in zip(["--report", "--json-out", "--comparison-json"], outputs, strict=True):
        args.extend([flag, str(path)])
    args[args.index(destination) + 1] = str(sources[source_name])
    assert evaluate(args) == 2
    assert all(path.read_bytes() == data for path, data in originals.items())
    assert all(not path.exists() for path in outputs)


def test_evaluation_rejects_colliding_artifacts(tmp_path: Path) -> None:
    target = tmp_path / "report"
    assert evaluate([
        "--cases", "examples/eval_cases.jsonl", "--runs", "examples/eval_runs.jsonl",
        "--report", str(target), "--json-out", str(target),
    ]) == 2
    assert not target.exists()
