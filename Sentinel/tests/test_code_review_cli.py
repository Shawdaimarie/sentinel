import json
from pathlib import Path

from sentinel.code_review_cli import main


def case_payload() -> list[dict[str, object]]:
    return [
        {
            "id": "safe-cache-fix",
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
            "expected_decision": "reject",
            "scores": {
                "requirement_fit": 0.80,
                "correctness": 0.76,
                "security": 0.18,
                "maintainability": 0.70,
                "verification": 0.64,
                "communication": 0.66,
            },
        },
    ]


def test_cli_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    json_out = tmp_path / "report.json"
    markdown_out = tmp_path / "report.md"
    cases.write_text(json.dumps(case_payload()), encoding="utf-8")

    exit_code = main(
        [
            "--cases",
            str(cases),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
            "--min-score",
            "0.10",
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "sentinel.code_review.v1"
    assert payload["results"][0]["decision"] == "accept"
    assert payload["results"][1]["decision"] == "reject"
    assert "unsafe-shell-secret" in markdown_out.read_text(encoding="utf-8")


def test_cli_fails_when_expected_decision_does_not_match(tmp_path: Path) -> None:
    payload = case_payload()
    payload[0]["expected_decision"] = "reject"
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["--cases", str(cases)]) == 1
