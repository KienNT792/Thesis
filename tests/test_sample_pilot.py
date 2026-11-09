import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sample_pilot as sp  # noqa: E402


def _rows():
    rows = []
    for y in ("2020", "2021"):
        for hh in ("10:00:00", "16:30:00"):
            for i in range(40):
                rows.append({"id": f"{y}{hh}{i}", "published_at_ict": f"{y}-03-02T{hh}+07:00",
                             "title": "mot hai ba bon nam", "summary": "", "placeholder_ts": False,
                             "session_date": f"{y}-03-02"})
    return rows


def test_equal_allocation_and_determinism():
    a = sp.draw(_rows(), 20, seed=1)
    b = sp.draw(_rows(), 20, seed=1)
    assert [r["id"] for r in a] == [r["id"] for r in b]
    counts = {}
    for r in a:
        counts[sp.stratum(r)] = counts.get(sp.stratum(r), 0) + 1
    assert set(counts.values()) == {5}


def test_excludes_placeholders_and_short_titles():
    rows = _rows()
    rows[0]["placeholder_ts"] = True
    rows[1]["title"] = "ngan"
    assert len(sp.eligible(rows)) == len(rows) - 2


def test_allocation_capped_by_stratum_size():
    import random
    al = sp.allocate({"a": 3, "b": 100}, 20, random.Random(0))
    assert al["a"] == 3 and sum(al.values()) == 20
