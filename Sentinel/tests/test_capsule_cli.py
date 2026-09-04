import json
from pathlib import Path

from sentinel.capsule_cli import main


def test_capsule_cli_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Capsule proof\n", encoding="utf-8")
    input_path = tmp_path / "capsules.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "id": "capsule-proof",
                    "title": "Capsule proof",
                    "owner": "Shawdai Marie",
                    "visibility": "public_proof",
                    "license_expression": "Apache-2.0 for repository code",
                    "summary": "A capsule built for public proof.",
                    "assets": [
                        {
                            "path": "README.md",
                            "asset_type": "documentation",
                            "required": True,
                        }
                    ],
                    "value_score": 0.92,
                    "evidence_score": 0.91,
                    "security_score": 0.93,
                    "deployability_score": 0.88,
                    "rights_score": 0.86,
                    "public_distribution": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    json_out = tmp_path / "reports" / "capsules.json"
    markdown_out = tmp_path / "reports" / "capsules.md"

    code = main(
        [
            "--capsules",
            str(input_path),
            "--root",
            str(tmp_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
            "--min-score",
            "0.70",
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["passed"] is True
    assert payload["manifests"][0]["status"] == "ready"
    assert "Deployment Capsule Report" in markdown_out.read_text(encoding="utf-8")


def test_capsule_cli_fails_when_capsule_is_blocked(tmp_path: Path) -> None:
    input_path = tmp_path / "capsules.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "id": "missing",
                    "title": "Missing required asset",
                    "owner": "Shawdai Marie",
                    "visibility": "public_proof",
                    "license_expression": "Apache-2.0",
                    "summary": "A blocked capsule.",
                    "assets": [
                        {
                            "path": "missing.md",
                            "asset_type": "documentation",
                            "required": True,
                        }
                    ],
                    "value_score": 0.91,
                    "evidence_score": 0.90,
                    "security_score": 0.91,
                    "deployability_score": 0.90,
                    "rights_score": 0.88,
                    "public_distribution": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    code = main(["--capsules", str(input_path), "--root", str(tmp_path), "--min-score", "0.70"])

    assert code == 1
