# Local protected-route performance protocol v1

Declared before execution on 2026-11-02. This is local capacity evidence, not Cloud Run scalability, network SLO, or hosted-model latency evidence.

Use an isolated Compose database/gateway; never run against the user's active demonstration. Use 50 synthetic owner identities in tenant-a, normal application rate limit 60 calls per minute per actor. Each actor makes 20 measured customer-read calls and 20 measured document-search calls plus at most one warmup call per route; no policy or rate limiter is disabled.

Run 10 concurrent HTTP clients, 50 warmup calls, then 1,000 measured calls for each protected operation in sequence: `customer.read(c-100)` and `document.search(renewal)`, both through `/v1/tool-calls`. The workload includes authentication, database access and audit persistence. It excludes model inference and approval/execution mutations; it does not establish performance of those routes.

Acceptance: all 1,000 requests per operation return HTTP 200 and valid expected content; zero timeouts, 429s, unexpected responses or content failures; end-to-end client p95 ≤100 ms separately for both operations. Retain p50/p95/p99/max, throughput, status counts and raw per-request latency/content results. Failed requests are counted, not dropped. Timestamp, platform, code revision, dirty-state status and source hashes accompany the output. The 100 ms criterion is inherited from SCORECARD.md; do not relax it after failure.

Use this workload to find bottlenecks, then rerun unchanged after corrective implementation. Shared-host noise is a limitation and should be reported, not used to discard a failed run. Cloud staging must repeat an independently declared workload with actual costs and the production identity/network configuration.
