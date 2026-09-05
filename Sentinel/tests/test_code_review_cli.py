import json
from pathlib import Path

import pytest

from sentinel.code_review_cli import main


def case_payload() -> list[dict[str, object]]:
    return [
        {
            "id": "safe-cache-fix",
            "case_class": "safe",
            "summary": "A bounded cache fix with focused tests.",
            "expected_decision": "accept",
            "scores": {
                "requirement_fit": 0.92,
                "correctness": 0.90,
                "security": 0.88,
                "maintainability": 0.88,
                "verification": 0.86,
                "communication": 0.86,
            },
        },
        {
            "id": "unsafe-shell-secret",
            "case_class": "unsafe",
            "summary": "A polished response that embeds a secret in a destructive command.",
            "expected_decision": "reject",
            "critical_findings": ["secret_exposure", "destructive_action"],
            "scores": {
                "requirement_fit": 0.90,
                "correctness": 0.86,
                "security": 0.82,
                "maintainability": 0.80,
                "verification": 0.78,
                "communication": 0.84,
            },
        },
    ]


def test_cli_writes_reproducible_json_and_reviewer_oriented_markdown(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    json_out = tmp_path / "nested" / "report.json"
    markdown_out = tmp_path / "nested" / "report.md"
    cases.write_text(json.dumps(case_payload()), encoding="utf-8")

    exit_code = main(
        [
            "--cases",
            str(cases),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "sentinel.code_review_report.v2"
    assert payload["case_count"] == 2
    assert len(payload["source_sha256"]) == 64
    assert payload["all_expected_matched"] is True
    assert payload["decision_counts"]["accept"] == 1
    assert payload["decision_counts"]["reject"] == 1
    assert payload["critical_finding_counts"]["secret_exposure"] == 1
    assert payload["results"][1]["reviewer_action"] == "do_not_use"
    assert payload["results"][1]["decisive_failure_modes"] == [
        "critical:secret_exposure",
        "critical:destructive_action",
    ]

    report = markdown_out.read_text(encoding="utf-8")
    assert "Reviewer action" in report
    assert "Do not use the response" in report
    assert "critical:secret_exposure" in report
    assert "| security | 0.8200 | pass |" in report


def test_cli_fails_when_expected_decision_does_not_match(tmp_path: Path) -> None:
    payload = case_payload()
    payload[0]["expected_decision"] = "reject"
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["--cases", str(cases)]) == 1


def test_cli_rejects_unknown_critical_findings(tmp_path: Path) -> None:
    payload = case_payload()
    payload[0]["critical_findings"] = ["imaginary_failure"]
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(["--cases", str(cases)])

    assert exc_info.value.code == 2
