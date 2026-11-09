#!/usr/bin/env python3
"""Historical backfill of Vietstock articles via its channel listing endpoint.

  POST https://vietstock.vn/StartPage/ChannelContentPage   form: channelID, page, fromdate, todate (YYYY-MM-DD)
  -> HTML fragment with 10 items/page (div.channelContent): title, url, "DD/MM HH:MM" (no year), sapo (truncated)

Windows are processed month by month so paging stays bounded.  Same JSONL schema and URL-hash dedup as
collect_news.py; safe to resume (re-running only adds unseen URLs).  Timestamps carry no year: the year is taken
from the URL (/YYYY/MM/...) and corrected at year boundaries.

  python scripts/backfill_vietstock.py --from 2020-01 --until 2025-12 --channels 144,733,734,761
  python scripts/backfill_vietstock.py --from 2020-01 --until 2020-01 --channels 144 --dry-run
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_news import ICT, SUMMARY_MAX, canonical_url, clean_text, load_known_ids  # noqa: E402
from backfill_cafef import append_records  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://vietstock.vn"
ENDPOINT = BASE + "/StartPage/ChannelContentPage"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
CATEGORY = {"144": "market", "733": "company", "734": "finance", "761": "macro", "579": "analysis", "830": "stocks"}
URL_YM = re.compile(r"^/(20\d\d)/(\d\d)/")
TIME_RE = re.compile(r"^(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})$")


class ChannelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict] = []
        self.total: int | None = None
        self._cur: dict | None = None
        self._depth = 0
        self._in_h4 = False
        self._in_p = False
        self._in_meta = False
        self._meta_a = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "div" and "channelContent" in cls and "single_post" in cls:
            self._cur = {"title": "", "href": "", "time": "", "sapo": ""}
            self._depth = 1
            return
        if self._cur is None:
            return
        if tag == "div":
            self._depth += 1
            if "meta3" in cls:
                self._in_meta = True
        elif tag == "h4":
            self._in_h4 = True
        elif tag == "a" and self._in_h4 and not self._cur["href"]:
            self._cur["href"] = a.get("href") or ""
        elif tag == "a" and self._in_meta:
            ttl = (a.get("title") or "").strip()
            if TIME_RE.match(ttl):
                self._cur["time"] = ttl
        elif tag == "p" and "post-p" in cls:
            self._in_p = True

    def handle_endtag(self, tag):
        if self._cur is None:
            return
        if tag == "h4":
            self._in_h4 = False
        elif tag == "p":
            self._in_p = False
        elif tag == "div":
            self._depth -= 1
            self._in_meta = False
            if self._depth == 0:
                self.items.append(self._cur)
                self._cur = None

    def handle_data(self, data):
        if self._cur is None:
            return
        if self._in_h4:
            self._cur["title"] += data
        elif self._in_p:
            self._cur["sapo"] += data


def parse_total(html_text: str) -> int | None:
    m = re.search(r"totalChannelRow\s*=\s*(\d+)", html_text)
    return int(m.group(1)) if m else None


def resolve_time(href: str, stamp: str) -> datetime | None:
    """'DD/MM HH:MM' + URL year/month -> aware ICT datetime (handles Dec/Jan boundary)."""
    um, tm = URL_YM.match(href or ""), TIME_RE.match(stamp or "")
    if not um or not tm:
        return None
    uy, umon = int(um.group(1)), int(um.group(2))
    day, mon, hh, mm = (int(x) for x in tm.groups())
    year = uy
    if mon == 12 and umon == 1:
        year = uy - 1
    elif mon == 1 and umon == 12:
        year = uy + 1
    try:
        return datetime(year, mon, day, hh, mm, tzinfo=ICT)
    except ValueError:
        return None


def to_records(items: list[dict], feed: str, category: str, now: datetime) -> list[dict]:
    out = []
    for it in items:
        published = resolve_time(it["href"], it["time"])
        title = clean_text(it["title"])
        if published is None or not title:
            continue
        url = canonical_url(BASE + it["href"] if it["href"].startswith("/") else it["href"])
        out.append(
            {
                "id": hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
                "source": "vietstock",
                "feed": feed,
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


def post_page(channel: str, page: int, d0: str, d1: str, retries: int = 4, timeout: int = 40) -> str:
    body = urllib.parse.urlencode({"channelID": channel, "page": page, "fromdate": d0, "todate": d1}).encode()
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE,
        "Referer": BASE + "/",
        "Accept": "*/*",
    }
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(ENDPOINT, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            time.sleep(3 * attempt)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def months(start: str, end: str):
    y, m = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", default="2020-01", help="first month YYYY-MM")
    ap.add_argument("--until", default="2025-12", help="last month YYYY-MM")
    ap.add_argument("--channels", default="144,733,734,761")
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--news-dir", default=str(ROOT / "data" / "news"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    news_dir = Path(args.news_dir)
    known = load_known_ids(news_dir)
    now = datetime.now(timezone.utc)
    grand_new = pages = fails = 0
    for channel in [c.strip() for c in args.channels.split(",") if c.strip()]:
        cat = CATEGORY.get(channel, "other")
        feed = f"vietstock_ch{channel}_archive"
        for y, m in months(args.start, args.until):
            d0, d1 = f"{y}-{m:02d}-01", f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"
            page, month_new, expected, got = 1, 0, None, 0
            buf: list[dict] = []
            while True:
                try:
                    p = ChannelParser()
                    text = post_page(channel, page, d0, d1)
                    p.feed(text)
                    fails = 0
                except Exception as exc:  # noqa: BLE001
                    fails += 1
                    print(f"ch{channel} {d0} p{page}: {type(exc).__name__}: {exc}", file=sys.stderr)
                    if fails >= 5:
                        print("too many consecutive failures; stopping (resume with --from)", file=sys.stderr)
                        if buf and not args.dry_run:
                            append_records(news_dir, buf)
                        return 1
                    break
                if expected is None:
                    expected = parse_total(text)
                pages += 1
                recs = to_records(p.items, feed, cat, now)
                got += len(p.items)
                if not p.items:
                    break
                for r in recs:
                    if r["id"] not in known:
                        known.add(r["id"])
                        buf.append(r)
                        month_new += 1
                page += 1
                time.sleep(args.delay)
                if page > 400:
                    break
            if buf and not args.dry_run:
                append_records(news_dir, buf)
            grand_new += month_new
            flag = "" if expected is None or abs(got - expected) <= 2 else f"  MISMATCH expected={expected}"
            print(f"ch{channel} {y}-{m:02d}: items={got} new={month_new}{flag}")
    print(f"done: pages={pages} new={grand_new} dry_run={args.dry_run}")
    return 0 if pages else 1


if __name__ == "__main__":
    sys.exit(main())
