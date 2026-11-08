import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import collect_news as cn  # noqa: E402
import collect_prices as cp  # noqa: E402

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>t</title>
<item><title>  VN-Index &amp;quot;giảm&amp;quot; mạnh  </title>
 <link>http://example.vn/a/1?utm_source=x&amp;id=7#frag</link>
 <description><![CDATA[<p>Khối ngoại <b>bán ròng</b> 1.200 tỷ</p>]]></description>
 <pubDate>Sun, 08 Nov 26 21:46:00 +0700</pubDate></item>
<item><title>Tin B</title><link>https://example.vn/b</link>
 <description>mô tả</description><pubDate>Sun, 08 Nov 2026 11:33:02 +0700</pubDate></item>
<item><title>Tin C (tz ngắn)</title><link>https://example.vn/c</link>
 <pubDate>Sun, 08 Nov 2026 20:14:00 +07</pubDate></item>
<item><title>Không có ngày</title><link>https://example.vn/d</link></item>
<item><title>Trùng A</title><link>https://example.vn/a/1?id=7&amp;utm_medium=y</link>
 <pubDate>Sun, 08 Nov 2026 21:46:00 +0700</pubDate></item>
</channel></rss>"""

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc)
FEED = {"source": "test", "name": "test_feed", "category": "market"}


class NewsTests(unittest.TestCase):
    def test_pubdate_formats(self):
        self.assertEqual(cn.parse_pubdate("Sun, 08 Nov 26 21:46:00 +0700").isoformat(), "2026-11-08T14:46:00+00:00")
        self.assertEqual(cn.parse_pubdate("Sun, 08 Nov 2026 11:33:02 +0700").isoformat(), "2026-11-08T04:33:02+00:00")
        self.assertEqual(cn.parse_pubdate("Sun, 08 Nov 2026 20:14:00 +07").isoformat(), "2026-11-08T13:14:00+00:00")
        self.assertIsNone(cn.parse_pubdate("not a date"))
        self.assertIsNone(cn.parse_pubdate(None))

    def test_canonical_url(self):
        self.assertEqual(cn.canonical_url("http://Example.vn/a/1?utm_source=x&id=7#frag"), "https://example.vn/a/1?id=7")

    def test_parse_feed(self):
        recs, skipped = cn.parse_feed(RSS.encode("utf-8"), FEED, NOW)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(recs), 4)
        first = recs[0]
        self.assertEqual(first["title"], 'VN-Index "giảm" mạnh')
        self.assertEqual(first["summary"], "Khối ngoại bán ròng 1.200 tỷ")
        self.assertEqual(first["published_at"], "2026-11-08T14:46:00Z")
        self.assertEqual(first["published_at_ict"], "2026-11-08T21:46:00+07:00")
        self.assertEqual(first["first_seen_at"], "2026-11-08T15:00:00Z")
        self.assertEqual(first["id"], recs[3]["id"])  # same canonical URL

    def test_end_to_end_dedup_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "feed.xml").write_text(RSS, encoding="utf-8")
            cfg = {"user_agent": "test", "feeds": [dict(FEED, url=(tmp / "feed.xml").as_uri())]}
            (tmp / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
            argv = ["--config", str(tmp / "cfg.json"), "--data-dir", str(tmp / "data")]
            self.assertEqual(cn.main(argv), 0)
            lines = (tmp / "data" / "news" / "2026-11.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 3)  # A, B, C (dup + undated dropped)
            self.assertEqual(cn.main(argv), 0)  # second run adds nothing
            lines2 = (tmp / "data" / "news" / "2026-11.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines2), 3)

    def test_all_feeds_failing_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg = {"user_agent": "t", "feeds": [dict(FEED, url=(tmp / "missing.xml").as_uri())]}
            (tmp / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
            self.assertEqual(cn.main(["--config", str(tmp / "cfg.json"), "--data-dir", str(tmp / "d"), "--dry-run"]), 1)


class PriceTests(unittest.TestCase):
    PAYLOAD = {"data": [
        {"tradingDate": "2026-11-05T00:00:00.000Z", "open": 90, "high": 92, "low": 89, "close": 91, "volume": 1000},
        {"tradingDate": "2026-11-06T00:00:00.000Z", "open": 91, "high": 93, "low": 90, "close": 92, "volume": 1200},
        {"tradingDate": "bad", "open": 1, "high": 1, "low": 1, "close": 1},
    ]}

    def test_parse_and_upsert(self):
        rows = cp.parse_rows(self.PAYLOAD)
        self.assertEqual([r["date"] for r in rows], ["2026-11-05", "2026-11-06"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "VCB.csv"
            self.assertEqual(cp.upsert_csv(path, rows), (2, 0))
            self.assertEqual(cp.upsert_csv(path, rows), (0, 0))  # idempotent
            rows[1]["close"] = 95
            self.assertEqual(cp.upsert_csv(path, rows), (0, 1))  # revision detected
            self.assertEqual(len(path.read_text().splitlines()), 3)

    def test_sanity(self):
        good = {"date": "d", "open": 10, "high": 12, "low": 9, "close": 11}
        bad = {"date": "d", "open": 10, "high": 8, "low": 9, "close": 11}
        self.assertEqual(cp.sanity_issues([good]), [])
        self.assertEqual(len(cp.sanity_issues([bad])), 1)


if __name__ == "__main__":
    unittest.main()
