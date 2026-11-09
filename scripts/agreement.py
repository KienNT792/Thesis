"""Inter-rater agreement for gate G5: Krippendorff's alpha (nominal / ordinal) with bootstrap CI.

Input: CSV files, one per rater, with columns `id` and the rating column.
Usage:
    python scripts/agreement.py --raters human.csv llm.csv --col fear --level ordinal
Pure Python (no numpy). Missing ratings are blank cells.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from itertools import permutations


def _delta2(level: str, n_c: dict):
    """Return delta^2(c, k) function for the metric level."""
    if level == "nominal":
        return lambda c, k: 0.0 if c == k else 1.0
    if level == "ordinal":
        vals = sorted(n_c)

        def d(c, k):
            if c == k:
                return 0.0
            lo, hi = (c, k) if c < k else (k, c)
            s = sum(n_c[g] for g in vals if lo <= g <= hi) - (n_c[lo] + n_c[hi]) / 2
            return s * s
        return d
    if level == "interval":
        return lambda c, k: (c - k) ** 2
    raise ValueError(level)


def alpha(units: list[list], level: str = "ordinal") -> float:
    """units: list of lists of ratings per unit (None already removed)."""
    units = [u for u in units if len(u) >= 2]
    coinc: Counter = Counter()
    for u in units:
        m = len(u)
        for c, k in permutations(range(m), 2):
            coinc[(u[c], u[k])] += 1.0 / (m - 1)
    n_c: Counter = Counter()
    for (c, _), v in coinc.items():
        n_c[c] += v
    n = sum(n_c.values())
    if n <= 1:
        return float("nan")
    d = _delta2(level, n_c)
    do = sum(v * d(c, k) for (c, k), v in coinc.items())
    de = sum(n_c[c] * n_c[k] * d(c, k) for c in n_c for k in n_c if c != k)
    if de == 0:
        return 1.0
    return 1.0 - (n - 1) * do / de


def bootstrap_ci(units: list[list], level: str, reps: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        a = alpha([units[rng.randrange(len(units))] for _ in units], level)
        if a == a:
            vals.append(a)
    vals.sort()
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals)) - 1]


def load_units(paths: list[str], col: str, numeric: bool) -> list[list]:
    by_id: dict[str, list] = defaultdict(list)
    for p in paths:
        with open(p, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                v = (r.get(col) or "").strip()
                if v:
                    by_id[r["id"]].append(float(v) if numeric else v)
    return list(by_id.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raters", nargs="+", required=True)
    ap.add_argument("--col", required=True)
    ap.add_argument("--level", choices=["nominal", "ordinal", "interval"], default="ordinal")
    ap.add_argument("--threshold", type=float, default=0.667)
    a = ap.parse_args()
    units = load_units(a.raters, a.col, a.level != "nominal")
    if not units:
        print("no ratings found")
        return 2
    al = alpha(units, a.level)
    lo, hi = bootstrap_ci(units, a.level)
    verdict = "PASS" if lo >= a.threshold else ("BORDERLINE" if al >= a.threshold else "FAIL")
    print(f"{a.col} ({a.level}): alpha={al:.3f}  95% CI [{lo:.3f}, {hi:.3f}]  units={len(units)}  -> {verdict} (threshold {a.threshold})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
