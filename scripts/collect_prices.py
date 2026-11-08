#!/usr/bin/env python3
"""Collect daily OHLCV for VN indices and VN30 stocks into data/prices/<TICKER>.csv.

Idempotent upsert keyed by date, so it is safe to re-run and to backfill:
  python scripts/collect_prices.py                      # last N days (config default_lookback_days)
  python scripts/collect_prices.py --start 2020-01-01   # historical backfill, chunked by year
  python scripts/collect_prices.py --tickers VCB,FPT --dry-run

Provider: VNDirect dchart (TradingView UDF), configured in config/prices.json. Verified 2026-11-08 from a\nbrowser: full history from 2020-01-02 in one call. Prices are in THOUSAND VND and appear dividend/split-adjusted;\nthey are stored as returned (see docs/DATA.md).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["date", "open", "high", "low", "close", "volume"]


def fetch_json(url: str, user_agent: str, retries: int = 3, timeout: int = 30) -> dict:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def to_ts(d: date, end_of_day: bool = False) -> int:
    dt = datetime(d.year, d.month, d.day, 23 if end_of_day else 0, 59 if end_of_day else 0, 59 if end_of_day else 0, tzinfo=timezone.utc)
    return int(dt.timestamp())


def parse_udf(payload: dict) -> list[dict]:
    """TradingView UDF format: {"t":[epoch...],"o":[],"h":[],"l":[],"c":[],"v":[],"s":"ok"}.
    "s":"no_data" means an empty window (not an error)."""
    if payload.get("s") != "ok":
        return []
    rows = []
    for i, ts in enumerate(payload.get("t") or []):
        try:
            rows.append(
                {
                    "date": datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "open": payload["o"][i],
                    "high": payload["h"][i],
                    "low": payload["l"][i],
                    "close": payload["c"][i],
                    "volume": payload["v"][i],
                }
            )
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return rows


def parse_rows(payload: dict) -> list[dict]:
    if "t" in payload and "c" in payload:
        return parse_udf(payload)
    rows = []
    for bar in payload.get("data") or []:
        trading_date = str(bar.get("tradingDate", ""))[:10]
        if len(trading_date) != 10:
            continue
        try:
            rows.append(
                {
                    "date": trading_date,
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar.get("volume", ""),
                }
            )
        except KeyError:
            continue
    return rows


def upsert_csv(path: Path, new_rows: list[dict]) -> tuple[int, int]:
    """Merge rows by date. Returns (rows_added, rows_changed)."""
    existing: dict[str, dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing[row["date"]] = row
    added = changed = 0
    for row in new_rows:
        norm = {k: str(row[k]) for k in FIELDS}
        old = existing.get(norm["date"])
        if old is None:
            added += 1
        elif {k: old[k] for k in FIELDS} != norm:
            changed += 1
        existing[norm["date"]] = norm
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return added, changed


def sanity_issues(rows: list[dict]) -> list[str]:
    issues = []
    for r in rows:
        try:
            o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
        except (TypeError, ValueError):
            issues.append(f"{r['date']}: non-numeric price")
            continue
        if min(o, h, l, c) <= 0 or h < max(o, c, l) - 1e-9 or l > min(o, c, h) + 1e-9:
            issues.append(f"{r['date']}: inconsistent OHLC {o},{h},{l},{c}")
    return issues


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "config" / "prices.json"))
    ap.add_argument("--tickers-config", default=str(ROOT / "config" / "tickers.json"))
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--start", help="YYYY-MM-DD; default = today - default_lookback_days")
    ap.add_argument("--end", help="YYYY-MM-DD; default = today (UTC)")
    ap.add_argument("--tickers", help="comma-separated override (applies to stocks and indices)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    tcfg = json.loads(Path(args.tickers_config).read_text(encoding="utf-8"))
    data_dir = Path(args.data_dir)
    end = date.fromisoformat(args.end) if args.end else datetime.now(timezone.utc).date()
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=int(cfg["default_lookback_days"]))

    jobs = [(t, cfg["kind_index"]) for t in tcfg["indices"]] + [(t, cfg["kind_stock"]) for t in tcfg["stocks"]]
    if args.tickers:
        wanted = {t.strip().upper() for t in args.tickers.split(",") if t.strip()}
        jobs = [j for j in jobs if j[0] in wanted]

    report: dict[str, dict] = {}
    for ticker, kind in jobs:
        entry = {"ok": False, "rows": 0, "added": 0, "changed": 0, "issues": 0, "error": None}
        report[ticker] = entry
        try:
            rows: list[dict] = []
            chunk_start = start
            while chunk_start <= end:
                chunk_end = min(chunk_start + timedelta(days=int(cfg["chunk_days"]) - 1), end)
                url = cfg["url_template"].format(ticker=ticker, kind=kind, from_ts=to_ts(chunk_start), to_ts=to_ts(chunk_end, True))
                rows.extend(parse_rows(fetch_json(url, cfg["user_agent"])))
                chunk_start = chunk_end + timedelta(days=1)
                time.sleep(float(cfg["request_delay_seconds"]))
            rows = [r for r in rows if start.isoformat() <= r["date"] <= end.isoformat()]
            if not rows:
                raise RuntimeError("provider returned no rows for the requested window")
            issues = sanity_issues(rows)
            entry.update(ok=True, rows=len(rows), issues=len(issues))
            if issues:
                print(f"::warning::{ticker}: {len(issues)} OHLC sanity issues, e.g. {issues[0]}", file=sys.stderr)
            if not args.dry_run:
                entry["added"], entry["changed"] = upsert_csv(data_dir / "prices" / f"{ticker}.csv", rows)
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"{type(exc).__name__}: {exc}"
            print(f"::warning::{ticker} failed: {entry['error']}", file=sys.stderr)

    ok = sum(1 for e in report.values() if e["ok"])
    print(f"tickers ok: {ok}/{len(report)}  window: {start}..{end}")
    for t, e in report.items():
        print(f"  {t:8s} ok={e['ok']!s:5} rows={e['rows']:5d} added={e['added']:5d} changed={e['changed']:3d} issues={e['issues']:3d} {e['error'] or ''}")

    if not args.dry_run:
        log_path = data_dir / "_logs" / "prices_runs.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "window": [str(start), str(end)], "tickers": report}, ensure_ascii=False) + "\n")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
