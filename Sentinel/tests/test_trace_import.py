from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sentinel.trace_cli import main
from sentinel.trace_import import (
    TraceImportConfig,
    TraceImportError,
    import_otel_document,
    import_otel_path,
)

TRACE_ID = "0123456789abcdef0123456789abcdef"
ROOT_ID = "0000000000000001"


def attr(key: str, kind: str, value: object) -> dict[str, object]:
    return {"key": key, "value": {kind: value}}


def document() -> dict[str, object]:
    root = {
        "traceId": TRACE_ID,
        "spanId": ROOT_ID,
        "name": "agent.run",
        "startTimeUnixNano": "1000000000",
        "endTimeUnixNano": "1600000000",
        "status": {"code": "STATUS_CODE_OK"},
        "attributes": [
            attr("sentinel.case.id", "stringValue", "grounded-answer"),
            attr("sentinel.run.id", "stringValue", "otel-trial-1"),
            attr("sentinel.output", "stringValue", "Supported by NIST evidence."),
            attr("gen_ai.usage.cost", "doubleValue", 0.004),
            attr(
                "sentinel.evidence.urls",
                "arrayValue",
                {"values": [{"stringValue": "https://nist.gov/ai?token=secret"}]},
            ),
            attr("api_key", "stringValue", "do-not-retain"),
            attr("deployment.environment", "stringValue", "test"),
        ],
    }
    tool_1 = {
        "traceId": TRACE_ID,
        "spanId": "0000000000000002",
        "parentSpanId": ROOT_ID,
        "name": "tool.http.get",
        "startTimeUnixNano": "1100000000",
        "endTimeUnixNano": "1200000000",
        "status": {"code": "STATUS_CODE_ERROR"},
        "attributes": [
            attr("gen_ai.operation.name", "stringValue", "execute_tool"),
            attr("gen_ai.tool.name", "stringValue", "http.get"),
            attr("url.full", "stringValue", "https://nist.gov/ai?api_key=secret"),
            attr("sentinel.action.status", "stringValue", "failed"),
            attr("sentinel.retry.attempt", "intValue", "1"),
        ],
    }
    tool_2 = {
        "traceId": TRACE_ID,
        "spanId": "0000000000000003",
        "parentSpanId": ROOT_ID,
        "name": "tool.http.get",
        "startTimeUnixNano": "1210000000",
        "endTimeUnixNano": "1310000000",
        "status": {"code": "STATUS_CODE_OK"},
        "attributes": [
            attr("gen_ai.operation.name", "stringValue", "execute_tool"),
            attr("gen_ai.tool.name", "stringValue", "http.get"),
            attr("url.full", "stringValue", "https://nist.gov/ai"),
            attr("sentinel.action.status", "stringValue", "executed"),
            attr("sentinel.retry.attempt", "intValue", "2"),
        ],
        "events": [
            {
                "name": "human.approval",
                "timeUnixNano": "1300000000",
                "attributes": [attr("approval.status", "stringValue", "approved")],
            }
        ],
    }
    approval = {
        "traceId": TRACE_ID,
        "spanId": "0000000000000004",
        "parentSpanId": ROOT_ID,
        "name": "approval.payment",
        "startTimeUnixNano": "1320000000",
        "endTimeUnixNano": "1330000000",
        "status": {"code": "STATUS_CODE_OK"},
        "attributes": [
            attr("sentinel.span.kind", "stringValue", "approval"),
            attr("sentinel.approval.status", "stringValue", "denied"),
        ],
    }
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [attr("service.name", "stringValue", "candidate-v3")]
                },
                "scopeSpans": [{"spans": [root, tool_1, tool_2, approval]}],
            }
        ]
    }


def source_bytes(doc: dict[str, object]) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def test_imports_complete_trace_deterministically() -> None:
    doc = document()
    source = source_bytes(doc)
    result = import_otel_document(doc, source_bytes=source)

    assert len(result.runs) == 1
    run = result.runs[0]
    assert run.case_id == "grounded-answer"
    assert run.run_id == "otel-trial-1"
    assert run.system == "candidate-v3"
    assert run.output == "Supported by NIST evidence."
    assert run.completed is True
    assert run.latency_ms == 600
    assert run.cost_usd == pytest.approx(0.004)

    assert [action.name for action in run.actions] == [
        "http.get",
        "http.get",
        "human.approval",
        "human.approval",
    ]
    assert run.actions[3].status == "denied"

    trace = result.manifest.traces[0]
    assert trace.trace_id == TRACE_ID
    assert trace.root_span_id == ROOT_ID
    assert trace.partial is False
    assert [action.attempt for action in trace.actions[:2]] == [1, 2]
    assert trace.actions[0].span_id == "0000000000000002"
    assert trace.actions[0].parent_span_id == ROOT_ID

    assert result.manifest.trace_count == 1
    assert result.manifest.run_count == 1
    assert result.manifest.partial_runs == 0
    assert result.manifest.source_sha256 == hashlib.sha256(source).hexdigest()
    assert len(result.manifest.config_sha256) == 64


def test_redacts_sensitive_attributes_and_url_secrets() -> None:
    doc = document()
    result = import_otel_document(doc, source_bytes=source_bytes(doc))
    run = result.runs[0]
    trace = result.manifest.traces[0]

    assert trace.metadata["api_key"] == "[REDACTED]"
    assert "secret" not in run.evidence_urls[0]
    assert "%5BREDACTED%5D" in run.actions[0].target
    assert result.manifest.redacted_attribute_count >= 3


def test_unknown_metadata_is_bounded_and_configurable() -> None:
    doc = document()
    root = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]  # type: ignore[index]
    root["attributes"].extend(  # type: ignore[union-attr]
        [attr(f"vendor.field.{index}", "stringValue", "x" * 100) for index in range(10)]
    )
    config = TraceImportConfig(max_metadata_entries=3, max_metadata_value_length=16)
    result = import_otel_document(doc, source_bytes=source_bytes(doc), config=config)

    # Three bounded unknown values plus importer-owned provenance entries.
    vendor_values = {
        key: value
        for key, value in result.manifest.traces[0].metadata.items()
        if key.startswith("vendor.field")
    }
    assert len(vendor_values) <= 3
    assert all(
        isinstance(value, str) and len(value) <= 16
        for value in vendor_values.values()
    )


def test_missing_output_marks_trace_partial_and_incomplete() -> None:
    doc = document()
    root = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]  # type: ignore[index]
    root["attributes"] = [  # type: ignore[index]
        item
        for item in root["attributes"]  # type: ignore[index]
        if item["key"] != "sentinel.output"
    ]
    result = import_otel_document(doc, source_bytes=source_bytes(doc))
    run = result.runs[0]

    assert result.manifest.traces[0].partial is True
    assert run.completed is False
    assert run.error is not None
    assert "missing output" in run.error
    assert result.manifest.partial_runs == 1


def test_missing_parent_marks_trace_partial_without_inventing_root() -> None:
    doc = document()
    root = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]  # type: ignore[index]
    root["parentSpanId"] = "ffffffffffffffff"  # type: ignore[index]
    result = import_otel_document(doc, source_bytes=source_bytes(doc))

    assert result.manifest.traces[0].partial is True
    assert "root.parent_span" in (result.runs[0].error or "")


def test_rejects_malformed_identifier() -> None:
    doc = document()
    root = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]  # type: ignore[index]
    root["traceId"] = "not-a-trace"  # type: ignore[index]

    with pytest.raises(TraceImportError, match="malformed traceId"):
        import_otel_document(doc, source_bytes=source_bytes(doc))


def test_rejects_ambiguous_roots() -> None:
    doc = document()
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]  # type: ignore[index]
    spans[1].pop("parentSpanId")  # type: ignore[index]

    with pytest.raises(TraceImportError, match="ambiguous roots"):
        import_otel_document(doc, source_bytes=source_bytes(doc))


def test_rejects_parent_cycle() -> None:
    doc = document()
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]  # type: ignore[index]
    spans[0]["parentSpanId"] = spans[1]["spanId"]  # type: ignore[index]
    spans[1]["parentSpanId"] = spans[0]["spanId"]  # type: ignore[index]

    with pytest.raises(TraceImportError, match="cycle detected"):
        import_otel_document(doc, source_bytes=source_bytes(doc))


def test_case_id_must_be_explicit_or_present() -> None:
    doc = document()
    root = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]  # type: ignore[index]
    root["attributes"] = [  # type: ignore[index]
        item
        for item in root["attributes"]  # type: ignore[index]
        if item["key"] != "sentinel.case.id"
    ]

    with pytest.raises(TraceImportError, match="has no case id"):
        import_otel_document(doc, source_bytes=source_bytes(doc))

    result = import_otel_document(
        doc,
        source_bytes=source_bytes(doc),
        config=TraceImportConfig(case_id="override-case"),
    )
    assert result.runs[0].case_id == "override-case"


def test_path_and_cli_write_valid_jsonl_and_manifest(tmp_path: Path) -> None:
    source = tmp_path / "trace.json"
    output = tmp_path / "runs.jsonl"
    manifest = tmp_path / "manifest.json"
    source.write_text(json.dumps(document()), encoding="utf-8")

    direct = import_otel_path(source)
    assert direct.runs[0].case_id == "grounded-answer"

    exit_code = main(
        [
            "--input",
            str(source),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--redact",
            "deployment.environment",
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8").strip())
    evidence = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["case_id"] == "grounded-answer"
    assert evidence["traces"][0]["trace_id"] == TRACE_ID
    assert evidence["traces"][0]["metadata"]["deployment.environment"] == "[REDACTED]"
    assert evidence["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
