import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import backfill_vietstock as bv  # noqa: E402

HTML = """
<div class="single_post post_type12 type20 mb20 channelContent"><div class="post_img"><a href="/2020/01/x-830-728300.htm"><img src="i.jpg"></a></div>
<div class="single_post_text"><div class="row"><div class="col-12"><div class="meta3"><a href="/chung-khoan/co-phieu.htm" title="Cổ phiếu">CỔ PHIẾU</a>
<a href="/2020/01/x-830-728300.htm" title="30/01 17:14">30/01 17:14</a></div></div></div>
<h4><a class="fontbold" href="/2020/01/x-830-728300.htm"> &#39;Cú đòn đau&#39; ngày đầu năm </a></h4>
<p class="post-p">VN-Index rớt mạnh 17 điểm...</p></div></div>
<div class="single_post post_type12 type20 mb20 channelContent"><div class="single_post_text"><div class="meta3"><a href="/2021/01/y-733-1.htm" title="31/12 23:50">31/12 23:50</a></div>
<h4><a href="/2021/01/y-733-1.htm">Bài cuối năm</a></h4><p class="post-p">Sapo.</p></div></div>
<script>var totalChannelRow = 164;</script>
"""


class VietstockTests(unittest.TestCase):
    def test_parse(self):
        p = bv.ChannelParser()
        p.feed(HTML)
        self.assertEqual(len(p.items), 2)
        self.assertEqual(bv.parse_total(HTML), 164)
        recs = bv.to_records(p.items, "vietstock_ch144_archive", "market", datetime(2026, 11, 9, tzinfo=timezone.utc))
        self.assertEqual(recs[0]["title"], "'Cú đòn đau' ngày đầu năm")
        self.assertEqual(recs[0]["published_at_ict"], "2020-01-30T17:14:00+07:00")
        self.assertEqual(recs[0]["published_at"], "2020-01-30T10:14:00Z")
        self.assertEqual(recs[0]["summary"], "VN-Index rớt mạnh 17 điểm...")
        # Dec-31 article filed under /2021/01/ belongs to 2020
        self.assertEqual(recs[1]["published_at_ict"], "2020-12-31T23:50:00+07:00")

    def test_months(self):
        self.assertEqual(list(bv.months("2020-11", "2021-02")), [(2020, 11), (2020, 12), (2021, 1), (2021, 2)])


if __name__ == "__main__":
    unittest.main()
