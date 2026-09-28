import json
from pathlib import Path

import pytest

from sentinel.financial_gate_cli import main


def case_payload() -> list[dict[str, object]]:
    return [
        {
            "id": "grounded-market-recap",
            "case_class": "grounded",
            "summary": "A weekly market recap sourced and disclosed throughout.",
            "expected_decision": "ready_for_human_release",
            "scores": {
                "grounding": 0.92,
                "advice_boundary": 0.90,
                "disclosure": 0.90,
                "data_sensitivity": 0.95,
                "recency": 0.88,
                "clarity": 0.85,
            },
        },
        {
            "id": "buy-now-directive",
            "case_class": "personalized_advice",
            "summary": "A response that tells the reader to buy a specific ticker now.",
            "expected_decision": "reject",
            "critical_findings": ["personalized_trade_directive"],
            "scores": {
                "grounding": 0.75,
                "advice_boundary": 0.15,
                "disclosure": 0.70,
                "data_sensitivity": 0.90,
                "recency": 0.80,
                "clarity": 0.70,
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
    assert payload["schema_version"] == "sentinel.financial_content_report.v1"
    assert payload["case_count"] == 2
    assert len(payload["source_sha256"]) == 64
    assert payload["all_expected_matched"] is True
    assert payload["decision_counts"]["ready_for_human_release"] == 1
    assert payload["decision_counts"]["reject"] == 1
    assert payload["critical_finding_counts"]["personalized_trade_directive"] == 1
    assert payload["results"][1]["reviewer_action"] == "do_not_publish"
    assert payload["results"][1]["decisive_failure_modes"] == [
        "critical:personalized_trade_directive",
        "dimension:advice_boundary",
    ]

    report = markdown_out.read_text(encoding="utf-8")
    assert "Reviewer action" in report
    assert "Do not publish the content" in report
    assert "critical:personalized_trade_directive" in report
    assert "| data_sensitivity | 0.9500 | pass |" in report


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


def test_cli_enforces_min_score_threshold(tmp_path: Path) -> None:
    payload = [case_payload()[0]]
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["--cases", str(cases), "--min-score", "0.5"]) == 0
    assert main(["--cases", str(cases), "--min-score", "0.99"]) == 1
