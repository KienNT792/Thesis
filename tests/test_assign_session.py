import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import assign_session as a  # noqa: E402

# Fri 2020-01-03, Mon 2020-01-06 (weekend 04-05 not trading)
CAL = ["2020-01-02", "2020-01-03", "2020-01-06"]


def test_before_cutoff_same_day():
    assert a.assign_session("2020-01-02T09:00:00+07:00", CAL) == "2020-01-02"


def test_exactly_cutoff_same_day():
    assert a.assign_session("2020-01-02T15:00:00+07:00", CAL) == "2020-01-02"


def test_after_cutoff_next_day():
    assert a.assign_session("2020-01-02T15:00:01+07:00", CAL) == "2020-01-03"


def test_friday_after_close_goes_to_monday():
    assert a.assign_session("2020-01-03T16:30:00+07:00", CAL) == "2020-01-06"


def test_weekend_goes_to_monday():
    assert a.assign_session("2020-01-04T10:00:00+07:00", CAL) == "2020-01-06"


def test_beyond_calendar_is_none():
    assert a.assign_session("2020-01-06T16:00:00+07:00", CAL) is None


def test_placeholder():
    assert a.is_placeholder("2020-01-02T00:00:00+07:00")
    assert not a.is_placeholder("2020-01-02T00:00:01+07:00")


def _row(url, title, p):
    return {"url": url, "title": title, "published_at": p, "published_at_ict": p}


def test_dedupe_url_and_title_keeps_earliest():
    rows = [
        _row("https://www.a.vn/x/", "Tin A", "2020-01-02T10:00:00Z"),
        _row("https://a.vn/x", "Tin A khac", "2020-01-02T09:00:00Z"),
        _row("https://b.vn/y", "TIN  a khac!", "2020-01-02T11:00:00Z"),
        _row("https://b.vn/z", "Tin B", "2020-01-02T12:00:00Z"),
    ]
    out = a.dedupe(rows)
    assert [r["url"] for r in out] == ["https://a.vn/x", "https://b.vn/z"]
