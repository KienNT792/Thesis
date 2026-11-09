"""Shared helpers for the analysis notebooks (read data/derived only)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DER = ROOT / "data" / "derived"
FIG = ROOT / "notebooks" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def load():
    news = pd.read_parquet(DER / "news_clean.parquet")
    px = pd.read_parquet(DER / "prices_long.parquet")
    tg = pd.read_parquet(DER / "targets.parquet")
    return news, px, tg


def savefig(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=110, bbox_inches="tight")


# Crude Vietnamese negative-sentiment keywords: a PROXY used only to exercise the
# pipeline before the LLM fear index exists. It is NOT the thesis fear score.
NEG = ["giảm", "lao dốc", "bán tháo", "sụt", "thua lỗ", "rủi ro", "lo ngại", "áp lực",
       "mất điểm", "giảm sàn", "đỏ lửa", "bất ổn", "khủng hoảng", "vỡ nợ", "thua"]
NEG_RE = re.compile("|".join(map(re.escape, NEG)), re.I)


def news_daily_features(news: pd.DataFrame) -> pd.DataFrame:
    """Per-session features using only articles with session_date (<= t) semantics."""
    n = news.dropna(subset=["session_date"]).copy()
    n["neg"] = n["title"].str.contains(NEG_RE).astype(int)
    n["after_hours"] = (n["published_at_ict"].str[11:19] > "15:00:00").astype(int)
    g = n.groupby("session_date")
    f = pd.DataFrame({"n_all": g.size(), "neg_rate": g["neg"].mean(), "after_hours": g["after_hours"].mean()})
    mk = n[n.category == "market"].groupby("session_date").size().rename("n_market")
    return f.join(mk).fillna(0)


def price_features(px: pd.DataFrame, index: str = "VN30") -> pd.DataFrame:
    s = px[px.ticker == index].set_index("date").sort_index()
    c, v = s["close"], s["volume"].astype(float)
    r = np.log(c).diff()
    f = pd.DataFrame(index=s.index)
    f["ret1"] = r
    f["ret5"] = np.log(c).diff(5)
    f["ret20"] = np.log(c).diff(20)
    f["vol20"] = r.rolling(20).std()
    f["vol5_over_20"] = r.rolling(5).std() / f["vol20"]
    f["volu_z"] = (np.log(v) - np.log(v).rolling(60).mean()) / np.log(v).rolling(60).std()
    f["dd60"] = c / c.rolling(60).max() - 1
    return f


def mcc(y, yhat):
    from sklearn.metrics import matthews_corrcoef
    return matthews_corrcoef(y, yhat) if len(set(yhat)) > 1 else 0.0
