"""Safe automation planning and execution for Sentinel stability tasks.

The automation layer is intentionally conservative: it can run only explicit,
low-risk commands from a catalog, captures evidence, and refuses shell-based or
identity-sensitive work. The objective is repeatable leverage, not unchecked
autonomy.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypeAlias, cast

TaskLayer: TypeAlias = Literal[
    "quality",
    "security",
    "evaluation",
    "observability",
    "portfolio",
    "governance",
]
TaskStatus: TypeAlias = Literal["planned", "skipped", "passed", "failed"]
TaskMode: TypeAlias = Literal["automated", "manual"]

ALLOWED_EXECUTABLES: frozenset[str] = frozenset(
    {
        "python",
        "ruff",
        "mypy",
        "pytest",
        "pip-audit",
        "sentinel-eval",
        "sentinel-code-review",
        "sentinel-import-otel",
    }
)
ALLOWED_PYTHON_MODULES: frozenset[str] = frozenset({"compileall"})
UNSAFE_ARGUMENT_TOKENS: tuple[str, ...] = ("&&", ";", "|", "`", "$(", "\n", "\r")


@dataclass(frozen=True)
class AutomationTask:
    """One repeatable task that can be planned or executed under guardrails."""

    id: str
    title: str
    layer: TaskLayer
    mode: TaskMode
    required: bool
    benefit_score: float
    command: tuple[str, ...]
    rationale: str
    evidence_paths: tuple[str, ...]
    timeout_seconds: int = 180


@dataclass(frozen=True)
class TaskResult:
    """Execution or planning result for one task."""

    task: AutomationTask
    status: TaskStatus
    returncode: int | None
    stdout: str
    stderr: str
    reason: str

    @property
    def successful(self) -> bool:
        """Whether a required automation gate can count this result as passing."""

        return self.status == "passed"


def _require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return cast(Mapping[str, object], value)


def _require_text(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{context} must not be blank")
    return normalized


def _require_bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{context} must be a boolean")
    return value


def _require_score(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be a number in [0.0, 1.0]")
    score = float(value)
    if score < 0.0 or score > 1.0:
        raise ValueError(f"{context} must be in [0.0, 1.0]")
    return score


def _require_positive_int(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context} must be a positive integer")
    if value <= 0:
        raise ValueError(f"{context} must be positive")
    return value


def _require_text_tuple(value: object, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    items: list[str] = []
    for index, item in enumerate(value, start=1):
        items.append(_require_text(item, f"{context}[{index}]"))
    return tuple(items)


def _task_layer(value: str) -> TaskLayer:
    allowed: tuple[TaskLayer, ...] = (
        "quality",
        "security",
        "evaluation",
        "observability",
        "portfolio",
        "governance",
    )
    if value not in allowed:
        raise ValueError(f"unknown task layer {value!r}; expected one of {', '.join(allowed)}")
    return cast(TaskLayer, value)


def _task_mode(value: str) -> TaskMode:
    allowed: tuple[TaskMode, ...] = ("automated", "manual")
    if value not in allowed:
        raise ValueError(f"unknown task mode {value!r}; expected one of {', '.join(allowed)}")
    return cast(TaskMode, value)


def _validate_command(command: Sequence[str]) -> tuple[str, ...]:
    if not command:
        raise ValueError("automated tasks require a non-empty command")
    executable = command[0]
    if executable not in ALLOWED_EXECUTABLES:
        raise ValueError(f"command executable {executable!r} is not allowlisted")

    for arg in command:
        if any(token in arg for token in UNSAFE_ARGUMENT_TOKENS):
            raise ValueError(f"unsafe shell token in command argument: {arg!r}")

    if executable == "python":
        if len(command) < 3 or command[1] != "-m" or command[2] not in ALLOWED_PYTHON_MODULES:
            allowed = ", ".join(sorted(ALLOWED_PYTHON_MODULES))
            raise ValueError(f"python automation may only run allowlisted modules: {allowed}")

    return tuple(command)


def task_from_mapping(raw: Mapping[str, object]) -> AutomationTask:
    """Convert a catalog record into a validated automation task."""

    task_id = _require_text(raw.get("id"), "id")
    title = _require_text(raw.get("title"), f"{task_id}.title")
    layer = _task_layer(_require_text(raw.get("layer"), f"{task_id}.layer"))
    mode = _task_mode(_require_text(raw.get("mode"), f"{task_id}.mode"))
    required = _require_bool(raw.get("required"), f"{task_id}.required")
    benefit_score = _require_score(raw.get("benefit_score"), f"{task_id}.benefit_score")
    rationale = _require_text(raw.get("rationale"), f"{task_id}.rationale")
    evidence_paths = _require_text_tuple(raw.get("evidence_paths", []), f"{task_id}.evidence_paths")
    timeout_seconds = _require_positive_int(
        raw.get("timeout_seconds", 180), f"{task_id}.timeout_seconds"
    )
    command = _require_text_tuple(raw.get("command", []), f"{task_id}.command")

    if mode == "manual" and command:
        raise ValueError(f"{task_id}: manual tasks must not declare commands")
    if mode == "automated":
        command = _validate_command(command)

    return AutomationTask(
        id=task_id,
        title=title,
        layer=layer,
        mode=mode,
        required=required,
        benefit_score=benefit_score,
        command=command,
        rationale=rationale,
        evidence_paths=evidence_paths,
        timeout_seconds=timeout_seconds,
    )


def load_catalog(path: Path) -> list[AutomationTask]:
    """Load a JSON automation task catalog."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("automation catalog must be a JSON array")
    tasks = [
        task_from_mapping(_require_mapping(item, f"task {index}"))
        for index, item in enumerate(data, 1)
    ]
    ids = [task.id for task in tasks]
    duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate task ids: {', '.join(duplicates)}")
    return tasks


def run_task(
    task: AutomationTask,
    *,
    cwd: Path,
    execute: bool,
    min_benefit_score: float,
) -> TaskResult:
    """Plan or execute one task under benefit and command guardrails."""

    if task.benefit_score < min_benefit_score:
        return TaskResult(
            task=task,
            status="skipped",
            returncode=None,
            stdout="",
            stderr="",
            reason=f"benefit score {task.benefit_score:.2f} below required {min_benefit_score:.2f}",
        )
    if task.mode == "manual":
        return TaskResult(
            task=task,
            status="skipped",
            returncode=None,
            stdout="",
            stderr="",
            reason="manual task is tracked but not executed by automation",
        )
    if not execute:
        return TaskResult(
            task=task,
            status="planned",
            returncode=None,
            stdout="",
            stderr="",
            reason="execution disabled; task is eligible for automation",
        )

    try:
        completed = subprocess.run(
            list(task.command),
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=task.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return TaskResult(
            task=task,
            status="failed",
            returncode=None,
            stdout=stdout[-2000:],
            stderr=stderr[-2000:],
            reason=f"task exceeded timeout of {task.timeout_seconds} seconds",
        )

    status: TaskStatus = "passed" if completed.returncode == 0 else "failed"
    return TaskResult(
        task=task,
        status=status,
        returncode=completed.returncode,
        stdout=completed.stdout[-2000:],
        stderr=completed.stderr[-2000:],
        reason="command completed" if status == "passed" else "command failed",
    )


def run_catalog(
    tasks: Sequence[AutomationTask],
    *,
    cwd: Path,
    execute: bool,
    min_benefit_score: float,
) -> list[TaskResult]:
    """Run a sequence of tasks in catalog order."""

    if min_benefit_score < 0.0 or min_benefit_score > 1.0:
        raise ValueError("min_benefit_score must be in [0.0, 1.0]")
    return [
        run_task(task, cwd=cwd, execute=execute, min_benefit_score=min_benefit_score)
        for task in tasks
    ]


def required_failures(results: Sequence[TaskResult]) -> list[TaskResult]:
    """Return required tasks that did not pass."""

    return [result for result in results if result.task.required and result.status != "passed"]


def result_payload(results: Sequence[TaskResult], *, min_benefit_score: float) -> dict[str, object]:
    """Build a deterministic JSON-serializable report payload."""

    return {
        "schema_version": "sentinel.automation.v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "min_benefit_score": min_benefit_score,
        "required_passed": not required_failures(results),
        "tasks": [
            {
                "id": result.task.id,
                "title": result.task.title,
                "layer": result.task.layer,
                "mode": result.task.mode,
                "required": result.task.required,
                "benefit_score": result.task.benefit_score,
                "status": result.status,
                "returncode": result.returncode,
                "reason": result.reason,
                "evidence_paths": list(result.task.evidence_paths),
                "command": list(result.task.command),
            }
            for result in results
        ],
    }


def markdown_report(results: Sequence[TaskResult], *, min_benefit_score: float) -> str:
    """Render a compact Markdown automation report."""

    lines = [
        "# Sentinel Stability Automation Report",
        "",
        f"Minimum benefit score: `{min_benefit_score:.2f}`",
        "",
        "| Task | Layer | Required | Benefit | Status | Reason |",
        "|---|---|---:|---:|---|---|",
    ]
    for result in results:
        lines.append(
            "| {title} | {layer} | {required} | {benefit:.2f} | {status} | {reason} |".format(
                title=result.task.title,
                layer=result.task.layer,
                required="yes" if result.task.required else "no",
                benefit=result.task.benefit_score,
                status=result.status,
                reason=result.reason.replace("|", "/"),
            )
        )
    lines.append("")
    failures = required_failures(results)
    if failures:
        lines.append("## Required failures")
        lines.append("")
        for failure in failures:
            lines.append(f"- `{failure.task.id}`: {failure.reason}")
        lines.append("")
    else:
        lines.append("All required automation tasks passed.")
        lines.append("")
    return "\n".join(lines)
