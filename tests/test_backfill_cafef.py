import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import backfill_cafef as bf  # noqa: E402

HTML = """
<div role="article" class="tlitem box-category-item" data-id="1"><h3><a href="/a-b-20200131150136699.chn">Năm Bảy Bảy (NBB): lãi 354 tỷ</a></h3>
<div class="tlitem-flex"><a class="avatar" href="/x.chn"><img src="i.png"></a><div class="knswli-right">
<span class="time time-ago" title="2020-01-31T15:16:47">2020-01-31T15:16:47</span>
<p class="sapo box-category-sapo">Lợi nhuận sau thuế giảm 96%.</p></div></div></div>
<div role="article" class="tlitem box-category-item" data-id="2"><h3><a href="/c-d-18826110820552351.chn">Phạt thao túng</a></h3>
<div class="tlitem-flex"><div class="knswli-right"><span class="time" title="2026-11-08T21:46:00.000000">x</span>
<p class="sapo">Phạt 1,5 tỷ.</p></div></div></div>
"""


class BackfillTests(unittest.TestCase):
    def test_parse_and_records(self):
        p = bf.TimelineParser()
        p.feed(HTML)
        self.assertEqual(len(p.items), 2)
        recs = bf.to_records(p.items, "cafef_timeline_18831", "market", datetime(2026, 11, 9, tzinfo=timezone.utc))
        self.assertEqual(recs[0]["title"], "Năm Bảy Bảy (NBB): lãi 354 tỷ")
        self.assertEqual(recs[0]["published_at"], "2020-01-31T08:16:47Z")
        self.assertEqual(recs[0]["published_at_ict"], "2020-01-31T15:16:47+07:00")
        self.assertEqual(recs[0]["summary"], "Lợi nhuận sau thuế giảm 96%.")
        self.assertTrue(recs[1]["url"].startswith("https://cafef.vn/"))
        self.assertEqual(recs[1]["published_at_ict"][:10], "2026-11-08")


if __name__ == "__main__":
    unittest.main()
