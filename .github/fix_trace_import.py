"""Apply the exact lint/type corrections reported by CI for trace_import.py."""

from pathlib import Path

path = Path("Sentinel/src/sentinel/trace_import.py")
text = path.read_text(encoding="utf-8")
replacements = {
    "return cast(JSONScalar, raw)": "return raw",
    "return cast(JSONScalar, value)": "return value",
    "if value is None or isinstance(value, list) or isinstance(value, bool):": "if value is None or isinstance(value, (list, bool)):",
    '''            status = cast(\n                Literal["allowed", "denied"],\n                "denied"\n                if decision in {"denied", "rejected", "false", "0"}\n                else "allowed",\n            )''': '''            status: Literal["allowed", "denied"] = (\n                "denied"\n                if decision in {"denied", "rejected", "false", "0"}\n                else "allowed"\n            )''',
}
for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one occurrence, found {count}: {old!r}")
    text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("Applied four exact CI corrections")
