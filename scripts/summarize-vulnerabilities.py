"""Expose actionable Grype findings without changing the scanner's decision."""

import html
import json
import sys
from pathlib import Path


def cell(value: object) -> str:
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")


def summarize(report_path: Path) -> str:
    title = f"### Vulnerability scan: {cell(report_path.stem)}\n\n"
    if not report_path.is_file():
        return (
            title
            + "Report unavailable. Inspect the build and scanner logs; no clean result is established.\n"
        )
    report = json.loads(report_path.read_text())
    # Only active matches count here. Grype records configured exceptions in
    # ignoredMatches; the scanner, not this display helper, enforces the gate.
    findings = set()
    for match in report["matches"]:
        vulnerability = match["vulnerability"]
        if vulnerability["severity"].lower() not in {"high", "critical"}:
            continue
        fix = vulnerability.get("fix", {})
        if fix.get("state") != "fixed":
            continue
        package = match["artifact"]
        findings.add(
            (
                vulnerability["severity"],
                vulnerability["id"],
                package["name"],
                package["version"],
                ", ".join(fix.get("versions", [])) or "See full report",
            )
        )
    lines = [title, f"Fixable High/Critical package findings: **{len(findings)}**.\n"]
    if findings:
        lines += [
            "| Severity | Finding | Package | Installed | Fixed in |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines += [
            "| " + " | ".join(cell(v) for v in row) + " |" for row in sorted(findings)
        ]
    lines += [
        "",
        "The scanner step determines pass/fail. The uploaded report and SBOM contain the full evidence.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(summarize(Path(sys.argv[1])), end="")
