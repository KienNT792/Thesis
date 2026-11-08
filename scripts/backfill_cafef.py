#!/usr/bin/env python3
"""Historical backfill of CafeF articles via its paginated timeline endpoint.

  https://cafef.vn/timelinelist/<zone_id>/<page>.chn   (~15 items/page, newest first)

Each item has title, url, ISO timestamp (ICT, in <span class="time" title=...>) and a sapo (summary).
Writes the same schema as collect_news.py into data/news/YYYY-MM.jsonl, deduplicated by URL id,
so it is safe to re-run/resume.  Look-ahead rule: published_at is the source timestamp; first_seen_at
is the backfill time and MUST NOT be used as an event time for backfilled rows (see docs/DATA.md).

  python scripts/backfill_cafef.py --until 2020-01-01 --zone 18831 --category market
  python scripts/backfill_cafef.py --start-page 2900 --max-pages 5 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_news import ICT, SUMMARY_MAX, canonical_url, clean_text, fetch, load_known_ids  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://cafef.vn"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


class TimelineParser(HTMLParser):
    """Extract (title, href, time, sapo) from div.tlitem blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict] = []
        self._cur: dict | None = None
        self._depth = 0
        self._in_h3 = False
        self._in_title_a = False
        self._in_sapo = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "div" and "tlitem" in cls.split():
            self._cur = {"title": "", "href": "", "time": "", "sapo": ""}
            self._depth = 1
            return
        if self._cur is None:
            return
        if tag == "div":
            self._depth += 1
        elif tag == "h3":
            self._in_h3 = True
        elif tag == "a" and self._in_h3 and not self._cur["href"]:
            self._cur["href"] = a.get("href") or ""
            self._in_title_a = True
        elif tag == "span" and "time" in cls.split() and not self._cur["time"]:
            self._cur["time"] = a.get("title") or ""
        elif tag == "p" and "sapo" in cls.split():
            self._in_sapo = True

    def handle_endtag(self, tag):
        if self._cur is None:
            return
        if tag == "a":
            self._in_title_a = False
        elif tag == "h3":
            self._in_h3 = False
        elif tag == "p":
            self._in_sapo = False
        elif tag == "div":
            self._depth -= 1
            if self._depth == 0:
                self.items.append(self._cur)
                self._cur = None

    def handle_data(self, data):
        if self._cur is None:
            return
        if self._in_title_a:
            self._cur["title"] += data
        elif self._in_sapo:
            self._cur["sapo"] += data


def parse_time(value: str) -> datetime | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=ICT)
        except ValueError:
            continue
    return None


def to_records(items: list[dict], source_feed: str, category: str, now: datetime) -> list[dict]:
    out = []
    for it in items:
        published = parse_time(it["time"])
        title = clean_text(it["title"])
        if published is None or not title or not it["href"]:
            continue
        url = canonical_url(it["href"] if it["href"].startswith("http") else BASE + it["href"])
        out.append(
            {
                "id": hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
                "source": "cafef",
                "feed": source_feed,
                "category": category,
                "title": title,
                "summary": clean_text(it["sapo"], SUMMARY_MAX),
                "url": url,
                "published_at": published.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "published_at_ict": published.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "first_seen_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    return out


def append_records(news_dir: Path, records: list[dict]) -> int:
    by_month: dict[str, list[dict]] = {}
    for r in records:
        by_month.setdefault(r["published_at_ict"][:7], []).append(r)
    news_dir.mkdir(parents=True, exist_ok=True)
    for month, rows in by_month.items():
        with (news_dir / f"{month}.jsonl").open("a", encoding="utf-8") as fh:
            for r in sorted(rows, key=lambda x: x["published_at"]):
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zone", default="18831")
    ap.add_argument("--category", default="market")
    ap.add_argument("--until", default="2020-01-01", help="stop once a whole page is older than this date")
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=10000)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--news-dir", default=str(ROOT / "data" / "news"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    until = date.fromisoformat(args.until)
    news_dir = Path(args.news_dir)
    known = load_known_ids(news_dir)
    feed_name = f"cafef_timeline_{args.zone}"
    now = datetime.now(timezone.utc)
    total_new = pages = fails = 0
    page = args.start_page
    buf: list[dict] = []
    while pages < args.max_pages:
        url = f"{BASE}/timelinelist/{args.zone}/{page}.chn"
        try:
            parser = TimelineParser()
            parser.feed(fetch(url, UA).decode("utf-8", "replace"))
            fails = 0
        except Exception as exc:  # noqa: BLE001
            fails += 1
            print(f"page {page}: {type(exc).__name__}: {exc}", file=sys.stderr)
            if fails >= 5:
                print("too many consecutive failures; stopping (resume with --start-page)", file=sys.stderr)
                break
            time.sleep(5)
            continue
        recs = to_records(parser.items, feed_name, args.category, now)
        if not recs:
            print(f"page {page}: no items; stopping")
            break
        new = [r for r in recs if r["id"] not in known]
        for r in new:
            known.add(r["id"])
        buf.extend(r for r in new if date.fromisoformat(r["published_at_ict"][:10]) >= until)
        total_new += len(new)
        pages += 1
        oldest = min(r["published_at_ict"][:10] for r in recs)
        if pages % 50 == 0 or pages == 1:
            print(f"page {page}: items={len(recs)} new={len(new)} oldest={oldest} total_new={total_new}")
        if len(buf) >= 1500 and not args.dry_run:
            append_records(news_dir, buf)
            buf = []
        if date.fromisoformat(oldest) < until and all(date.fromisoformat(r["published_at_ict"][:10]) < until for r in recs):
            break
        page += 1
        time.sleep(args.delay)
    if buf and not args.dry_run:
        append_records(news_dir, buf)
    print(f"done: pages={pages} new={total_new} last_page={page} dry_run={args.dry_run}")
    return 0 if pages else 1


if __name__ == "__main__":
    sys.exit(main())
