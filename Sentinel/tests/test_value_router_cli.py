import json

import pytest

from sentinel.value_router_cli import main


def route_items() -> list[dict[str, object]]:
    return [
        {
            "id": "sentinel.public-proof",
            "title": "Sentinel public proof layer",
            "domain": "engineering",
            "asset_type": "source_code",
            "owner": "Shawdai Marie",
            "value_score": 0.95,
            "evidence_score": 0.94,
            "security_score": 0.96,
            "deployment_score": 0.90,
            "rights_score": 0.92,
            "external_distribution": True,
        },
        {
            "id": "client.routing-template",
            "title": "Private client routing template",
            "domain": "client_delivery",
            "asset_type": "client_workflow",
            "owner": "Shawdai Marie",
            "value_score": 0.90,
            "evidence_score": 0.82,
            "security_score": 0.86,
            "deployment_score": 0.78,
            "rights_score": 0.88,
            "requires_human_approval": True,
            "external_distribution": False,
        },
    ]


def test_cli_writes_value_route_reports(tmp_path) -> None:
    items_path = tmp_path / "items.json"
    json_out = tmp_path / "value_routes.json"
    markdown_out = tmp_path / "value_routes.md"
    items_path.write_text(json.dumps(route_items()), encoding="utf-8")

    result = main(
        [
            "--items",
            str(items_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
            "--min-score",
            "0.70",
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    report = markdown_out.read_text(encoding="utf-8")

    assert result == 0
    assert payload["schema_version"] == "sentinel.value_route.v1"
    assert payload["passed"] is True
    assert payload["results"][0]["lane"] == "deployable"
    assert payload["results"][1]["lane"] == "human_review"
    assert "Sentinel Value Route Gateway Report" in report


def test_cli_returns_failure_for_rejected_item(tmp_path) -> None:
    items = route_items()
    items[0]["security_score"] = 0.20
    items_path = tmp_path / "items.json"
    items_path.write_text(json.dumps(items), encoding="utf-8")

    result = main(["--items", str(items_path), "--min-score", "0.70"])

    assert result == 1


def test_cli_rejects_unknown_domain(tmp_path) -> None:
    items = route_items()
    items[0]["domain"] = "unknown"
    items_path = tmp_path / "items.json"
    items_path.write_text(json.dumps(items), encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["--items", str(items_path)])
