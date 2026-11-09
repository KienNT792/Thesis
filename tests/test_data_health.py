import csv
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import backfill_vietstock as bv  # noqa: E402
import data_health as dh  # noqa: E402


def write_news(root: Path, rows: list[tuple[str, str, str]]) -> None:
    (root / "news").mkdir(parents=True)
    by_month: dict[str, list[str]] = {}
    for i, (source, day, _) in enumerate(rows):
        rec = {"id": f"{source}{i}", "source": source, "published_at_ict": f"{day}T10:00:00+07:00"}
        by_month.setdefault(day[:7], []).append(json.dumps(rec))
    for month, lines in by_month.items():
        (root / "news" / f"{month}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_prices(root: Path, ticker: str, days: list[date], ohlc=(10, 11, 9, 10)) -> None:
    (root / "prices").mkdir(exist_ok=True)
    with (root / "prices" / f"{ticker}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for d in days:
            w.writerow([d.isoformat(), *ohlc, 1000])


def weekdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


class HealthTests(unittest.TestCase):
    def run_health(self, root: Path) -> str:
        dh.main(["--data-dir", str(root), "--days", "14"])
        return (root / "health" / "latest.md").read_text(encoding="utf-8")

    def test_new_source_not_flagged_before_first_article(self):
        today = datetime.now(timezone.utc).date()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = [("a", d.isoformat(), "") for d in weekdays(today - timedelta(days=20), today - timedelta(days=1))]
            new = [("b", d.isoformat(), "") for d in weekdays(today - timedelta(days=3), today - timedelta(days=1))]
            write_news(root, old + new)
            write_prices(root, "VNINDEX", weekdays(today - timedelta(days=20), today))
            report = self.run_health(root)
            self.assertNotIn("news: b has 0", report)

    def test_gap_after_first_article_is_flagged(self):
        today = datetime.now(timezone.utc).date()
        days = [d for d in weekdays(today - timedelta(days=12), today - timedelta(days=1))]
        gap = days[5]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_news(root, [("a", d.isoformat(), "") for d in days if d != gap])
            write_prices(root, "VNINDEX", weekdays(today - timedelta(days=20), today))
            self.assertIn(f"news: a has 0 articles on weekday {gap}", self.run_health(root))

    def test_stale_prices_use_business_days(self):
        self.assertEqual(dh.business_days_between(date(2026, 11, 6), date(2026, 11, 9)), 1)  # Fri -> Mon
        self.assertEqual(dh.business_days_between(date(2026, 11, 2), date(2026, 11, 9)), 5)

    def test_ohlc_and_missing_day(self):
        today = datetime.now(timezone.utc).date()
        cal = weekdays(today - timedelta(days=10), today - timedelta(days=1))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_news(root, [("a", d.isoformat(), "") for d in cal])
            write_prices(root, "VNINDEX", cal)
            write_prices(root, "XXX", [d for d in cal if d != cal[3]], ohlc=(10, 9, 11, 10))
            report = self.run_health(root)
            self.assertIn("XXX has inconsistent OHLC", report)
            self.assertIn("XXX is missing 1 trading day", report)


class MonthWindowTests(unittest.TestCase):
    def test_todate_is_first_of_next_month(self):
        self.assertEqual(bv.month_window(2026, 9), ("2026-09-01", "2026-10-01"))
        self.assertEqual(bv.month_window(2025, 12), ("2025-12-01", "2026-01-01"))
        self.assertEqual(bv.month_window(2024, 2), ("2024-02-01", "2024-03-01"))

    def test_month_end_only(self):
        self.assertEqual(bv.month_window(2026, 9, True), ("2026-09-30", "2026-10-01"))
        self.assertEqual(bv.month_window(2025, 12, True), ("2025-12-31", "2026-01-01"))


if __name__ == "__main__":
    unittest.main()
