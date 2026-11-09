#!/usr/bin/env python3
"""Weekly data-quality report -> data/health/latest.md. Exit 1 if a blocking problem is found.

Checks (last N days, default 14):
  * news: articles per source per day (ICT) - flags weekdays with zero articles for a source,
    but only from the day that source first appeared in the data (new sources are not "missing")
  * news: duplicate ids, feeds that failed in >50% of recent runs
  * prices: per-ticker last date and staleness in business days, tickers listed in config but
    without a file, OHLC sanity and missing trading days (vs the VNINDEX calendar) inside the window
Holidays (Tet etc.) can still raise expected alerts.
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
STALE_BUSINESS_DAYS = 3


def business_days_between(last: date, today: date) -> int:
    """Weekdays in (last, today]."""
    n, d = 0, last
    while d < today:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def ohlc_ok(r: dict) -> bool:
    try:
        o, h, lo, c = (float(r[k]) for k in ("open", "high", "low", "close"))
    except (TypeError, ValueError, KeyError):
        return False
    return min(o, h, lo, c) > 0 and h >= max(o, c, lo) - 1e-9 and lo <= min(o, c, h) + 1e-9


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
    first_seen_day: dict[str, str] = {}
    seen_ids: Counter = Counter()
    for path in sorted((data / "news").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            day = rec["published_at_ict"][:10]
            seen_ids[rec["id"]] += 1
            src = rec["source"]
            if day < first_seen_day.get(src, "9999"):
                first_seen_day[src] = day
            if day >= first_day.isoformat():
                per_day[src][day] += 1
    lines += ["## News: articles per source per day (ICT)", "", "| source | " + " | ".join(str(first_day + timedelta(days=i))[5:] for i in range(args.days + 1)) + " |", "|---|" + "---|" * (args.days + 1)]
    for source in sorted(per_day):
        cells = []
        start = first_seen_day[source]
        for i in range(args.days + 1):
            d = first_day + timedelta(days=i)
            n = per_day[source].get(d.isoformat(), 0)
            cells.append(str(n))
            if n == 0 and d.weekday() < 5 and d < today and d.isoformat() >= start:
                problems.append(f"news: {source} has 0 articles on weekday {d}")
        lines.append(f"| {source} | " + " | ".join(cells) + " |")
    if not per_day:
        problems.append("news: no articles found in window")
    dups = sum(1 for v in seen_ids.values() if v > 1)
    if dups:
        problems.append(f"news: {dups} duplicate article ids")

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
    tickers_cfg = ROOT / "config" / "tickers.json"
    if tickers_cfg.exists() and Path(args.data_dir) == ROOT / "data":
        cfg = json.loads(tickers_cfg.read_text(encoding="utf-8"))
        for t in cfg.get("indices", []) + cfg.get("stocks", []):
            if not (data / "prices" / f"{t}.csv").exists():
                problems.append(f"prices: {t} is in config/tickers.json but has no data file")

    calendar_days: set[str] = set()
    ref = data / "prices" / "VNINDEX.csv"
    if ref.exists():
        with ref.open(newline="", encoding="utf-8") as fh:
            calendar_days = {r["date"] for r in csv.DictReader(fh)}

    lines += ["", "## Prices: last available date per ticker", "", "| ticker | rows | last date | stale (business days) |", "|---|---|---|---|"]
    for path in sorted((data / "prices").glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            problems.append(f"prices: {path.stem} file is empty")
            continue
        dates = [r["date"] for r in rows]
        last = date.fromisoformat(max(dates))
        stale = business_days_between(last, today)
        lines.append(f"| {path.stem} | {len(dates)} | {last} | {stale} |")
        if stale > STALE_BUSINESS_DAYS:
            problems.append(f"prices: {path.stem} last bar is {stale} business days old")
        if len(dates) != len(set(dates)):
            problems.append(f"prices: {path.stem} has duplicate dates")
        recent = [r for r in rows if r["date"] >= first_day.isoformat()]
        bad = [r["date"] for r in recent if not ohlc_ok(r)]
        if bad:
            problems.append(f"prices: {path.stem} has inconsistent OHLC on {', '.join(bad[:3])}")
        if calendar_days:
            have = set(dates)
            gaps = [d for d in sorted(calendar_days) if first_day.isoformat() <= d < today.isoformat() and d >= dates[0] and d not in have]
            if gaps:
                problems.append(f"prices: {path.stem} is missing {len(gaps)} trading day(s) in window, e.g. {gaps[0]}")

    lines += ["", "## Problems", ""] + ([f"- {p}" for p in problems] or ["- none"])
    out = data / "health" / "latest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
