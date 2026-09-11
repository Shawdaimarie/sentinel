"""Prevent required merge checks from drifting away from runnable PR jobs."""

import itertools
import json
from collections import Counter
from pathlib import Path

import yaml


def test_required_checks_have_unconditional_pull_request_jobs() -> None:
    """Every protected context must have exactly one non-optional producer."""
    root = Path(__file__).resolve().parents[2]
    ruleset = json.loads((root / ".github/rulesets/main.json").read_text())
    required = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
    contexts = [item["context"] for item in required["parameters"]["required_status_checks"]]
    assert len(contexts) == len(set(contexts)), "Duplicate required contexts"
    producers: Counter[str] = Counter()

    for path in (root / ".github/workflows").glob("*.yml"):
        # BaseLoader retains `on` and matrix versions as strings (YAML 1.2 semantics).
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job_id, job in workflow["jobs"].items():
            matrix = job.get("strategy", {}).get("matrix", {})
            axes = list(matrix)
            if "include" in axes or "exclude" in axes:
                raise AssertionError(f"Extend context expansion for {path.name}: {job_id}")
            combinations = itertools.product(*(matrix[axis] for axis in axes))
            for values in combinations:
                name = job.get("name", job_id)
                for axis, value in zip(axes, values, strict=True):
                    name = name.replace("${{ matrix." + axis + " }}", value)
                if axes and "name" not in job:
                    name += " (" + ", ".join(values) + ")"
                if name not in contexts:
                    continue
                producers[name] += 1
                events = workflow["on"]
                assert "pull_request" in events, f"{name} does not run on PRs"
                assert not events["pull_request"], f"{name} filters PR events"
                assert "if" not in job, f"{name} can be skipped"
                assert job.get("continue-on-error", "false") == "false", name

    assert producers == Counter(contexts), "Required checks have missing or ambiguous producers"
