import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import vn30_universe as u  # noqa: E402


def test_validate_clean():
    assert u.validate() == []


def test_always_30_members():
    for d in ["2020-01-02", "2020-02-03", "2021-08-02", "2023-08-07", "2025-08-04", "2026-08-03"]:
        assert len(u.members_on(d)) == 30


def test_effective_date_boundary():
    assert "PLX" not in u.members_on("2020-02-02")
    assert "PLX" in u.members_on("2020-02-03")


def test_current_basket_matches_tickers_json():
    import json
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "tickers.json").read_text(encoding="utf-8"))
    assert u.members_on("2026-11-01") == set(cfg["stocks"][:30])


def test_every_member_has_a_ticker_entry():
    import json
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "tickers.json").read_text(encoding="utf-8"))
    assert u.all_tickers() <= set(cfg["stocks"])
