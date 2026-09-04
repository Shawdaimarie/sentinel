import json
from pathlib import Path

import pytest

from sentinel.automation import (
    load_catalog,
    markdown_report,
    required_failures,
    result_payload,
    run_catalog,
)


def write_catalog(path: Path, command: list[str] | None = None, score: float = 0.91) -> None:
    payload = [
        {
            "id": "quality.compile",
            "title": "Compile Python sources",
            "layer": "quality",
            "mode": "automated",
            "required": True,
            "benefit_score": score,
            "command": command or ["python", "-m", "compileall", "-q", "."],
            "rationale": "Compilation catches syntax regressions before release.",
            "evidence_paths": ["reports/automation/stability.md"],
            "timeout_seconds": 30,
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_catalog_loads_and_executes_allowlisted_command(tmp_path: Path) -> None:
    (tmp_path / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    catalog = tmp_path / "tasks.json"
    write_catalog(catalog)

    tasks = load_catalog(catalog)
    results = run_catalog(tasks, cwd=tmp_path, execute=True, min_benefit_score=0.85)

    assert len(results) == 1
    assert results[0].status == "passed"
    assert required_failures(results) == []


def test_low_benefit_required_task_is_reported_as_failure(tmp_path: Path) -> None:
    catalog = tmp_path / "tasks.json"
    write_catalog(catalog, score=0.50)

    tasks = load_catalog(catalog)
    results = run_catalog(tasks, cwd=tmp_path, execute=True, min_benefit_score=0.85)

    assert results[0].status == "skipped"
    assert required_failures(results) == [results[0]]
    assert "below required" in results[0].reason


def test_catalog_rejects_non_allowlisted_or_shell_like_commands(tmp_path: Path) -> None:
    catalog = tmp_path / "unsafe.json"
    write_catalog(catalog, command=["bash", "-lc", "echo unsafe"])

    with pytest.raises(ValueError, match="not allowlisted"):
        load_catalog(catalog)

    catalog.write_text(
        json.dumps(
            [
                {
                    "id": "quality.bad",
                    "title": "Bad command",
                    "layer": "quality",
                    "mode": "automated",
                    "required": True,
                    "benefit_score": 0.90,
                    "command": ["pytest", "-q", "tests && rm -rf ."],
                    "rationale": "Unsafe shell tokens must be rejected.",
                    "evidence_paths": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsafe shell token"):
        load_catalog(catalog)


def test_planning_mode_does_not_execute_required_tasks(tmp_path: Path) -> None:
    catalog = tmp_path / "tasks.json"
    write_catalog(catalog)

    tasks = load_catalog(catalog)
    results = run_catalog(tasks, cwd=tmp_path, execute=False, min_benefit_score=0.85)

    assert results[0].status == "planned"
    assert required_failures(results) == [results[0]]


def test_payload_and_markdown_report_required_gate(tmp_path: Path) -> None:
    catalog = tmp_path / "tasks.json"
    write_catalog(catalog)
    tasks = load_catalog(catalog)
    results = run_catalog(tasks, cwd=tmp_path, execute=True, min_benefit_score=0.85)

    payload = result_payload(results, min_benefit_score=0.85)
    markdown = markdown_report(results, min_benefit_score=0.85)

    assert payload["schema_version"] == "sentinel.automation.v1"
    assert payload["required_passed"] is True
    assert "All required automation tasks passed." in markdown


def test_duplicate_task_ids_are_rejected(tmp_path: Path) -> None:
    catalog = tmp_path / "duplicate.json"
    task = {
        "id": "quality.compile",
        "title": "Compile Python sources",
        "layer": "quality",
        "mode": "automated",
        "required": True,
        "benefit_score": 0.90,
        "command": ["python", "-m", "compileall", "-q", "."],
        "rationale": "Compilation catches syntax regressions before release.",
        "evidence_paths": [],
    }
    catalog.write_text(json.dumps([task, task]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate task ids"):
        load_catalog(catalog)


def test_manual_tasks_are_skipped_and_cannot_declare_commands(tmp_path: Path) -> None:
    catalog = tmp_path / "manual.json"
    catalog.write_text(
        json.dumps(
            [
                {
                    "id": "candidate.mercor",
                    "title": "Mercor assessment",
                    "layer": "governance",
                    "mode": "manual",
                    "required": False,
                    "benefit_score": 0.95,
                    "command": [],
                    "rationale": "Live assessments require candidate identity and consent.",
                    "evidence_paths": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    tasks = load_catalog(catalog)
    results = run_catalog(tasks, cwd=tmp_path, execute=True, min_benefit_score=0.85)

    assert results[0].status == "skipped"
    assert "manual task" in results[0].reason

    catalog.write_text(
        json.dumps(
            [
                {
                    "id": "candidate.bad",
                    "title": "Manual with command",
                    "layer": "governance",
                    "mode": "manual",
                    "required": False,
                    "benefit_score": 0.95,
                    "command": ["pytest", "-q"],
                    "rationale": "Manual tasks cannot be executed by the automation runner.",
                    "evidence_paths": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="manual tasks must not declare commands"):
        load_catalog(catalog)
