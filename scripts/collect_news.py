#!/usr/bin/env python3
"""Collect Vietnamese financial-news metadata from public RSS feeds.

Design goals (thesis data quality):
  * Append-only JSONL, one file per month (by published month, ICT): data/news/YYYY-MM.jsonl
  * Idempotent: records are de-duplicated by sha1 of the canonical URL.
  * Look-ahead control: every record keeps `published_at` (source timestamp, UTC)
    AND `first_seen_at` (our collection time, UTC). Use `published_at` for the
    information set; `first_seen_at` is only an upper bound on availability.
  * Only title / short summary / URL are stored (no full article text).
  * Standard library only, so the workflow needs no dependency install.

Usage:
  python scripts/collect_news.py                # normal run
  python scripts/collect_news.py --dry-run      # fetch + parse, write nothing
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
ICT = timezone(timedelta(hours=7))
TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "src", "source", "zarsrc", "mc_cid", "mc_eid"}
SUMMARY_MAX = 600
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TZ_SHORT_RE = re.compile(r"([+-]\d{2})$")  # e.g. "+07" -> "+0700"


def clean_text(value: str | None, limit: int | None = None) -> str:
    if not value:
        return ""
    text = html.unescape(TAG_RE.sub(" ", value))
    text = text.replace("​", "").replace("­", "").replace("͏", "").replace("\xa0", " ")
    text = WS_RE.sub(" ", text).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    scheme = "https" if parts.scheme in ("http", "https") else parts.scheme
    return urlunsplit((scheme, parts.netloc.lower(), parts.path, urlencode(query), ""))


def parse_pubdate(value: str | None) -> datetime | None:
    """Parse RFC-822-ish dates, incl. 2-digit years ('08 Nov 26') and short tz ('+07')."""
    if not value:
        return None
    raw = TZ_SHORT_RE.sub(r"\g<1>00", value.strip())
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:  # all three sources are Vietnamese, assume ICT
        dt = dt.replace(tzinfo=ICT)
    return dt.astimezone(timezone.utc)


def fetch(url: str, user_agent: str, retries: int = 3, timeout: int = 30) -> bytes:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": user_agent, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def parse_feed(xml_bytes: bytes, feed: dict, now: datetime) -> tuple[list[dict], int]:
    """Return (records, skipped_without_date)."""
    root = ET.fromstring(xml_bytes)
    records: list[dict] = []
    skipped = 0
    for item in root.iter("item"):
        title = clean_text(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        published = parse_pubdate(item.findtext("pubDate"))
        if not title or not link:
            continue
        if published is None:
            skipped += 1
            continue
        url = canonical_url(link)
        records.append(
            {
                "id": hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
                "source": feed["source"],
                "feed": feed["name"],
                "category": feed["category"],
                "title": title,
                "summary": clean_text(item.findtext("description"), SUMMARY_MAX),
                "url": url,
                "published_at": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "published_at_ict": published.astimezone(ICT).strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "first_seen_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    return records, skipped


def load_known_ids(news_dir: Path) -> set[str]:
    ids: set[str] = set()
    for path in news_dir.glob("*.jsonl"):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line)["id"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    return ids


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "config" / "news_feeds.json"))
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    data_dir = Path(args.data_dir)
    news_dir = data_dir / "news"
    log_path = data_dir / "_logs" / "news_runs.jsonl"
    news_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    known = load_known_ids(news_dir)
    new_by_month: dict[str, list[dict]] = {}
    report: dict[str, dict] = {}
    seen_this_run: set[str] = set()

    for feed in cfg["feeds"]:
        entry = {"ok": False, "items": 0, "new": 0, "no_date": 0, "error": None}
        report[feed["name"]] = entry
        try:
            records, skipped = parse_feed(fetch(feed["url"], cfg["user_agent"]), feed, now)
            entry.update(ok=True, items=len(records), no_date=skipped)
            if not records:
                entry.update(ok=False, error="feed parsed but contained no usable items")
            for rec in records:
                if rec["id"] in known or rec["id"] in seen_this_run:
                    continue
                seen_this_run.add(rec["id"])
                month = rec["published_at_ict"][:7]
                new_by_month.setdefault(month, []).append(rec)
                entry["new"] += 1
        except Exception as exc:  # noqa: BLE001 - one broken feed must not stop the others
            entry["error"] = f"{type(exc).__name__}: {exc}"
            print(f"::warning::feed {feed['name']} failed: {entry['error']}", file=sys.stderr)

    total_new = sum(len(v) for v in new_by_month.values())
    ok_feeds = sum(1 for e in report.values() if e["ok"])
    print(f"feeds ok: {ok_feeds}/{len(report)}  new records: {total_new}")
    for name, e in report.items():
        print(f"  {name:34s} ok={e['ok']!s:5} items={e['items']:3d} new={e['new']:3d} {e['error'] or ''}")

    if not args.dry_run:
        for month, recs in new_by_month.items():
            recs.sort(key=lambda r: r["published_at"])
            with (news_dir / f"{month}.jsonl").open("a", encoding="utf-8") as fh:
                for rec in recs:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"run_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "new": total_new, "feeds": report}, ensure_ascii=False) + "\n")

    return 0 if ok_feeds else 1  # fail loudly only if every feed failed


if __name__ == "__main__":
    sys.exit(main())
