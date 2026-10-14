"""Measure the installed offline evaluator against previously merged criteria.

POSIX only: each short-lived measurement wrapper owns exactly one evaluator
child, so getrusage(CHILDREN) cannot mix measurements from concurrent workers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("a percentile requires samples")
    return sorted(values)[max(0, math.ceil(len(values) * quantile) - 1)]


def valid_report(report: dict, hashes: dict, count: int) -> bool:
    results = report.get("results", [])
    return (
        report.get("input_hashes") == hashes
        and report.get("run_count") == count
        and len(results) == count
        and report.get("gate_passed") is True
        and report.get("safety_pass_rate") == 1.0
        and all(r.get("passed") is True and r.get("safety_passed") is True for r in results)
    )


def summarize(
    rows: list[dict],
    duration: float,
    concurrency: int,
    limits: dict,
    acceptance: dict,
    minimum_samples: int,
) -> dict:
    good = [r for r in rows if r["ok"]]
    errors = len(rows) - len(good)
    latencies = [r["seconds"] for r in rows]
    rss = [r["peak_rss_mib"] for r in rows]
    metrics_complete = all(
        math.isfinite(r[k]) and r[k] >= 0
        for r in rows
        for k in ("seconds", "peak_rss_mib", "cpu_seconds")
    )
    summary = {
        "attempts": len(rows),
        "validated_batches": len(good),
        "unexpected_errors": errors,
        "error_rate": errors / len(rows) if rows else None,
        "seconds": duration,
        "concurrency": concurrency,
        "p50_seconds": percentile(latencies, 0.5) if rows else None,
        "p95_seconds": percentile(latencies, 0.95) if rows else None,
        "p99_seconds": percentile(latencies, 0.99) if rows else None,
        "batches_per_second": len(good) / duration if duration > 0 else 0,
        "maximum_worker_peak_rss_mib": max(rss, default=0),
        "sum_worker_peak_rss_upper_bound_mib": sum(sorted(rss, reverse=True)[:concurrency]),
        "cpu_seconds": sum(r["cpu_seconds"] for r in rows),
        "currency_cost_per_successful_operation": None,
    }
    summary["cpu_seconds_per_validated_batch"] = (
        summary["cpu_seconds"] / len(good) if good else None
    )
    failures = []
    if len(rows) < minimum_samples or not metrics_complete:
        failures.append("insufficient samples or missing resource metrics")
    if errors > acceptance["maximum_unexpected_errors"]:
        failures.append("unexpected operation errors")
    for key in ("p95_seconds", "p99_seconds"):
        if summary[key] is None or summary[key] > limits[key]:
            failures.append(key)
    if summary["batches_per_second"] < limits.get("minimum_batches_per_second", 0):
        failures.append("throughput")
    if summary["maximum_worker_peak_rss_mib"] > acceptance["maximum_worker_peak_rss_mib"]:
        failures.append("worker memory")
    if (
        summary["sum_worker_peak_rss_upper_bound_mib"]
        > acceptance["maximum_sum_worker_peak_rss_mib"]
    ):
        failures.append("concurrent memory upper bound")
    summary["failures"] = failures
    summary["status"] = "PASS" if not failures else "FAIL"
    return summary


def measure_child(argv: list[str]) -> None:
    timeout = float(argv[0])
    started = time.perf_counter()
    try:
        result = subprocess.run(argv[1:], capture_output=True, timeout=timeout, check=False)
        code = result.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        code, timed_out = None, True
    elapsed = time.perf_counter() - started
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    print(
        json.dumps(
            {
                "exit_code": code,
                "timed_out": timed_out,
                "seconds": elapsed,
                "cpu_seconds": usage.ru_utime + usage.ru_stime,
                "peak_rss_mib": usage.ru_maxrss / divisor,
            }
        )
    )


class Runner:
    def __init__(self, args: argparse.Namespace, criteria: dict, output: Path):
        self.args, self.criteria, self.output = args, criteria, output
        self.started = time.perf_counter()
        self.lock = threading.Lock()
        self.sequence = 0
        self.raw = (output / "operations.jsonl").open("x")
        self.script = Path(__file__).resolve()
        self.hashes = {
            name: digest((output / f"{name}.jsonl").read_bytes()) for name in ("cases", "runs")
        }

    def operation(self, stage: str, failure: str | None = None) -> dict:
        with self.lock:
            self.sequence += 1
            number = self.sequence
        folder = self.output / "operations" / str(number)
        folder.mkdir(parents=True)
        json_out, md_out = folder / "report.json", folder / "report.md"
        seed = b"previous verified report\n"
        if failure:
            json_out.write_bytes(seed)
            md_out.write_bytes(seed)
        runs = self.output / (
            "missing.jsonl"
            if failure == "missing"
            else "malformed.jsonl"
            if failure == "malformed"
            else "runs.jsonl"
        )
        command = [
            str(self.args.python),
            "-m",
            "sentinel.eval_cli",
            "--cases",
            str(self.output / "cases.jsonl"),
            "--runs",
            str(runs),
            "--report",
            str(md_out),
            "--json-out",
            str(json_out),
        ]
        timeout = self.criteria["execution"]["per_batch_timeout_seconds"]
        # Wrapper startup is excluded; evaluator startup through exit is timed.
        result = subprocess.run(
            [sys.executable, str(self.script), "--measure-child", str(timeout), *command],
            capture_output=True,
            text=True,
            check=True,
            cwd=self.output,
            env=self.args.env,
            timeout=timeout + 5,
        )
        row = json.loads(result.stdout)
        row.update(stage=stage, operation=number, kind=failure or "valid")
        if failure:
            row["outputs_preserved"] = json_out.read_bytes() == seed and md_out.read_bytes() == seed
            row["ok"] = (
                row["exit_code"] == self.criteria["acceptance"]["required_failure_exit_code"]
                and not row["timed_out"]
                and row["outputs_preserved"]
                and row["seconds"] <= self.criteria["acceptance"]["failure_recovery_seconds"]
            )
        else:
            try:
                report = json.loads(json_out.read_text())
                row["ok"] = (
                    row["exit_code"] == 0
                    and not row["timed_out"]
                    and md_out.is_file()
                    and valid_report(
                        report, self.hashes, self.criteria["dataset"]["runs_per_batch"]
                    )
                )
            except (OSError, ValueError, TypeError):
                row["ok"] = False
        row["report_sha256"] = digest(json_out.read_bytes()) if json_out.is_file() else None
        with self.lock:
            self.raw.write(json.dumps(row, sort_keys=True) + "\n")
            self.raw.flush()
        # Keep one normal pair per stage, plus every negative or failed pair.
        # Every operation retains validation and report hashes in operations.jsonl.
        retained = self.output / f"sample-{stage}.json"
        with self.lock:
            if not failure and row["ok"] and not retained.exists():
                retained.write_bytes(json_out.read_bytes())
                (self.output / f"sample-{stage}.md").write_bytes(md_out.read_bytes())
            if not failure and row["ok"]:
                json_out.unlink()
                md_out.unlink()
                folder.rmdir()
        return row

    def stage(self, name: str, concurrency: int, seconds: int, limits: dict) -> dict:
        started = time.perf_counter()
        rows, launched = [], 0
        minimum = self.criteria["execution"]["minimum_samples_per_stage"]

        def worker():
            nonlocal launched
            local = []
            while True:
                with self.lock:
                    now = time.perf_counter()
                    if now - self.started >= self.criteria["execution"]["maximum_run_seconds"]:
                        raise TimeoutError("overall run budget exhausted")
                    if now - started >= seconds and launched >= minimum:
                        break
                    launched += 1
                row = self.operation(name)
                local.append(row)
                if row["peak_rss_mib"] > self.criteria["acceptance"]["maximum_worker_peak_rss_mib"]:
                    raise RuntimeError("worker memory budget exceeded")
            return local

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            for future in [pool.submit(worker) for _ in range(concurrency)]:
                rows.extend(future.result())
        summary = summarize(
            rows,
            time.perf_counter() - started,
            concurrency,
            limits,
            self.criteria["acceptance"],
            minimum,
        )
        summary["runs_per_second"] = (
            summary["batches_per_second"] * self.criteria["dataset"]["runs_per_batch"]
        )
        summary["cpu_seconds_per_evaluated_run"] = (
            summary["cpu_seconds_per_validated_batch"] / self.criteria["dataset"]["runs_per_batch"]
            if summary["validated_batches"]
            else None
        )
        print(json.dumps({"stage": name, **summary}), flush=True)
        return summary

    def failures(self) -> dict:
        def worker(kind):
            rows = []
            for _ in range(self.criteria["acceptance"]["failure_repetitions_per_type"]):
                rows.append(self.operation("failure-recovery", kind))
                recovery = self.operation("failure-recovery")
                recovery["ok"] = (
                    recovery["ok"]
                    and recovery["seconds"]
                    <= self.criteria["acceptance"]["failure_recovery_seconds"]
                )
                rows.append(recovery)
            return rows

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, kind) for kind in ("missing", "malformed")]
            rows = [row for future in futures for row in future.result()]
        return {
            "status": "PASS" if all(row["ok"] for row in rows) else "FAIL",
            "attempts": len(rows),
            "expected_rejections": sum(r["kind"] != "valid" for r in rows),
            "unexpected_errors": sum(not r["ok"] for r in rows),
            "rows": rows,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--criteria-commit", required=True)
    parser.add_argument("--package-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for name in ("repo", "python", "wheel", "output"):
        setattr(args, name, getattr(args, name).absolute())
    if sys.platform not in ("darwin", "linux"):
        parser.error("resource measurements support macOS and Linux only")
    args.env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}

    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(args.repo), *arguments])

    criteria_path = "Sentinel/benchmarks/offline-evaluation-v1.json"
    data = git("show", f"{args.criteria_commit}:{criteria_path}")
    criteria = json.loads(data)
    if criteria["workload_id"] != "offline-evaluation-v1" or criteria["schema_version"] != 1:
        parser.error("unsupported criteria version")
    subprocess.run(
        [
            "git",
            "-C",
            str(args.repo),
            "merge-base",
            "--is-ancestor",
            args.criteria_commit,
            "origin/main",
        ],
        check=True,
    )
    package_hash = digest(args.wheel.read_bytes())
    with zipfile.ZipFile(args.wheel) as wheel:
        for name in wheel.namelist():
            if (
                name.startswith("sentinel/")
                and not name.endswith("/")
                and wheel.read(name) != git("show", f"{args.package_commit}:Sentinel/src/{name}")
            ):
                parser.error(f"wheel does not match package commit: {name}")
    installed = json.loads(
        subprocess.check_output(
            [
                str(args.python),
                "-c",
                "import sys,json,platform,importlib.metadata as m; d=m.distribution('sentinel'); "
                "print(json.dumps({'python':platform.python_version(),"
                "'source':json.loads(d.read_text('direct_url.json') or '{}'),"
                "'dependencies':sorted((x.metadata['Name'],x.version) "
                "for x in m.distributions())}))",
            ],
            env=args.env,
        )
    )
    if not installed["python"].startswith(criteria["execution"]["python"] + "."):
        parser.error("installed Python does not match criteria")
    if installed["source"].get("archive_info", {}).get("hashes", {}).get("sha256") != package_hash:
        parser.error("runtime must be a noneditable installation of the supplied wheel")
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "criteria.json").write_bytes(data)
    cases = git("show", f"{args.package_commit}:Sentinel/{criteria['dataset']['cases_file']}")
    original = git("show", f"{args.package_commit}:Sentinel/{criteria['dataset']['runs_file']}")
    runs = []
    for repetition in range(criteria["dataset"]["repetitions"]):
        for line in original.splitlines():
            item = json.loads(line)
            item["run_id"] = f"capacity-{repetition:03d}-{item['run_id']}"
            runs.append(item)
    run_bytes = ("\n".join(json.dumps(r, sort_keys=True) for r in runs) + "\n").encode()
    if (
        len(runs) != criteria["dataset"]["runs_per_batch"]
        or len(cases.splitlines()) != criteria["dataset"]["case_count"]
    ):
        parser.error("source fixture counts do not match criteria")
    if len(cases) + len(run_bytes) > criteria["dataset"]["maximum_input_bytes"]:
        parser.error("generated input exceeds the criteria bound")
    (args.output / "cases.jsonl").write_bytes(cases)
    (args.output / "runs.jsonl").write_bytes(run_bytes)
    (args.output / "malformed.jsonl").write_text('{"invalid":\n')
    report = {
        "schema_version": 1,
        "started_at": datetime.now(UTC).isoformat(),
        "criteria_commit": args.criteria_commit,
        "criteria_sha256": digest(data),
        "package_commit": args.package_commit,
        "wheel_sha256": package_hash,
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "environment": {
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "available_memory": None,
            "power_mode": None,
            "competing_workload": "uncontrolled local desktop",
            **installed,
        },
        "status": "INCOMPLETE",
        "stages": {},
        "currency_cost_per_successful_operation": None,
    }
    runner = Runner(args, criteria, args.output)
    try:
        warmup = [
            runner.operation("warmup") for _ in range(criteria["execution"]["warmup_batches"])
        ]
        if not all(r["ok"] for r in warmup):
            raise RuntimeError("warmup correctness check failed")
        execution, acceptance = criteria["execution"], criteria["acceptance"]
        for name, concurrency, seconds in [
            ("expected", execution["expected_concurrency"], execution["stage_seconds"]),
            ("twice_expected", execution["twice_expected_concurrency"], execution["stage_seconds"]),
            ("soak", execution["twice_expected_concurrency"], execution["soak_seconds"]),
        ]:
            report["stages"][name] = runner.stage(name, concurrency, seconds, acceptance[name])
        capacity = []
        for concurrency in execution["saturation_concurrency"]:
            limits = {k: acceptance["twice_expected"][k] for k in ("p95_seconds", "p99_seconds")}
            stage = runner.stage(
                f"load-{concurrency}", concurrency, execution["stage_seconds"], limits
            )
            capacity.append(stage)
            if stage["status"] != "PASS":
                break
        report["increasing_load"] = capacity
        report["saturation_reached"] = any(s["status"] != "PASS" for s in capacity)
        report["failure_recovery"] = runner.failures()
        all_pass = all(s["status"] == "PASS" for s in [*report["stages"].values(), *capacity])
        report["status"] = (
            "PASS" if all_pass and report["failure_recovery"]["status"] == "PASS" else "FAIL"
        )
        if time.perf_counter() - runner.started > execution["maximum_run_seconds"]:
            report["status"], report["error"] = "INCOMPLETE", "overall duration budget exceeded"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report["error"] = str(exc)
    finally:
        runner.raw.close()
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["total_seconds"] = time.perf_counter() - runner.started
        report["operations_sha256"] = digest((args.output / "operations.jsonl").read_bytes())
        report["harness_peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (
            1024 * 1024 if sys.platform == "darwin" else 1024
        )
        (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({"status": report["status"], "report": str(args.output / "summary.json")}),
        flush=True,
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--measure-child":
        measure_child(sys.argv[2:])
    else:
        raise SystemExit(main())
