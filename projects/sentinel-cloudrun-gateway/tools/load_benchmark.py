"""Measure real protected requests; no inferred success or excluded failures."""
import argparse
import hashlib
import json
import platform
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int(len(ordered) * fraction + 0.999999) - 1))]


def request(base, operation, index):
    body = {"tool": operation, "arguments": {"customer_id": "c-100"} if operation == "customer.read" else {"query": "renewal"}}
    started = time.perf_counter_ns()
    status, valid, error = None, False, None
    try:
        req = urllib.request.Request(base + "/v1/tool-calls", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer load-token-%02d" % (index % 50)})
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            data = json.loads(response.read())
        if operation == "customer.read":
            valid = data.get("customer_id") == "c-100" and isinstance(data.get("version"), int)
        else:
            docs = data.get("documents", [])
            valid = bool(docs) and all(d.get("untrusted") is True for d in docs)
    except urllib.error.HTTPError as exc:
        status, error = exc.code, "HTTP failure"
    except Exception as exc:
        error = type(exc).__name__
    return {"index": index, "operation": operation, "elapsed_ms": (time.perf_counter_ns() - started) / 1e6, "status": status, "content_valid": valid, "error": error}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not args.base_url.startswith("http://127.0.0.1:"):
        parser.error("This protocol permits only the isolated loopback stack")
    result = {"started_at": datetime.now(timezone.utc).isoformat(), "commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")), "platform": platform.platform(), "python": platform.python_version(), "protocol": "protected-routes-v1", "concurrency": 10, "samples_per_operation": 1000, "p95_threshold_ms": 100, "source_hashes": {}, "operations": []}
    for source in [Path("sentinel/api.py"), Path("sentinel/security.py"), Path(__file__), Path("evaluation/PERFORMANCE_PROTOCOL.md")]:
        if source.exists():
            result["source_hashes"][str(source)] = hashlib.sha256(source.read_bytes()).hexdigest()
    all_passed = True
    for operation in ["customer.read", "document.search"]:
        with ThreadPoolExecutor(max_workers=10) as executor:
            warmup = list(executor.map(lambda i: request(args.base_url, operation, i), range(50)))
            started = time.perf_counter()
            rows = list(executor.map(lambda i: request(args.base_url, operation, i), range(1000)))
            duration = time.perf_counter() - started
        latencies = [row["elapsed_ms"] for row in rows]
        failures = sum(row["status"] != 200 or not row["content_valid"] or row["error"] is not None for row in rows)
        warmup_failures = sum(row["status"] != 200 or not row["content_valid"] for row in warmup)
        summary = {"operation": operation, "status_counts": dict(Counter(str(r["status"]) for r in rows)), "failures": failures, "warmup_failures": warmup_failures, "p50_ms": percentile(latencies, .5), "p95_ms": percentile(latencies, .95), "p99_ms": percentile(latencies, .99), "max_ms": max(latencies), "duration_seconds": duration, "requests_per_second": len(rows) / duration}
        summary["passed"] = failures == 0 and warmup_failures == 0 and summary["p95_ms"] <= 100
        result["operations"].append({**summary, "warmup": warmup, "requests": rows})
        print(json.dumps(summary), flush=True)
        all_passed = all_passed and summary["passed"]
    result["passed"] = all_passed
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
