from __future__ import annotations

import argparse
import json
import statistics
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def post_json(base_url: str, path: str, payload: dict) -> tuple[int, float]:
    started = time.perf_counter()
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            response.read()
            status = response.status
    except Exception:
        status = 0
    return status, (time.perf_counter() - started) * 1000


def worker(base_url: str, index: int) -> list[tuple[int, float]]:
    start_status, start_ms = post_json(base_url, "/api/chat/start", {"scene_id": "delivery", "mode": "text"})
    if start_status != 200:
        return [(start_status, start_ms)]
    sid = f"synthetic-{index}"
    return [(start_status, start_ms)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight concurrent smoke/load test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=100)
    args = parser.parse_args()

    results: list[tuple[int, float]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(worker, args.base_url, i) for i in range(args.concurrency)]
        for future in as_completed(futures):
            results.extend(future.result())

    durations = [item[1] for item in results]
    ok = sum(1 for status, _ in results if 200 <= status < 300)
    total = len(results)
    report = {
        "total_requests": total,
        "success": ok,
        "success_rate": round(ok * 100 / max(1, total), 2),
        "avg_ms": round(statistics.mean(durations), 1) if durations else 0,
        "p95_ms": round(statistics.quantiles(durations, n=20)[18], 1) if len(durations) >= 20 else 0,
        "concurrency": args.concurrency,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
