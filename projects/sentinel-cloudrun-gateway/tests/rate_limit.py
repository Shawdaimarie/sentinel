"""Exercise the per-actor request limit using a dedicated synthetic identity."""
import json
import os
import time
import urllib.error
import urllib.request

BASE = os.getenv("SENTINEL_BASE_URL", "http://127.0.0.1:8080")


def call(path, token="demo-ratelimit"):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps({"tool": "document.search", "arguments": {"query": "renewal"}}).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def main():
    # Start near the beginning of a fixed minute bucket, leaving a wide margin
    # so this test cannot accidentally split its requests across two buckets.
    bucket_offset = time.time() % 60
    if bucket_offset > 5:
        time.sleep(60 - bucket_offset + 2)
    started = time.monotonic()
    statuses = [call("/v1/tool-calls")[0] for _ in range(70)]
    elapsed = time.monotonic() - started
    assert elapsed < 50, f"Rate-limit probe crossed its controlled request window ({elapsed:.2f}s)"
    assert statuses.count(200) == 60, statuses
    assert statuses.count(429) == 10, statuses
    request = urllib.request.Request(
        BASE + "/v1/audit/events",
        headers={"Authorization": "Bearer demo-ratelimit"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        audit = json.loads(response.read())["events"]
    assert any(event["action"] == "tool.rate_limit" for event in audit), audit
    print(f"PASS: per-actor rate limit (60 allowed, 10 denied in {elapsed:.2f}s)")


if __name__ == "__main__":
    main()
