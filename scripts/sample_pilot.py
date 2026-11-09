"""Draw the stratified pilot sample for gate G5 (LLM-vs-human agreement).

Strata: calendar year x timing (published before/after the 15:00 ICT cut-off).
Equal allocation per stratum (so 2020 and after-hours articles are represented),
remaining slots go to random strata. Deterministic for a given seed.
Excludes placeholder timestamps and very short titles.

Outputs (default data/pilot/):
    pilot_sample.csv      id, published_at_ict, session_date, source, category, title, summary, url
    pilot_annotation.csv  id + empty columns for each human rater to fill
Usage: python scripts/sample_pilot.py --n 300 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assign_session as asg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANNOT_COLS = ["event_label", "sentiment", "fear", "notes"]


def stratum(row: dict) -> tuple[str, str]:
    ts = row["published_at_ict"]
    return ts[:4], "after" if ts[11:19] > asg.CUTOFF else "before"


def eligible(rows: list[dict]) -> list[dict]:
    return [r for r in rows
            if not r["placeholder_ts"] and r["session_date"] and len(r["title"].split()) >= 4]


def allocate(sizes: dict, n: int, rng: random.Random) -> dict:
    """Equal allocation, capped by stratum size; leftovers go to random strata with room."""
    keys = sorted(sizes)
    alloc = {k: 0 for k in keys}
    base = n // len(keys)
    for k in keys:
        alloc[k] = min(base, sizes[k])
    left = n - sum(alloc.values())
    while left > 0:
        room = [k for k in keys if alloc[k] < sizes[k]]
        if not room:
            break
        alloc[rng.choice(room)] += 1
        left -= 1
    return alloc


def draw(rows: list[dict], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in eligible(rows):
        groups[stratum(r)].append(r)
    alloc = allocate({k: len(v) for k, v in groups.items()}, n, rng)
    out = []
    for k in sorted(groups):
        out.extend(rng.sample(sorted(groups[k], key=lambda r: r["id"]), alloc[k]))
    rng.shuffle(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "data" / "pilot"))
    a = ap.parse_args()
    cal = asg.load_calendar()
    rows = asg.process(asg.load_news(), cal)
    sample = draw(rows, a.n, a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cols = ["id", "published_at_ict", "session_date", "source", "category", "title", "summary", "url"]
    with open(out / "pilot_sample.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sample)
    with open(out / "pilot_annotation.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "summary"] + ANNOT_COLS)
        for r in sample:
            w.writerow([r["id"], r["title"], r["summary"], "", "", "", ""])
    counts: dict = defaultdict(int)
    for r in sample:
        counts[stratum(r)] += 1
    print(f"sampled {len(sample)} (seed {a.seed}); per stratum:")
    for k in sorted(counts):
        print(" ", k, counts[k])
    return 0


if __name__ == "__main__":
    sys.exit(main())
