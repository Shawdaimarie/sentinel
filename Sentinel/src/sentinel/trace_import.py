"""OpenTelemetry trace normalization for Sentinel evaluation runs.

The importer is deliberately offline and deterministic: it parses an OTLP JSON
export, validates trace topology, redacts sensitive metadata, and emits the
provider-neutral :class:`sentinel.evaluation.AgentRun` contract. Trace content
is treated as untrusted data and is never executed or used to contact a remote
endpoint.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, TypeAlias, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sentinel.evaluation import AgentRun, ToolAction

IMPORTER_NAME = "sentinel.otel.v1"
_HEX_16 = re.compile(r"^[0-9a-fA-F]{16}$")
_HEX_32 = re.compile(r"^[0-9a-fA-F]{32}$")

JSONScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JSONScalar | list[JSONScalar]

DEFAULT_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "http.request.header.authorization",
        "http.request.header.cookie",
        "http.response.header.set-cookie",
        "cookie",
        "set-cookie",
        "api_key",
        "api.key",
        "openai.api_key",
        "anthropic.api_key",
        "token",
        "access_token",
        "refresh_token",
        "password",
        "secret",
        "session",
        "user.email",
        "user.phone",
        "user.ssn",
    }
)

CASE_KEYS = ("sentinel.case.id", "eval.case.id", "case.id")
RUN_KEYS = ("sentinel.run.id", "run.id")
SYSTEM_KEYS = ("sentinel.system", "service.name")
OUTPUT_KEYS = (
    "sentinel.output",
    "gen_ai.response.text",
    "gen_ai.output.messages",
    "output.value",
)
COST_KEYS = ("sentinel.cost.usd", "gen_ai.usage.cost", "gen_ai.cost.usd")
TOOL_NAME_KEYS = ("gen_ai.tool.name", "sentinel.tool.name", "tool.name")
TOOL_TARGET_KEYS = (
    "sentinel.tool.target",
    "url.full",
    "http.url",
    "db.operation.name",
    "db.statement",
)
ACTION_STATUS_KEYS = ("sentinel.action.status", "tool.status")
ATTEMPT_KEYS = ("sentinel.retry.attempt", "retry.attempt", "tool.attempt")
EVIDENCE_KEYS = (
    "sentinel.evidence.url",
    "sentinel.evidence.urls",
    "gen_ai.evidence.url",
    "evidence.url",
)
APPROVAL_KEYS = ("sentinel.approval.status", "approval.status", "approval.decision")


class TraceImportError(ValueError):
    """Raised when an OTLP export cannot be normalized without invention."""


class TraceImportConfig(BaseModel):
    """Deterministic mapping, redaction, and metadata limits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    system: str = "candidate"
    case_id: str | None = None
    additional_redactions: frozenset[str] = Field(default_factory=frozenset)
    max_metadata_entries: int = Field(default=32, ge=0, le=256)
    max_metadata_value_length: int = Field(default=256, ge=16, le=4096)

    @field_validator("system")
    @classmethod
    def _system_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("system must not be blank")
        return value

    @field_validator("case_id")
    @classmethod
    def _case_is_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("case_id must not be blank")
        return value

    @field_validator("additional_redactions")
    @classmethod
    def _normalize_redactions(cls, values: frozenset[str]) -> frozenset[str]:
        return frozenset(value.strip().lower() for value in values if value.strip())

    @property
    def sensitive_keys(self) -> frozenset[str]:
        return DEFAULT_SENSITIVE_KEYS | self.additional_redactions


class TraceActionRecord(BaseModel):
    """Trace topology and retry evidence kept outside the strict AgentRun contract."""

    model_config = ConfigDict(extra="forbid")

    span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    parent_span_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    name: str
    target: str = ""
    status: Literal["proposed", "allowed", "denied", "executed", "failed"]
    attempt: int = Field(default=1, ge=1)
    start_ns: int | None = Field(default=None, ge=0)
    metadata: dict[str, JSONScalar] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    """Per-trace provenance, completeness, topology, and bounded metadata."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    root_span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    case_id: str
    run_id: str
    partial: bool
    missing_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, JSONScalar] = Field(default_factory=dict)
    actions: list[TraceActionRecord] = Field(default_factory=list)


class TraceImportManifest(BaseModel):
    """Evidence proving which source and configuration produced the runs."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "sentinel.otel.import.v1"
    importer: str = IMPORTER_NAME
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    trace_count: int = Field(ge=0)
    run_count: int = Field(ge=0)
    partial_runs: int = Field(ge=0)
    redacted_attribute_count: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    traces: list[TraceRecord] = Field(default_factory=list)


class TraceImportResult(BaseModel):
    """Strict AgentRun records plus a separate reproducibility manifest."""

    model_config = ConfigDict(extra="forbid")

    runs: list[AgentRun]
    manifest: TraceImportManifest


class _Span(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_ns: int | None
    end_ns: int | None
    attributes: dict[str, JsonValue]
    events: list[dict[str, Any]]
    status_code: str


class _RedactionState:
    def __init__(self) -> None:
        self.count = 0


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _config_hash(config: TraceImportConfig) -> str:
    data = config.model_dump(mode="json")
    data["effective_sensitive_keys"] = sorted(config.sensitive_keys)
    return _sha256_bytes(_canonical_json(data))


def _otlp_value(raw: object) -> JsonValue:
    if not isinstance(raw, Mapping):
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            return raw
        raise TraceImportError(f"unsupported OTLP value: {type(raw).__name__}")

    known = (
        "stringValue",
        "boolValue",
        "intValue",
        "doubleValue",
        "bytesValue",
    )
    for key in known:
        if key in raw:
            value = raw[key]
            if key == "intValue":
                try:
                    return int(cast(str | int, value))
                except (TypeError, ValueError) as exc:
                    raise TraceImportError(f"invalid OTLP intValue: {value!r}") from exc
            if key == "doubleValue":
                try:
                    return float(cast(str | int | float, value))
                except (TypeError, ValueError) as exc:
                    raise TraceImportError(f"invalid OTLP doubleValue: {value!r}") from exc
            if key == "bytesValue":
                return "[BINARY]"
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            raise TraceImportError(f"invalid OTLP {key}: {value!r}")

    array = raw.get("arrayValue")
    if isinstance(array, Mapping):
        values = array.get("values", [])
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise TraceImportError("OTLP arrayValue.values must be an array")
        result: list[JSONScalar] = []
        for item in values:
            parsed = _otlp_value(item)
            if isinstance(parsed, list):
                result.append(json.dumps(parsed, sort_keys=True, separators=(",", ":")))
            else:
                result.append(parsed)
        return result

    kvlist = raw.get("kvlistValue")
    if isinstance(kvlist, Mapping):
        values = kvlist.get("values", [])
        return json.dumps(_attributes(values), sort_keys=True, separators=(",", ":"))

    if "value" in raw:
        return _otlp_value(raw["value"])
    raise TraceImportError(f"unrecognized OTLP value object: {sorted(map(str, raw))}")


def _attributes(raw: object) -> dict[str, JsonValue]:
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        result: dict[str, JsonValue] = {}
        for key, value in raw.items():
            result[str(key)] = _otlp_value(value)
        return result
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TraceImportError("attributes must be an OTLP key/value array or object")

    result = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise TraceImportError("attribute entries must be objects")
        key = item.get("key")
        if not isinstance(key, str) or not key.strip():
            raise TraceImportError("attribute key must be a non-empty string")
        if key in result:
            raise TraceImportError(f"duplicate attribute key: {key}")
        result[key] = _otlp_value(item.get("value"))
    return result


def _normalize_id(value: object, *, length: int, label: str) -> str:
    if not isinstance(value, str):
        raise TraceImportError(f"{label} must be a hexadecimal string")
    normalized = value.strip().lower()
    pattern = _HEX_32 if length == 32 else _HEX_16
    if pattern.fullmatch(normalized) is None:
        raise TraceImportError(f"malformed {label}: {value!r}")
    return normalized


def _optional_parent(value: object) -> str | None:
    if value is None or value == "":
        return None
    return _normalize_id(value, length=16, label="parentSpanId")


def _nano_time(value: object, label: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(cast(str | int, value))
    except (TypeError, ValueError) as exc:
        raise TraceImportError(f"{label} must be an integer nanosecond timestamp") from exc
    if parsed < 0:
        raise TraceImportError(f"{label} must be non-negative")
    return parsed


def _status_code(raw: object) -> str:
    if isinstance(raw, Mapping):
        raw = raw.get("code", "UNSET")
    if isinstance(raw, int):
        return {0: "UNSET", 1: "OK", 2: "ERROR"}.get(raw, "UNSET")
    if isinstance(raw, str):
        value = raw.strip().upper()
        aliases = {"STATUS_CODE_OK": "OK", "STATUS_CODE_ERROR": "ERROR"}
        return aliases.get(value, value or "UNSET")
    return "UNSET"


def _event(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TraceImportError("span events must be objects")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise TraceImportError("span event name must be a non-empty string")
    return {
        "name": name.strip(),
        "time_ns": _nano_time(raw.get("timeUnixNano"), "event.timeUnixNano"),
        "attributes": _attributes(raw.get("attributes", [])),
    }


def _iter_span_records(
    document: Mapping[str, Any],
) -> Iterable[tuple[Mapping[str, Any], dict[str, JsonValue]]]:
    top_level = document.get("spans")
    if top_level is not None:
        if not isinstance(top_level, Sequence) or isinstance(top_level, (str, bytes)):
            raise TraceImportError("top-level spans must be an array")
        for raw_span in top_level:
            if not isinstance(raw_span, Mapping):
                raise TraceImportError("span entries must be objects")
            yield raw_span, {}

    resource_spans = document.get("resourceSpans", [])
    if not isinstance(resource_spans, Sequence) or isinstance(resource_spans, (str, bytes)):
        raise TraceImportError("resourceSpans must be an array")
    for resource_group in resource_spans:
        if not isinstance(resource_group, Mapping):
            raise TraceImportError("resourceSpans entries must be objects")
        resource_raw = resource_group.get("resource", {})
        resource_attrs = _attributes(
            resource_raw.get("attributes", []) if isinstance(resource_raw, Mapping) else []
        )
        scope_groups = resource_group.get(
            "scopeSpans", resource_group.get("instrumentationLibrarySpans", [])
        )
        if not isinstance(scope_groups, Sequence) or isinstance(scope_groups, (str, bytes)):
            raise TraceImportError("scopeSpans must be an array")
        for scope_group in scope_groups:
            if not isinstance(scope_group, Mapping):
                raise TraceImportError("scopeSpans entries must be objects")
            spans = scope_group.get("spans", [])
            if not isinstance(spans, Sequence) or isinstance(spans, (str, bytes)):
                raise TraceImportError("scopeSpans.spans must be an array")
            for raw_span in spans:
                if not isinstance(raw_span, Mapping):
                    raise TraceImportError("span entries must be objects")
                yield raw_span, resource_attrs


def _parse_spans(document: Mapping[str, Any]) -> list[_Span]:
    parsed: list[_Span] = []
    seen: set[tuple[str, str]] = set()
    for raw, resource_attrs in _iter_span_records(document):
        trace_id = _normalize_id(raw.get("traceId"), length=32, label="traceId")
        span_id = _normalize_id(raw.get("spanId"), length=16, label="spanId")
        identity = (trace_id, span_id)
        if identity in seen:
            raise TraceImportError(f"duplicate spanId {span_id} in trace {trace_id}")
        seen.add(identity)
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise TraceImportError(f"span {span_id} name must be a non-empty string")
        attrs = dict(resource_attrs)
        attrs.update(_attributes(raw.get("attributes", [])))
        events_raw = raw.get("events", [])
        if not isinstance(events_raw, Sequence) or isinstance(events_raw, (str, bytes)):
            raise TraceImportError("span events must be an array")
        parsed.append(
            _Span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=_optional_parent(raw.get("parentSpanId")),
                name=name.strip(),
                start_ns=_nano_time(raw.get("startTimeUnixNano"), "startTimeUnixNano"),
                end_ns=_nano_time(raw.get("endTimeUnixNano"), "endTimeUnixNano"),
                attributes=attrs,
                events=[_event(event) for event in events_raw],
                status_code=_status_code(raw.get("status")),
            )
        )
    if not parsed:
        raise TraceImportError("trace export contains no spans")
    return parsed


def _detect_cycles(spans: Sequence[_Span]) -> None:
    by_id = {span.span_id: span for span in spans}
    for span in spans:
        visited: set[str] = set()
        current = span
        while current.parent_span_id and current.parent_span_id in by_id:
            if current.span_id in visited:
                raise TraceImportError(f"cycle detected in trace {span.trace_id}")
            visited.add(current.span_id)
            current = by_id[current.parent_span_id]
        if current.span_id in visited:
            raise TraceImportError(f"cycle detected in trace {span.trace_id}")


def _root_for(spans: Sequence[_Span]) -> tuple[_Span, bool]:
    by_id = {span.span_id for span in spans}
    candidates = [
        span for span in spans if span.parent_span_id is None or span.parent_span_id not in by_id
    ]
    if len(candidates) != 1:
        ids = ", ".join(span.span_id for span in candidates) or "none"
        raise TraceImportError(
            f"trace {spans[0].trace_id} has ambiguous roots ({len(candidates)}): {ids}"
        )
    root = candidates[0]
    partial_parent = root.parent_span_id is not None
    return root, partial_parent


def _first(attrs: Mapping[str, JsonValue], keys: Sequence[str]) -> JsonValue | None:
    for key in keys:
        if key in attrs:
            return attrs[key]
    return None


def _as_string(value: JsonValue | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def _as_float(value: JsonValue | None) -> float | None:
    if value is None or isinstance(value, (list, bool)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: JsonValue | None) -> int | None:
    number = _as_float(value)
    if number is None or number < 1 or not number.is_integer():
        return None
    return int(number)


def _redact_url(value: str, state: _RedactionState) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value[:512]
    if parsed.scheme not in {"http", "https"}:
        return value[:512]
    hostname = parsed.hostname or ""
    try:
        parsed_port = parsed.port
    except ValueError:
        state.count += 1
        parsed_port = None
    port = f":{parsed_port}" if parsed_port is not None else ""
    netloc = f"{hostname}{port}"
    if parsed.username or parsed.password:
        state.count += 1
    query: list[tuple[str, str]] = []
    for key, raw_value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if any(
            token in lowered
            for token in ("token", "key", "secret", "password", "auth", "session")
        ):
            query.append((key, "[REDACTED]"))
            state.count += 1
        else:
            query.append((key, raw_value[:256]))
    return urlunsplit((parsed.scheme, netloc, parsed.path[:1024], urlencode(query), ""))


def _safe_scalar(value: JsonValue, limit: int, state: _RedactionState) -> JSONScalar:
    if isinstance(value, list):
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return text[:limit]
    if isinstance(value, str):
        text = _redact_url(value, state) if value.startswith(("http://", "https://")) else value
        return text[:limit]
    return value


def _bounded_metadata(
    attrs: Mapping[str, JsonValue],
    *,
    consumed: set[str],
    config: TraceImportConfig,
    state: _RedactionState,
) -> dict[str, JSONScalar]:
    result: dict[str, JSONScalar] = {}
    for key in sorted(attrs):
        lowered = key.lower()
        if key in consumed:
            continue
        if lowered in config.sensitive_keys or any(
            token in lowered
            for token in ("authorization", "cookie", "password", "api_key", "secret")
        ):
            result[key] = "[REDACTED]"
            state.count += 1
        else:
            result[key] = _safe_scalar(
                attrs[key], config.max_metadata_value_length, state
            )
        if len(result) >= config.max_metadata_entries:
            break
    return result


def _span_kind(span: _Span) -> str:
    raw = _first(
        span.attributes,
        ("sentinel.span.kind", "openinference.span.kind", "gen_ai.operation.name"),
    )
    value = (_as_string(raw) or "").strip().lower()
    name = span.name.lower()
    if value in {"tool", "execute_tool", "tool_call"} or name.startswith("tool."):
        return "tool"
    if value in {"approval", "human_approval"} or "approval" in name:
        return "approval"
    return "other"


def _action_status(span: _Span, kind: str) -> str:
    explicit = (_as_string(_first(span.attributes, ACTION_STATUS_KEYS)) or "").lower()
    if explicit in {"proposed", "allowed", "denied", "executed", "failed"}:
        return explicit
    if kind == "approval":
        decision = (_as_string(_first(span.attributes, APPROVAL_KEYS)) or "").lower()
        if decision in {"denied", "rejected", "false", "0"}:
            return "denied"
        if decision in {"approved", "allowed", "true", "1"}:
            return "allowed"
    return "failed" if span.status_code == "ERROR" else "executed"


def _latency_ms(span: _Span) -> int:
    if span.start_ns is None or span.end_ns is None or span.end_ns < span.start_ns:
        return 0
    return int((span.end_ns - span.start_ns) / 1_000_000)


def _cost_usd(span: _Span) -> float:
    value = _as_float(_first(span.attributes, COST_KEYS))
    return max(0.0, value or 0.0)


def _action_from_span(
    span: _Span,
    *,
    kind: str,
    derived_attempt: int,
    config: TraceImportConfig,
    state: _RedactionState,
) -> tuple[ToolAction, TraceActionRecord]:
    name = _as_string(_first(span.attributes, TOOL_NAME_KEYS))
    if not name:
        name = "human.approval" if kind == "approval" else span.name.removeprefix("tool.")
    target = _as_string(_first(span.attributes, TOOL_TARGET_KEYS)) or ""
    if target.startswith(("http://", "https://")):
        target = _redact_url(target, state)
    target = target[:1024]
    status = cast(
        Literal["proposed", "allowed", "denied", "executed", "failed"],
        _action_status(span, kind),
    )
    attempt = _as_int(_first(span.attributes, ATTEMPT_KEYS)) or derived_attempt
    consumed = set(TOOL_NAME_KEYS + TOOL_TARGET_KEYS + ACTION_STATUS_KEYS + ATTEMPT_KEYS)
    metadata = _bounded_metadata(
        span.attributes, consumed=consumed, config=config, state=state
    )
    return (
        ToolAction(
            name=name.strip(),
            target=target,
            status=status,
            latency_ms=_latency_ms(span),
            cost_usd=_cost_usd(span),
        ),
        TraceActionRecord(
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            name=name.strip(),
            target=target,
            status=status,
            attempt=attempt,
            start_ns=span.start_ns,
            metadata=metadata,
        ),
    )


def _actions(
    spans: Sequence[_Span],
    config: TraceImportConfig,
    state: _RedactionState,
) -> tuple[list[ToolAction], list[TraceActionRecord]]:
    ordered = sorted(
        spans,
        key=lambda span: (span.start_ns is None, span.start_ns or 0, span.span_id),
    )
    counters: defaultdict[tuple[str, str], int] = defaultdict(int)
    candidates: list[tuple[tuple[bool, int, str, int], ToolAction, TraceActionRecord]] = []
    for span in ordered:
        kind = _span_kind(span)
        if kind not in {"tool", "approval"}:
            continue
        raw_name = _as_string(_first(span.attributes, TOOL_NAME_KEYS)) or span.name
        raw_target = _as_string(_first(span.attributes, TOOL_TARGET_KEYS)) or ""
        identity = (raw_name, raw_target)
        counters[identity] += 1
        action, record = _action_from_span(
            span,
            kind=kind,
            derived_attempt=counters[identity],
            config=config,
            state=state,
        )
        candidates.append(
            (
                (span.start_ns is None, span.start_ns or 0, span.span_id, 0),
                action,
                record,
            )
        )

        for event_index, event in enumerate(
            sorted(span.events, key=lambda item: item["time_ns"] or 0),
            start=1,
        ):
            event_name = cast(str, event["name"])
            event_attrs = cast(dict[str, JsonValue], event["attributes"])
            if "approval" not in event_name.lower():
                continue
            decision = (_as_string(_first(event_attrs, APPROVAL_KEYS)) or "").lower()
            status: Literal["allowed", "denied"] = (
                "denied"
                if decision in {"denied", "rejected", "false", "0"}
                else "allowed"
            )
            event_metadata = _bounded_metadata(
                event_attrs,
                consumed=set(APPROVAL_KEYS),
                config=config,
                state=state,
            )
            event_time = cast(int | None, event["time_ns"])
            event_action = ToolAction(
                name="human.approval",
                target=event_name,
                status=status,
            )
            event_record = TraceActionRecord(
                span_id=span.span_id,
                parent_span_id=span.parent_span_id,
                name="human.approval",
                target=event_name,
                status=status,
                start_ns=event_time,
                metadata=event_metadata,
            )
            candidates.append(
                (
                    (event_time is None, event_time or 0, span.span_id, event_index),
                    event_action,
                    event_record,
                )
            )

    candidates.sort(key=lambda item: item[0])
    return (
        [candidate[1] for candidate in candidates],
        [candidate[2] for candidate in candidates],
    )

def _evidence_urls(spans: Sequence[_Span], state: _RedactionState) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for span in spans:
        values: list[JsonValue] = []
        for key in EVIDENCE_KEYS:
            if key in span.attributes:
                values.append(span.attributes[key])
        for event in span.events:
            if "evidence" in cast(str, event["name"]).lower():
                attrs = cast(dict[str, JsonValue], event["attributes"])
                for key in EVIDENCE_KEYS:
                    if key in attrs:
                        values.append(attrs[key])
        for value in values:
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if not isinstance(candidate, str):
                    continue
                cleaned = _redact_url(candidate.strip(), state)
                parsed = urlsplit(cleaned)
                if parsed.scheme in {"http", "https"} and parsed.hostname and cleaned not in seen:
                    seen.add(cleaned)
                    result.append(cleaned)
    return result


def _trace_latency_ms(spans: Sequence[_Span], root: _Span) -> tuple[int, bool]:
    if root.start_ns is not None and root.end_ns is not None and root.end_ns >= root.start_ns:
        return int((root.end_ns - root.start_ns) / 1_000_000), False
    starts = [span.start_ns for span in spans if span.start_ns is not None]
    ends = [span.end_ns for span in spans if span.end_ns is not None]
    if starts and ends and max(ends) >= min(starts):
        return int((max(ends) - min(starts)) / 1_000_000), True
    return 0, True


def _run_for_trace(
    spans: Sequence[_Span],
    *,
    config: TraceImportConfig,
    state: _RedactionState,
) -> tuple[AgentRun, TraceRecord, list[str]]:
    _detect_cycles(spans)
    root, missing_parent = _root_for(spans)
    warnings: list[str] = []
    missing: list[str] = []

    case_id = config.case_id or _as_string(_first(root.attributes, CASE_KEYS))
    if not case_id:
        raise TraceImportError(
            f"trace {root.trace_id} has no case id; pass --case-id or set sentinel.case.id"
        )
    run_id = _as_string(_first(root.attributes, RUN_KEYS)) or root.trace_id
    system = _as_string(_first(root.attributes, SYSTEM_KEYS)) or config.system
    output = _as_string(_first(root.attributes, OUTPUT_KEYS)) or ""
    if not output:
        missing.append("output")
    if root.start_ns is None:
        missing.append("root.startTimeUnixNano")
    if root.end_ns is None:
        missing.append("root.endTimeUnixNano")
    if missing_parent:
        missing.append("root.parent_span")

    latency_ms, derived_latency = _trace_latency_ms(spans, root)
    if derived_latency:
        warnings.append(f"trace {root.trace_id}: latency derived from available child spans")
    actions, action_records = _actions(spans, config, state)
    evidence = _evidence_urls(spans, state)
    cost = sum(_cost_usd(span) for span in spans)
    partial = bool(missing)
    completed = root.status_code != "ERROR" and not partial
    error: str | None = None
    if root.status_code == "ERROR":
        error = "root span reported ERROR"
    if partial:
        suffix = "partial telemetry: missing " + ", ".join(sorted(missing))
        error = f"{error}; {suffix}" if error else suffix

    consumed = set(CASE_KEYS + RUN_KEYS + SYSTEM_KEYS + OUTPUT_KEYS + COST_KEYS + EVIDENCE_KEYS)
    metadata = _bounded_metadata(
        root.attributes, consumed=consumed, config=config, state=state
    )
    run = AgentRun(
        case_id=case_id,
        run_id=run_id,
        system=system,
        output=output,
        completed=completed,
        actions=actions,
        evidence_urls=evidence,
        latency_ms=latency_ms,
        cost_usd=cost,
        error=error,
    )
    trace_record = TraceRecord(
        trace_id=root.trace_id,
        root_span_id=root.span_id,
        case_id=case_id,
        run_id=run_id,
        partial=partial,
        missing_fields=sorted(missing),
        metadata=metadata,
        actions=action_records,
    )
    return run, trace_record, warnings

def import_otel_document(
    document: Mapping[str, Any],
    *,
    source_bytes: bytes,
    config: TraceImportConfig | None = None,
) -> TraceImportResult:
    """Normalize an OTLP JSON object into deterministic Sentinel runs."""

    config = config or TraceImportConfig()
    spans = _parse_spans(document)
    grouped: defaultdict[str, list[_Span]] = defaultdict(list)
    for span in spans:
        grouped[span.trace_id].append(span)

    source_hash = _sha256_bytes(source_bytes)
    state = _RedactionState()
    runs: list[AgentRun] = []
    trace_records: list[TraceRecord] = []
    warnings: list[str] = []
    for trace_id in sorted(grouped):
        run, trace_record, trace_warnings = _run_for_trace(
            grouped[trace_id], config=config, state=state
        )
        runs.append(run)
        trace_records.append(trace_record)
        warnings.extend(trace_warnings)

    manifest = TraceImportManifest(
        source_sha256=source_hash,
        config_sha256=_config_hash(config),
        trace_count=len(grouped),
        run_count=len(runs),
        partial_runs=sum(record.partial for record in trace_records),
        redacted_attribute_count=state.count,
        warnings=warnings,
        traces=trace_records,
    )
    return TraceImportResult(runs=runs, manifest=manifest)


def import_otel_path(path: Path, config: TraceImportConfig | None = None) -> TraceImportResult:
    """Read and normalize an OTLP JSON export from disk."""

    source = path.read_bytes()
    try:
        document = json.loads(source)
    except json.JSONDecodeError as exc:
        raise TraceImportError(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON") from exc
    if not isinstance(document, Mapping):
        raise TraceImportError("OTLP export root must be a JSON object")
    return import_otel_document(document, source_bytes=source, config=config)


def write_runs_jsonl(path: Path, runs: Sequence[AgentRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(run.model_dump_json(exclude_none=True) for run in runs)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_manifest(path: Path, manifest: TraceImportManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
