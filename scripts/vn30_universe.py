"""Point-in-time VN30 universe.

members_on(date) reconstructs the constituent set from config/vn30_baseline.csv
plus the deltas in config/vn30_history.csv. validate() checks that the set has
30 members after every effective date and equals the independent anchor lists
in config/vn30_anchors.csv.

Usage:
    python scripts/vn30_universe.py --validate
    python scripts/vn30_universe.py --date 2022-03-01
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

CFG = Path(__file__).resolve().parent.parent / "config"


def _read(name: str) -> list[dict]:
    with open(CFG / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_baseline() -> tuple[str, set[str]]:
    rows = _read("vn30_baseline.csv")
    return rows[0]["effective_date"], {r["ticker"] for r in rows}


def load_events() -> dict[str, dict[str, set[str]]]:
    ev: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"add": set(), "remove": set()})
    for r in _read("vn30_history.csv"):
        ev[r["effective_date"]][r["action"]].add(r["ticker"])
    return dict(ev)


def members_on(date: str) -> set[str]:
    """Constituents in force on `date` (ISO string). Changes apply on effective_date."""
    base_date, members = load_baseline()
    if date < base_date:
        raise ValueError(f"date {date} precedes baseline {base_date}")
    members = set(members)
    for d, e in sorted(load_events().items()):
        if d > date:
            break
        missing = e["remove"] - members
        if missing:
            raise ValueError(f"{d}: removing non-members {sorted(missing)}")
        members = (members - e["remove"]) | e["add"]
    return members


def all_tickers() -> set[str]:
    base = load_baseline()[1]
    ev = load_events()
    return base | {t for e in ev.values() for t in e["add"] | e["remove"]}


def validate() -> list[str]:
    errs: list[str] = []
    base_date, base = load_baseline()
    if len(base) != 30:
        errs.append(f"baseline has {len(base)} members")
    for d in sorted(load_events()):
        try:
            n = len(members_on(d))
        except ValueError as exc:
            errs.append(str(exc))
            continue
        if n != 30:
            errs.append(f"{d}: {n} members")
    anchors: dict[str, set[str]] = defaultdict(set)
    for r in _read("vn30_anchors.csv"):
        anchors[r["as_of_date"]].add(r["ticker"])
    for d, exp in sorted(anchors.items()):
        got = members_on(d)
        if got != exp:
            errs.append(f"anchor {d}: extra={sorted(got - exp)} missing={sorted(exp - got)}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--date")
    a = ap.parse_args()
    if a.date:
        print(" ".join(sorted(members_on(a.date))))
    if a.validate or not a.date:
        errs = validate()
        for e in errs:
            print("FAIL", e)
        print("OK" if not errs else f"{len(errs)} error(s)")
        return 1 if errs else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
