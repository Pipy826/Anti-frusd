from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Anti-fraud service metrics report.")
    parser.add_argument("--db", default="backend/data/anti_fraud.db", help="SQLite database path")
    parser.add_argument("--window", type=int, default=3600, help="Report window in seconds")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"database not found: {db_path}")

    since = int(time.time()) - args.window
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        events = conn.execute(
            "SELECT COUNT(*) AS total, SUM(ok) AS ok, AVG(duration_ms) AS avg_duration FROM api_events WHERE created_at >= ?",
            (since,),
        ).fetchone()
        sessions = conn.execute("SELECT COUNT(*) AS total FROM sessions WHERE status = 'active'").fetchone()
        llm_failures = conn.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE role = 'assistant' AND degraded = 1 AND created_at >= ?",
            (since,),
        ).fetchone()
        high_risk = conn.execute(
            "SELECT COUNT(*) AS total FROM sessions WHERE risk_privacy >= 40 OR risk_property >= 40"
        ).fetchone()

    total = int(events["total"] or 0)
    ok = int(events["ok"] or 0)
    report = {
        "window_seconds": args.window,
        "api_success_rate": round(ok * 100 / max(1, total), 2),
        "average_response_ms": round(float(events["avg_duration"] or 0), 1),
        "active_sessions": int(sessions["total"] or 0),
        "llm_failure_count": int(llm_failures["total"] or 0),
        "high_risk_session_count": int(high_risk["total"] or 0),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("Anti-fraud service metrics")
    print(f"Window: {report['window_seconds']}s")
    print(f"API success rate: {report['api_success_rate']}%")
    print(f"Average response: {report['average_response_ms']} ms")
    print(f"Active sessions: {report['active_sessions']}")
    print(f"LLM failures: {report['llm_failure_count']}")
    print(f"High-risk sessions: {report['high_risk_session_count']}")


if __name__ == "__main__":
    main()
