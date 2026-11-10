"""Reproducible local gateway baseline; does not mutate records or create approvals."""
import argparse
import concurrent.futures
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = os.getenv("SENTINEL_BASE_URL", "http://127.0.0.1:8080")
ROUTES = {
    "health": ("/health", None),
    "auth_mode": ("/v1/auth-mode", None),
    "tools": ("/v1/tools", "demo-alice"),
    "approval_queue": ("/v1/approvals", "demo-alice"),
    "audit_verify": ("/v1/audit/verify", "demo-alice"),
}


def percentile(samples, p):
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]


def request(route):
    path, token = ROUTES[route]
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(BASE + path, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        error.read()
    return time.perf_counter() - started, status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=1000, help="Requests per route")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--p95-limit-ms", type=float, default=100)
    parser.add_argument("--output", default="evaluation/performance-local.json")
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        raise SystemExit("requests and concurrency must be positive")
    report = {"date_utc": datetime.now(timezone.utc).isoformat(), "base_url": BASE, "environment": "local Docker Compose synthetic", "requests_per_route": args.requests, "concurrency": args.concurrency, "p95_limit_ms": args.p95_limit_ms, "routes": {}, "cost": "not applicable: local containers", "inference": "not applicable: deterministic fixture; no model provider"}
    all_start = time.perf_counter()
    failures = []
    for route in ROUTES:
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(pool.map(request, [route] * args.requests))
        elapsed = time.perf_counter() - started
        latencies = [r[0] * 1000 for r in results]
        statuses = {}
        for _, status in results:
            statuses[str(status)] = statuses.get(str(status), 0) + 1
        report["routes"][route] = {
            "requests": len(results), "statuses": statuses,
            "p50_ms": round(percentile(latencies, .50), 3),
            "p95_ms": round(percentile(latencies, .95), 3),
            "max_ms": round(max(latencies), 3),
            "elapsed_s": round(elapsed, 3),
            "throughput_rps": round(len(results) / elapsed, 2),
        }
        if statuses != {"200": args.requests}:
            failures.append(f"{route}: unexpected status counts {statuses}")
        if report["routes"][route]["p95_ms"] > args.p95_limit_ms:
            failures.append(f"{route}: p95 {report['routes'][route]['p95_ms']}ms exceeds {args.p95_limit_ms}ms")
    report["elapsed_total_s"] = round(time.perf_counter() - all_start, 3)
    report["aggregate_throughput_rps"] = round(args.requests * len(ROUTES) / report["elapsed_total_s"], 2)
    report["acceptance_target"] = f"{args.requests} per route, concurrency {args.concurrency}, all HTTP 200, p95 <= {args.p95_limit_ms}ms"
    with open(args.output, "w") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit("FAIL: " + "; ".join(failures))
    print("PASS: all route error counts and p95 latency limits met")


if __name__ == "__main__":
    main()
