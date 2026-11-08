#!/usr/bin/env python3
"""Weekly data-quality report -> data/health/latest.md. Exit 1 if a blocking problem is found.

Checks (last N days, default 14):
  * news: articles per source per day (ICT) - flags weekdays with zero articles for a source
  * news: feeds that failed in >50% of recent runs
  * prices: per-ticker last date and staleness
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args(argv)
    data = Path(args.data_dir)
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=args.days)
    problems: list[str] = []
    lines = [f"# Data health report", "", f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, window {first_day}..{today}", ""]

    # ---- news
    per_day: dict[str, Counter] = defaultdict(Counter)
    for path in sorted((data / "news").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            day = rec["published_at_ict"][:10]
            if day >= first_day.isoformat():
                per_day[rec["source"]][day] += 1
    lines += ["## News: articles per source per day (ICT)", "", "| source | " + " | ".join(str(first_day + timedelta(days=i))[5:] for i in range(args.days + 1)) + " |", "|---|" + "---|" * (args.days + 1)]
    for source in sorted(per_day):
        cells = []
        for i in range(args.days + 1):
            d = first_day + timedelta(days=i)
            n = per_day[source].get(d.isoformat(), 0)
            cells.append(str(n))
            if n == 0 and d.weekday() < 5 and d < today:
                problems.append(f"news: {source} has 0 articles on weekday {d}")
        lines.append(f"| {source} | " + " | ".join(cells) + " |")
    if not per_day:
        problems.append("news: no articles found in window")

    runs_path = data / "_logs" / "news_runs.jsonl"
    if runs_path.exists():
        fail, total = Counter(), Counter()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%dT")
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            run = json.loads(line)
            if run["run_at"] < cutoff:
                continue
            for name, e in run["feeds"].items():
                total[name] += 1
                fail[name] += 0 if e["ok"] else 1
        lines += ["", "## News: feed failure rate", "", "| feed | runs | failed |", "|---|---|---|"]
        for name in sorted(total):
            lines.append(f"| {name} | {total[name]} | {fail[name]} |")
            if total[name] >= 4 and fail[name] / total[name] > 0.5:
                problems.append(f"feed {name} failed in {fail[name]}/{total[name]} recent runs")

    # ---- prices
    lines += ["", "## Prices: last available date per ticker", "", "| ticker | rows | last date | stale (days) |", "|---|---|---|---|"]
    for path in sorted((data / "prices").glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as fh:
            dates = [r["date"] for r in csv.DictReader(fh)]
        if not dates:
            continue
        last = date.fromisoformat(max(dates))
        stale = (today - last).days
        lines.append(f"| {path.stem} | {len(dates)} | {last} | {stale} |")
        if stale > 5:
            problems.append(f"prices: {path.stem} last bar is {stale} days old")

    lines += ["", "## Problems", ""] + ([f"- {p}" for p in problems] or ["- none"])
    out = data / "health" / "latest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
