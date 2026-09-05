"""Training-data quality gates for AI evaluation and post-training."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DatasetSplit: TypeAlias = Literal["train", "validation", "test"]
TrainingLabel: TypeAlias = Literal[
    "allow",
    "deny",
    "refuse",
    "request_approval",
    "cite_evidence",
    "complete",
    "human_review",
]
TaskType: TypeAlias = Literal[
    "tool_use_safety",
    "grounding",
    "privacy",
    "human_approval",
    "cost_control",
    "regulated_workflow",
    "safe_completion",
    "coding_agent_review",
]
SourceType: TypeAlias = Literal["synthetic", "public", "benchmark", "internal"]
IssueSeverity: TypeAlias = Literal["hard_failure", "warning"]

LABELS: tuple[TrainingLabel, ...] = (
    "allow",
    "deny",
    "refuse",
    "request_approval",
    "cite_evidence",
    "complete",
    "human_review",
)
SPLITS: tuple[DatasetSplit, ...] = ("train", "validation", "test")
RISK_TAGS: frozenset[str] = frozenset(
    {
        "cost_runaway",
        "fabricated_evidence",
        "grounding",
        "human_approval",
        "missing_citation",
        "privacy",
        "prompt_injection",
        "regulated_decision",
        "retry_loop",
        "safe_completion",
        "secret_exposure",
        "unsafe_file_write",
        "unsafe_shell",
        "unauthorized_tool_use",
    }
)
NEGATIVE_LABELS = frozenset({"deny", "refuse", "request_approval", "human_review"})
HUMAN_APPROVAL_LABELS = frozenset({"request_approval", "human_review"})
PRIVACY_TAGS = frozenset({"privacy", "secret_exposure"})
TOOL_USE_TAGS = frozenset(
    {"unauthorized_tool_use", "unsafe_shell", "unsafe_file_write", "cost_runaway"}
)
MAX_PROMPT_WARNING_CHARS = 4_000

CREDENTIAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "named_secret",
        re.compile(
            r"(?i)\b(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?"
            r"[A-Za-z0-9_./+=-]{8,}"
        ),
    ),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)
PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("us_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
)


class DataGateInputError(ValueError):
    """Raised when a dataset cannot be read as JSONL."""


class ExampleSource(BaseModel):
    """Source metadata for one training or evaluation example."""

    model_config = ConfigDict(extra="forbid")

    type: SourceType
    note: str = Field(min_length=1)
    url: str | None = None

    @field_validator("note")
    @classmethod
    def _strip_note(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("source note must not be blank")
        return stripped

    @field_validator("url")
    @classmethod
    def _strip_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class PrivacyMetadata(BaseModel):
    """Privacy and public-release status for one example."""

    model_config = ConfigDict(extra="forbid")

    contains_personal_data: bool = False
    contains_credentials: bool = False
    public_release_ok: bool = True


class TrainingExample(BaseModel):
    """One structured example used for evaluation or post-training."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    task_type: TaskType
    prompt: str = Field(min_length=1)
    expected_behavior: str = Field(min_length=1)
    label: TrainingLabel
    risk_tags: list[str] = Field(min_length=1)
    source: ExampleSource
    privacy: PrivacyMetadata
    split: DatasetSplit
    created_at: date
    limitations: str = ""

    @field_validator("prompt", "expected_behavior", "limitations")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("risk_tags")
    @classmethod
    def _normalize_tags(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in values:
            tag = raw.strip().lower().replace("-", "_")
            if tag and tag not in normalized:
                normalized.append(tag)
        if not normalized:
            raise ValueError("at least one risk tag is required")
        return normalized


@dataclass(frozen=True)
class LoadedExample:
    line: int
    example: TrainingExample


@dataclass(frozen=True)
class DataIssue:
    severity: IssueSeverity
    code: str
    message: str
    line: int | None = None
    row_id: str | None = None


@dataclass(frozen=True)
class LoadedDataset:
    source_path: Path
    row_count: int
    examples: tuple[LoadedExample, ...]
    issues: tuple[DataIssue, ...]


@dataclass(frozen=True)
class DatasetGateConfig:
    public_release_required: bool = True
    min_examples: int = 1
    fail_on_warnings: bool = False


@dataclass(frozen=True)
class DatasetGateReport:
    source_path: Path
    source_sha256: str
    generated_at: str
    row_count: int
    valid_row_count: int
    passed: bool
    split_counts: dict[str, int]
    label_counts: dict[str, int]
    risk_tag_counts: dict[str, int]
    task_type_counts: dict[str, int]
    duplicate_ids: tuple[str, ...]
    hard_failures: tuple[DataIssue, ...]
    warnings: tuple[DataIssue, ...]


def sha256_file(path: Path) -> str:
    """Return a SHA-256 digest for the exact dataset bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validation_message(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)


def _row_id(raw: object) -> str | None:
    if isinstance(raw, dict) and isinstance(raw.get("id"), str):
        return raw["id"].strip() or None
    return None


def load_jsonl(path: Path) -> LoadedDataset:
    """Load a JSONL dataset while preserving row-level parse failures."""

    examples: list[LoadedExample] = []
    issues: list[DataIssue] = []
    row_count = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DataGateInputError(str(exc)) from exc

    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            issues.append(
                DataIssue("warning", "blank_line", "blank JSONL line ignored", line_number)
            )
            continue
        row_count += 1
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(
                DataIssue("hard_failure", "invalid_json", f"invalid JSON: {exc.msg}", line_number)
            )
            continue
        if not isinstance(raw, dict):
            issues.append(
                DataIssue("hard_failure", "schema", "row must be a JSON object", line_number)
            )
            continue
        try:
            examples.append(LoadedExample(line_number, TrainingExample.model_validate(raw)))
        except ValidationError as exc:
            issues.append(
                DataIssue(
                    "hard_failure",
                    "schema",
                    _validation_message(exc),
                    line_number,
                    _row_id(raw),
                )
            )
    return LoadedDataset(path, row_count, tuple(examples), tuple(issues))


def _all_text(example: TrainingExample) -> str:
    return "\n".join(
        [
            example.prompt,
            example.expected_behavior,
            example.source.note,
            example.source.url or "",
            example.limitations,
        ]
    )


def _pattern_hits(patterns: tuple[tuple[str, re.Pattern[str]], ...], text: str) -> list[str]:
    return [name for name, pattern in patterns if pattern.search(text)]


def _normalized_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", prompt.lower())).strip()


def _counter_payload(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _counts(
    examples: tuple[LoadedExample, ...],
) -> tuple[dict[str, int], dict[str, int], dict[str, int], dict[str, int]]:
    split_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    risk_tag_counts: Counter[str] = Counter()
    task_type_counts: Counter[str] = Counter()
    for loaded in examples:
        example = loaded.example
        split_counts[example.split] += 1
        label_counts[example.label] += 1
        risk_tag_counts.update(example.risk_tags)
        task_type_counts[example.task_type] += 1
    return (
        _counter_payload(split_counts),
        _counter_payload(label_counts),
        _counter_payload(risk_tag_counts),
        _counter_payload(task_type_counts),
    )


def _dataset_warnings(
    examples: tuple[LoadedExample, ...],
    label_counts: dict[str, int],
    risk_tag_counts: dict[str, int],
    task_type_counts: dict[str, int],
) -> list[DataIssue]:
    valid_count = len(examples)
    if valid_count == 0:
        return []
    warnings: list[DataIssue] = []
    if valid_count >= 5 and max(label_counts.values(), default=0) / valid_count > 0.60:
        warnings.append(DataIssue("warning", "class_imbalance", "one label exceeds 60 percent"))
    if len(task_type_counts) < min(3, valid_count):
        warnings.append(DataIssue("warning", "low_scenario_diversity", "too few task types"))
    if not any(item.example.label in NEGATIVE_LABELS for item in examples):
        warnings.append(DataIssue("warning", "missing_negative_examples", "no negative examples"))
    if "prompt_injection" not in risk_tag_counts:
        warnings.append(
            DataIssue("warning", "missing_prompt_injection_cases", "no prompt-injection cases")
        )
    if not PRIVACY_TAGS.intersection(risk_tag_counts):
        warnings.append(DataIssue("warning", "missing_privacy_cases", "no privacy or secret cases"))
    if "human_approval" not in risk_tag_counts and not any(
        item.example.label in HUMAN_APPROVAL_LABELS for item in examples
    ):
        warnings.append(DataIssue("warning", "missing_human_approval_cases", "no approval cases"))
    if not TOOL_USE_TAGS.intersection(risk_tag_counts):
        warnings.append(DataIssue("warning", "missing_tool_use_cases", "no tool-use cases"))
    return warnings


def validate_dataset(
    loaded: LoadedDataset,
    config: DatasetGateConfig | None = None,
) -> DatasetGateReport:
    """Validate a parsed dataset and return a complete gate report."""

    active_config = config or DatasetGateConfig()
    if active_config.min_examples < 1:
        raise ValueError("min_examples must be at least 1")

    issues = list(loaded.issues)
    examples = loaded.examples
    if len(examples) < active_config.min_examples:
        issues.append(
            DataIssue(
                "hard_failure",
                "too_few_examples",
                (
                    f"dataset has {len(examples)} valid examples; "
                    f"requires {active_config.min_examples}"
                ),
            )
        )

    duplicate_ids = tuple(
        sorted(
            item_id
            for item_id, count in Counter(item.example.id for item in examples).items()
            if count > 1
        )
    )
    for item_id in duplicate_ids:
        lines = [str(item.line) for item in examples if item.example.id == item_id]
        issues.append(
            DataIssue(
                "hard_failure",
                "duplicate_id",
                f"duplicate example id appears on lines {', '.join(lines)}",
                row_id=item_id,
            )
        )

    prompts: dict[str, list[LoadedExample]] = defaultdict(list)
    for item in examples:
        example = item.example
        prompts[_normalized_prompt(example.prompt)].append(item)
        issues.extend(_row_issues(item, active_config))

    for prompt_group in prompts.values():
        splits = sorted({item.example.split for item in prompt_group})
        if len(splits) > 1:
            row_ids = ", ".join(item.example.id for item in prompt_group)
            issues.append(
                DataIssue(
                    "hard_failure",
                    "split_leakage",
                    f"near-identical prompt appears across splits {', '.join(splits)}: {row_ids}",
                )
            )

    split_counts, label_counts, risk_tag_counts, task_type_counts = _counts(examples)
    issues.extend(_dataset_warnings(examples, label_counts, risk_tag_counts, task_type_counts))
    hard_failures = tuple(issue for issue in issues if issue.severity == "hard_failure")
    warnings = tuple(issue for issue in issues if issue.severity == "warning")

    return DatasetGateReport(
        source_path=loaded.source_path,
        source_sha256=sha256_file(loaded.source_path),
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        row_count=loaded.row_count,
        valid_row_count=len(examples),
        passed=not hard_failures and (not warnings or not active_config.fail_on_warnings),
        split_counts=split_counts,
        label_counts=label_counts,
        risk_tag_counts=risk_tag_counts,
        task_type_counts=task_type_counts,
        duplicate_ids=duplicate_ids,
        hard_failures=hard_failures,
        warnings=warnings,
    )


def _row_issues(item: LoadedExample, config: DatasetGateConfig) -> list[DataIssue]:
    example = item.example
    issues: list[DataIssue] = []
    unknown_tags = sorted(tag for tag in example.risk_tags if tag not in RISK_TAGS)
    if unknown_tags:
        issues.append(
            DataIssue(
                "hard_failure",
                "unknown_risk_tag",
                "unknown risk tags: " + ", ".join(unknown_tags),
                item.line,
                example.id,
            )
        )

    credential_hits = _pattern_hits(CREDENTIAL_PATTERNS, _all_text(example))
    if credential_hits or example.privacy.contains_credentials:
        detail = ", ".join(credential_hits) if credential_hits else "metadata flag"
        issues.append(
            DataIssue(
                "hard_failure",
                "credential_exposure",
                f"credential-like content is not allowed in training proof: {detail}",
                item.line,
                example.id,
            )
        )

    pii_hits = _pattern_hits(PII_PATTERNS, _all_text(example))
    if pii_hits and not example.privacy.contains_personal_data:
        issues.append(
            DataIssue(
                "hard_failure",
                "privacy_metadata_mismatch",
                "direct personal data detected but privacy metadata says false",
                item.line,
                example.id,
            )
        )
    if config.public_release_required and example.privacy.contains_personal_data:
        issues.append(
            DataIssue(
                "hard_failure",
                "personal_data_public_proof",
                "personal data cannot be included in public training proof",
                item.line,
                example.id,
            )
        )
    if config.public_release_required and not example.privacy.public_release_ok:
        issues.append(
            DataIssue(
                "hard_failure",
                "not_public_release_ready",
                "example is not marked safe for public release",
                item.line,
                example.id,
            )
        )
    if len(example.prompt) > MAX_PROMPT_WARNING_CHARS:
        issues.append(
            DataIssue(
                "warning",
                "long_prompt",
                f"prompt exceeds {MAX_PROMPT_WARNING_CHARS} characters",
                item.line,
                example.id,
            )
        )
    if not example.limitations:
        issues.append(
            DataIssue(
                "warning",
                "missing_limitation",
                "example should state a limitation",
                item.line,
                example.id,
            )
        )
    return issues


def evaluate_file(path: Path, config: DatasetGateConfig | None = None) -> DatasetGateReport:
    """Load and validate one JSONL dataset."""

    return validate_dataset(load_jsonl(path), config)


def _issue_payload(issue: DataIssue) -> dict[str, object]:
    return {
        "severity": issue.severity,
        "code": issue.code,
        "message": issue.message,
        "line": issue.line,
        "row_id": issue.row_id,
    }


def report_payload(report: DatasetGateReport) -> dict[str, object]:
    """Return a JSON-serializable report payload."""

    return {
        "schema_version": "sentinel.training_data_gate.v1",
        "generated_at": report.generated_at,
        "source_path": str(report.source_path),
        "source_sha256": report.source_sha256,
        "row_count": report.row_count,
        "valid_row_count": report.valid_row_count,
        "passed": report.passed,
        "split_counts": report.split_counts,
        "label_counts": report.label_counts,
        "risk_tag_counts": report.risk_tag_counts,
        "task_type_counts": report.task_type_counts,
        "duplicate_ids": list(report.duplicate_ids),
        "hard_failures": [_issue_payload(issue) for issue in report.hard_failures],
        "warnings": [_issue_payload(issue) for issue in report.warnings],
    }


def _issue_location(issue: DataIssue) -> str:
    parts: list[str] = []
    if issue.row_id:
        parts.append(f"id={issue.row_id}")
    if issue.line is not None:
        parts.append(f"line={issue.line}")
    return "" if not parts else f" ({', '.join(parts)})"


def render_markdown(report: DatasetGateReport) -> str:
    """Render a training-data quality report as Markdown."""

    lines = [
        "# Sentinel Training Data Quality Gate Report",
        "",
        f"**Source:** `{report.source_path}`  ",
        f"**Generated:** `{report.generated_at}`  ",
        f"**Gate:** **{'PASS' if report.passed else 'FAIL'}**",
        "",
        "## Dataset summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | {report.row_count} |",
        f"| Valid rows | {report.valid_row_count} |",
        f"| Hard failures | {len(report.hard_failures)} |",
        f"| Warnings | {len(report.warnings)} |",
        "",
        "## Split counts",
        "",
        "| Split | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| `{split}` | {report.split_counts.get(split, 0)} |" for split in SPLITS)
    lines.extend(["", "## Label counts", "", "| Label | Count |", "|---|---:|"])
    lines.extend(f"| `{label}` | {report.label_counts.get(label, 0)} |" for label in LABELS)
    lines.extend(["", "## Risk-tag coverage", "", "| Risk tag | Count |", "|---|---:|"])
    lines.extend(f"| `{tag}` | {count} |" for tag, count in report.risk_tag_counts.items())
    lines.extend(_issue_section("Hard failures", report.hard_failures))
    lines.extend(_issue_section("Warnings", report.warnings))
    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            f"- `source_sha256`: `{report.source_sha256}`",
            "",
            "## Interpretation boundary",
            "",
            (
                "This report validates dataset structure, declared source notes, "
                "privacy posture, split hygiene, and risk coverage. It does not "
                "prove that a trained model is safe, unbiased, compliant, or "
                "production-ready. Model behavior still requires separate "
                "evaluation, red-team testing, human review, and monitoring."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _issue_section(title: str, issues: tuple[DataIssue, ...]) -> list[str]:
    if not issues:
        return []
    lines = ["", f"## {title}", ""]
    lines.extend(f"- `{issue.code}`{_issue_location(issue)}: {issue.message}" for issue in issues)
    return lines


def write_json(path: Path, report: DatasetGateReport) -> None:
    """Write a JSON report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_payload(report), indent=2, sort_keys=True) + "\n", "utf-8")


def write_markdown(path: Path, report: DatasetGateReport) -> None:
    """Write a Markdown report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), "utf-8")
