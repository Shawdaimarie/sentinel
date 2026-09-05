import json
from pathlib import Path

import pytest

from sentinel.code_review import DimensionScore, score_code_review
from sentinel.code_review_cli import DECISIONS, evaluate_cases

ROOT = Path(__file__).resolve().parents[1]


def complete_scores(**overrides: float) -> list[DimensionScore]:
    values = {
        "requirement_fit": 0.90,
        "correctness": 0.90,
        "security": 0.90,
        "maintainability": 0.88,
        "verification": 0.86,
        "communication": 0.86,
    }
    values.update(overrides)
    return [DimensionScore(dimension=key, score=value) for key, value in values.items()]


def test_accept_with_edits_has_explicit_reverification_action() -> None:
    result = score_code_review(complete_scores(verification=0.48))

    assert result.decision == "accept_with_edits"
    assert result.reviewer_action == "edit_and_reverify"
    assert result.decisive_failure_modes == ("dimension:verification",)


def test_explicit_critical_finding_rejects_polished_answer() -> None:
    result = score_code_review(
        complete_scores(),
        critical_findings=["fabricated_evidence"],
    )

    assert result.score >= 0.85
    assert result.decision == "reject"
    assert result.critical_findings == ("fabricated_evidence",)
    assert result.decisive_failure_modes == ("critical:fabricated_evidence",)
    assert result.reviewer_action == "do_not_use"


def test_critical_finding_vocabulary_is_strict_and_unique() -> None:
    with pytest.raises(ValueError, match="unknown critical finding"):
        score_code_review(complete_scores(), critical_findings=["imaginary_failure"])

    with pytest.raises(ValueError, match="duplicate critical finding"):
        score_code_review(
            complete_scores(),
            critical_findings=["secret_exposure", "secret_exposure"],
        )


def test_public_fixture_covers_required_classes_and_decisions() -> None:
    cases = json.loads(
        (ROOT / "examples" / "code_review_scorecard_cases.json").read_text(encoding="utf-8")
    )
    results = evaluate_cases(cases)

    assert {case["case_class"] for case in cases} >= {
        "safe",
        "unsafe",
        "incomplete",
        "over_engineered",
        "unverifiable",
    }
    assert {result["decision"] for result in results} == set(DECISIONS)
    assert all(result.get("expected_matched") is True for result in results)


def test_public_schemas_are_parseable_and_versioned() -> None:
    case_schema = json.loads(
        (ROOT / "schemas" / "code_review_cases.schema.json").read_text(encoding="utf-8")
    )
    report_schema = json.loads(
        (ROOT / "schemas" / "code_review_report.schema.json").read_text(encoding="utf-8")
    )

    assert case_schema["$id"].endswith("code_review_cases.schema.json")
    assert report_schema["properties"]["schema_version"]["const"] == (
        "sentinel.code_review_report.v2"
    )
