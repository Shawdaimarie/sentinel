"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sentinel import orchestrator
from sentinel.audit import AuditError, AuditLog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="crawl, verify, probe, and report")
    run.add_argument("--policy", type=Path, default=Path("policy.yaml"))
    run.add_argument("--audit", type=Path, default=Path("audit/sentinel.jsonl"))
    run.add_argument("--page", action="append", default=[], help="page URL to crawl (repeatable)")
    run.add_argument(
        "--control", action="append", default=[], help="endpoint to probe (repeatable)"
    )
    run.add_argument("--llm", action="store_true", help="enable Claude for semantic verification")
    run.add_argument(
        "--policy-sha256", help="refuse to run unless the policy file matches this fingerprint"
    )

    verify = sub.add_parser("verify-audit", help="check the audit chain for tampering")
    verify.add_argument("--audit", type=Path, default=Path("audit/sentinel.jsonl"))

    args = parser.parse_args(argv)

    if args.command == "run":
        result = orchestrator.run(
            policy_path=args.policy,
            audit_path=args.audit,
            pages=args.page,
            controls=args.control,
            use_llm=args.llm,
            policy_sha256=args.policy_sha256,
        )
        print(
            f"claims: {len(result.verifications)}  probes: {len(result.probes)}  "
            f"violations: {len(result.violations)}  failures: {len(result.failures)}"
        )
        for violation in result.violations:
            print(f"  denied: {violation}", file=sys.stderr)
        if result.report_path:
            print(f"report: {result.report_path}")
        return 0

    log = AuditLog(args.audit)
    try:
        count = log.verify()
    except AuditError as exc:
        print(f"audit chain INVALID: {exc}", file=sys.stderr)
        return 1
    mode = "HMAC-SHA256 (keyed)" if log.keyed else "SHA-256 (unkeyed)"
    print(f"audit chain valid: {count} records, {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
