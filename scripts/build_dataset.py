"""Build analysis-ready Parquet files in data/derived/ from raw collectors' output.

Raw files (data/news, data/prices) are never modified. Outputs (not committed):
    news_clean.parquet   deduplicated news with session_date / placeholder flag
    prices_long.parquet  one row per ticker-day with in_vn30 (point-in-time)
    universe_pit.parquet date, ticker for every VN30 member-day
    targets.parquet      market-level 5-session forward labels with window bounds

Usage:  python scripts/build_dataset.py [--out data/derived] [--horizon 5]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assign_session as asg  # noqa: E402
import vn30_universe as uni  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DROP_THRESHOLD = -0.02  # fixed ex ante: "sharp drop" = 5-session return <= -2%


def build_prices(cal: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    for f in sorted((ROOT / "data" / "prices").glob("*.csv")):
        df = pd.read_csv(f, parse_dates=["date"])
        df["ticker"] = f.stem
        frames.append(df)
    px = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"])
    members = {d: uni.members_on(d) for d in cal}
    rows = [(pd.Timestamp(d), t) for d, ms in members.items() for t in sorted(ms)]
    pit = pd.DataFrame(rows, columns=["date", "ticker"])
    pit["in_vn30"] = True
    px = px.merge(pit, on=["date", "ticker"], how="left")
    px["in_vn30"] = px["in_vn30"].fillna(False).astype(bool)
    return px, pit[["date", "ticker"]]


def build_targets(px: pd.DataFrame, cal: list[str], horizon: int, index: str = "VN30") -> pd.DataFrame:
    s = px[px.ticker == index].set_index("date")["close"].sort_index()
    dates = s.index
    out = pd.DataFrame({"date": dates, "close": s.values})
    out["t_end"] = pd.Series(dates).shift(-horizon).values
    out["fwd_ret"] = s.shift(-horizon).values / s.values - 1
    out = out.dropna(subset=["t_end"]).copy()
    out["y_up"] = (out["fwd_ret"] > 0).astype(int)
    out["y_drop"] = (out["fwd_ret"] <= DROP_THRESHOLD).astype(int)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "derived"))
    ap.add_argument("--horizon", type=int, default=5)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    cal = asg.load_calendar()
    news = pd.DataFrame(asg.process(asg.load_news(), cal))
    news = news.drop(columns=["summary", "feed", "first_seen_at"], errors="ignore")
    news["published_at"] = pd.to_datetime(news["published_at"], utc=True)
    news["session_date"] = pd.to_datetime(news["session_date"])
    news.to_parquet(out / "news_clean.parquet", index=False)

    px, pit = build_prices(cal)
    px.to_parquet(out / "prices_long.parquet", index=False)
    pit.to_parquet(out / "universe_pit.parquet", index=False)
    tg = build_targets(px, cal, a.horizon)
    tg.to_parquet(out / "targets.parquet", index=False)
    print(f"news_clean {len(news):,} | prices_long {len(px):,} | universe_pit {len(pit):,} | targets {len(tg):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
