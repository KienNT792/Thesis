# Data collection guide

Purpose: raw inputs for an LLM-derived news fear index and VN30 short-term direction forecasting
(thesis: *Does an LLM-Derived News Fear Index Improve Short-Term Direction Forecasting of VN30 Stocks?
An Empirical Study with Look-Ahead Bias Control*).

## What runs

| Workflow | Schedule (UTC / ICT) | Output |
|---|---|---|
| `collect-news.yml` | every 3 h at :17 (ICT 00:17, 03:17, ...) | `data/news/YYYY-MM.jsonl` |
| `collect-prices.yml` | Mon-Fri 09:30 / 16:30 | `data/prices/<TICKER>.csv` |
| `data-health.yml` | Mon 02:00 / 09:00 | `data/health/latest.md`; job fails (email) on problems |

Run logs: `data/_logs/news_runs.jsonl`, `data/_logs/prices_runs.jsonl`.

## News record schema (`data/news/*.jsonl`)

| Field | Meaning |
|---|---|
| `id` | first 16 hex of sha1(canonical URL); unique key |
| `source`, `feed`, `category` | outlet, RSS feed name, topic bucket from `config/news_feeds.json` |
| `title`, `summary` | cleaned text, summary capped at 600 chars (no full article text stored) |
| `url` | canonical URL (https, tracking params and fragment removed) |
| `published_at` | **source timestamp, UTC.** Use this for the information set |
| `published_at_ict` | same instant in ICT (+07:00); monthly files are split by this |
| `first_seen_at` | our collection time, UTC. Upper bound on availability only |

### Look-ahead rule (use in the thesis)

For a forecast of day *t+1* made after the close of day *t*, the allowed text is
`published_at <= t 15:00 ICT` (HOSE close), or a stricter cut-off you define and report.
Never filter on `first_seen_at`: collection can be hours later than publication, and articles
first seen late would be wrongly treated as "future". Articles are never edited after first capture,
so later updates by the outlet are not reflected (this is intentional, it freezes the information set).

## Price schema (`data/prices/<TICKER>.csv`)

`date,open,high,low,close,volume` (daily bars, date = trading day as returned by the provider,
`YYYY-MM-DD`). Includes `VNINDEX` and `VN30`.

## Known limitations (read before using the data)

1. **News history comes from backfills, not RSS.** RSS only exposes ~2-3 days. CafeF (market zone
   only) and Vietstock (4 channels) are backfilled from 2020-01 (see the two backfill sections
   below); VnExpress has RSS only, starting 2026-11-05. Coverage differs per source and category,
   so treat news volume as source-dependent, not as a uniform market signal.
2. **Price endpoint is unverified.** `config/prices.json` points to a TCBS public API that could not be
   tested from the authoring environment. Run *Collect prices* manually with `dry_run=true` first,
   then check units (VND vs thousand VND), adjusted vs unadjusted prices, and the date convention
   (provider timestamps are UTC midnight; the code keeps the date part).
3. **Survivorship / constituents.** `config/tickers.json` is a seed basket, **not** the official VN30
   list for any date. For an honest backtest use the official constituents for each semi-annual
   rebalance period and keep a history file (`config/vn30_history.csv`: `effective_from,ticker`).
4. **Terms of use.** Only titles, short summaries, URLs and timestamps are stored. Check each outlet's
   terms before publishing the dataset itself; cite and link rather than redistribute.
5. **Schedules can be delayed or paused.** GitHub may delay cron by several minutes and disables
   scheduled workflows in repositories with no activity for 60 days. The weekly health job and the
   data commits normally keep the repo active; if the repo goes quiet, re-enable from the Actions tab.
6. **Holidays.** The health job flags weekdays with zero articles for a source (only from the day the
   source first appears in the data) and prices more than 3 business days old; Tet and public
   holidays will raise expected alerts.
7. **Vietstock month-end gap (fixed and repaired 2026-11-09).** The archive endpoint treats `todate`
   as exclusive, so backfills up to 2026-11-08 dropped every article published on the last day of a
   month (58 weekdays, 2020-2026). `backfill_vietstock.py` now uses the first day of the next
   month, and a repair run (`month_end_only=true`, 2020-01..2026-10) added 2,517 articles. After the
   repair no weekday is empty for CafeF or Vietstock. Features or LLM scores computed before this
   date miss those articles and must be recomputed for month-end days.
8. **Provider price gaps (confirmed, not fixable from this provider).** Some tickers miss 3-10 trading
   days in 2020-2025 relative to the VNINDEX calendar (e.g. ACB 5, BCM 7, BSR 8, LPB 10, VIB 7,
   MCH 5). A full-range *Collect prices* dry run on 2026-11-09 (`start=2020-01-01`) returned
   `added=0, changed=0` for all 39 symbols, so VNDirect does not have these days. Treat them as
   missing (do not forward-fill silently), or fill from a second provider and document it.
   The health job only checks the recent window.
9. **OHLC anomalies in provider data.** Two bars fail the OHLC sanity check: VNINDEX 2020-09-29
   (close below low) and VNM 2025-05-13 (close below low). They are kept as delivered; exclude or
   correct them explicitly in modelling.

## Commands

```bash
python -m unittest discover -s tests -v
python scripts/collect_news.py --dry-run
python scripts/collect_prices.py --tickers VCB,FPT --dry-run
python scripts/collect_prices.py --start 2020-01-01      # historical backfill (or via workflow input)
python scripts/data_health.py
```

## VN30 constituents (added 2026-11)

- `config/tickers.json` -> `stocks`: current basket (effective 2026-08-03, 30 tickers) plus verified leavers since 2021.
- `config/vn30_baseline.csv` (basket on 2020-01-02) + `config/vn30_history.csv` (deltas, 2020-02-03 .. 2026-08-03) give the point-in-time VN30 universe. `scripts/vn30_universe.py --validate` checks 30 members after every date and equality with the independent full lists in `config/vn30_anchors.csv` (KBSV 2020-02 and 2022-01). `config/vn30_reviews.csv` logs every semi-annual/quarterly review with evidence level (A = official-result article, B = date inferred, C = inferred from chain/forecast) and source URLs.
- Residual risk: reviews 2020-04, 2020-10, 2024-01 and 2024-04 are evidence level C (no change inferred; chain and both anchors remain consistent). Confirm against HOSE announcements before final submission. Price files for the 11 former members added to `tickers.json` must be collected (Collect prices workflow, start=2020-01-01); ROS and EIB may return no data.

## Price source (updated 2026-11-08)

TCBS bars endpoint returned HTTP 404 and was replaced by VNDirect dchart (TradingView UDF). Verified from a browser: VCB/VN30/VNINDEX, 2020-01-02..2026-11-06 in a single call. Prices are in **thousand VND** and appear **adjusted** for dividends/splits (VCB first close 2020-01-02 = 38.881). Implications: use returns, not raw levels, for modelling; adjusted history can be revised retroactively, so the upsert may report `changed` rows after corporate actions. Not yet confirmed from GitHub runners: run `dry_run` first.

## News backfill (CafeF timeline)

RSS has no history, so 2020-2025 news is backfilled from `https://cafef.vn/timelinelist/18831/<page>.chn` (market news, ~15 items/page, newest first; page ~3000 reaches Jan 2020) by `scripts/backfill_cafef.py` (workflow `Backfill CafeF news`). Fields: title, url, sapo (short summary), ISO timestamp in ICT.
- Only CafeF "Thi truong chung khoan" zone; one source => source-selection bias. Other sources/zones can be added later.
- For backfilled rows `first_seen_at` is the backfill time, not an event time. Use `published_at` only.
- Only title + sapo are stored, not full text.
- Check CafeF terms of service before any redistribution; keep use academic, low-rate.

## News backfill (Vietstock channel listing)

Second source for 2020-2025: `POST https://vietstock.vn/StartPage/ChannelContentPage` (channelID, page, fromdate, todate), 10 items/page, processed month by month by `scripts/backfill_vietstock.py` (workflow `Backfill Vietstock news`). Channels: 144 (market, parent of 830 stocks / 579 analysis), 733 (company), 734 (finance), 761 (macro). Stored: title, url, truncated sapo, timestamp.
- Listing timestamps have no year; the year is taken from the URL and corrected at the Dec/Jan boundary.
- Per month the collector compares fetched item count with the site's reported total and prints `MISMATCH` if they differ.
- Overlap between channels is removed by URL hash; cross-source duplicates (same story on CafeF and Vietstock) are NOT removed here: deduplicate near-identical titles at the modelling stage.

## Session assignment and deduplication (added 2026-11-09)

`scripts/assign_session.py` implements the look-ahead rule: an article published on a trading day at or before 15:00 ICT belongs to that day's session; after 15:00 or on a non-trading day it belongs to the next trading day. A forecast made at the close of day t may use only articles with `session_date <= t`. Dedupe keeps the earliest article per normalised URL, then per (normalised title, ICT date).

Measured on 122,824 articles (run 2026-11-09): 122,557 remain after dedupe (0.22% removed); session counts with all categories reach >=20 articles on 100% of 1,709 trading days (market-category only: 99.9%); placeholder timestamps (00:00:00 ICT) are 0.008%. Median articles per session rose from 53 (2020) to 76 (2026). Run `python scripts/assign_session.py --report` to reproduce.

Price coverage of point-in-time VN30 members: 99.47% of member-days overall; the only gap is ROS (272 member-days to 2021-02-01, no data from the price provider), all other members are complete.

