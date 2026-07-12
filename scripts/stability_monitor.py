"""Monitor backend health over a fixed window and write JSONL evidence."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_health(url: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            ok = 200 <= response.status < 300
            return {
                "timestamp": utc_now(),
                "ok": ok,
                "status": response.status,
                "elapsed_ms": elapsed_ms,
                "body": body[:500],
            }
    except (TimeoutError, URLError, OSError) as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "timestamp": utc_now(),
            "ok": False,
            "status": None,
            "elapsed_ms": elapsed_ms,
            "error": exc.__class__.__name__,
            "message": str(exc)[:500],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record backend health checks.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--duration-days", type=float, default=7.0)
    parser.add_argument("--duration-seconds", type=float, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument(
        "--output",
        default="release/stability-monitor.jsonl",
        help="JSONL evidence file path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    duration_seconds = (
        args.duration_seconds
        if args.duration_seconds is not None
        else args.duration_days * 24 * 60 * 60
    )
    if duration_seconds <= 0:
        raise ValueError("duration must be positive")
    if args.interval_seconds <= 0:
        raise ValueError("interval must be positive")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    deadline = started + duration_seconds
    total = 0
    failures = 0
    max_elapsed_ms = 0.0

    with output.open("a", encoding="utf-8") as handle:
        while time.monotonic() < deadline:
            result = check_health(args.url, args.timeout_seconds)
            total += 1
            failures += 0 if result["ok"] else 1
            max_elapsed_ms = max(max_elapsed_ms, result["elapsed_ms"])
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            handle.flush()

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(args.interval_seconds, remaining))

    summary = {
        "url": args.url,
        "output": str(output),
        "checks": total,
        "failures": failures,
        "success_rate": round(((total - failures) / total) * 100, 4) if total else 0.0,
        "max_elapsed_ms": max_elapsed_ms,
        "started_at": utc_now(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
