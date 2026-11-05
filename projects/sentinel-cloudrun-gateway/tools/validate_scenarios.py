"""Validate scenario inventory and holdout split before any benchmark run."""
import json
from collections import Counter
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "evaluation" / "scenarios.jsonl"
rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
assert len(rows) >= 200, len(rows)
assert len({r["id"] for r in rows}) == len(rows)
assert all(r["class"] in ("legitimate", "adversarial") for r in rows)
assert all(r["expected_tools"] for r in rows)
assert all(r["task"] and r["notes"] for r in rows)
families = Counter(r["family"] for r in rows if r["class"] == "adversarial")
heldout = {r["family"] for r in rows if r["split"] == "heldout"}
trained = {r["family"] for r in rows if r["split"] == "train" and r["class"] == "adversarial"}
assert heldout and heldout.isdisjoint(trained), (heldout, trained)
print(json.dumps({"rows":len(rows),"legitimate":sum(r["class"]=="legitimate" for r in rows),"adversarial":sum(r["class"]=="adversarial" for r in rows),"attack_families":dict(sorted(families.items())),"heldout_families":sorted(heldout),"heldout_rows":sum(r["split"]=="heldout" for r in rows)},indent=2))
