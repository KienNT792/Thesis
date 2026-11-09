"""Assign news to trading sessions and deduplicate (gates G1 / G4).

Rule (look-ahead safe, uses published_at only):
    session_date = the first HOSE trading session whose close (15:00 ICT) the
    article can inform *after* publication, i.e.
      - published on a trading day at or before 15:00 ICT -> that day's session
      - published after 15:00 ICT, or on a non-trading day  -> next trading day
    A forecast made at the close of day t may use only articles with
    session_date <= t.  Articles published exactly at 15:00:00 count for day t.

Deduplication: first by normalised URL, then by (normalised title, ICT date).
The earliest published_at is kept, so dedupe never pulls information forward.

Placeholder timestamps: published_at_ict at exactly 00:00:00 (date-only feeds)
are flagged; they cannot be placed inside a session reliably.

Usage:
    python scripts/assign_session.py --report
    python scripts/assign_session.py --out data/derived/news_sessions.csv
"""
from __future__ import annotations

import argparse
import bisect
import csv
import glob
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
CUTOFF = "15:00:00"
MIN_ARTICLES_PER_DAY = 20


def load_calendar(path: Path | None = None) -> list[str]:
    path = path or ROOT / "data" / "prices" / "VNINDEX.csv"
    with open(path, encoding="utf-8", newline="") as f:
        return sorted(r["date"] for r in csv.DictReader(f))


def split_ict(ts: str) -> tuple[str, str]:
    """'2020-01-20T09:58:50+07:00' -> ('2020-01-20', '09:58:50')."""
    return ts[:10], ts[11:19]


def assign_session(ts_ict: str, calendar: list[str]) -> str | None:
    """Return session_date, or None if beyond the last known trading day."""
    day, clock = split_ict(ts_ict)
    i = bisect.bisect_left(calendar, day)
    on_trading_day = i < len(calendar) and calendar[i] == day
    if on_trading_day and clock <= CUTOFF:
        return day
    j = i + 1 if on_trading_day else i
    return calendar[j] if j < len(calendar) else None


def is_placeholder(ts_ict: str) -> bool:
    return split_ict(ts_ict)[1] == "00:00:00"


def norm_url(url: str) -> str:
    p = urlsplit(url.strip())
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}"


def norm_title(title: str) -> str:
    t = unicodedata.normalize("NFKC", title).lower()
    return re.sub(r"[\W_]+", " ", t).strip()


def dedupe(rows: list[dict]) -> list[dict]:
    """Keep the earliest article per normalised URL, then per (title, ICT date)."""
    rows = sorted(rows, key=lambda r: r["published_at"])
    seen_url: set[str] = set()
    seen_title: set[tuple[str, str]] = set()
    out = []
    for r in rows:
        u = norm_url(r["url"])
        k = (norm_title(r["title"]), r["published_at_ict"][:10])
        if u in seen_url or k in seen_title:
            continue
        seen_url.add(u)
        seen_title.add(k)
        out.append(r)
    return out


def load_news(pattern: str | None = None) -> list[dict]:
    rows = []
    for f in sorted(glob.glob(pattern or str(ROOT / "data" / "news" / "*.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def process(rows: list[dict], calendar: list[str]) -> list[dict]:
    out = []
    for r in dedupe(rows):
        r = dict(r)
        r["placeholder_ts"] = is_placeholder(r["published_at_ict"])
        r["session_date"] = assign_session(r["published_at_ict"], calendar)
        out.append(r)
    return out


def report(raw: list[dict], clean: list[dict], calendar: list[str]) -> dict:
    per_session = Counter(r["session_date"] for r in clean if r["session_date"])
    per_session_mkt = Counter(r["session_date"] for r in clean
                              if r["session_date"] and r.get("category") == "market")
    days = [d for d in calendar]
    g1_all = sum(per_session[d] >= MIN_ARTICLES_PER_DAY for d in days) / len(days)
    g1_mkt = sum(per_session_mkt[d] >= MIN_ARTICLES_PER_DAY for d in days) / len(days)
    ph = sum(r["placeholder_ts"] for r in clean) / max(len(clean), 1)
    by_year: dict[str, list[int]] = defaultdict(list)
    for d in days:
        by_year[d[:4]].append(per_session[d])
    return {
        "raw": len(raw), "deduped": len(clean),
        "removed_pct": 1 - len(clean) / max(len(raw), 1),
        "trading_days": len(days),
        "G1_all_categories": g1_all, "G1_market_only": g1_mkt,
        "G4_placeholder_pct": ph,
        "median_per_session_by_year": {y: sorted(v)[len(v) // 2] for y, v in sorted(by_year.items())},
        "days_below_threshold": sorted(d for d in days if per_session[d] < MIN_ARTICLES_PER_DAY)[:10],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    cal = load_calendar()
    raw = load_news()
    clean = process(raw, cal)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        cols = ["id", "source", "category", "published_at", "published_at_ict",
                "session_date", "placeholder_ts", "title", "url"]
        with open(a.out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(clean)
    if a.report or not a.out:
        print(json.dumps(report(raw, clean, cal), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
