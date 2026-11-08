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

1. **News depth starts at the first successful run.** RSS only exposes ~2-3 days. There is no
   2020-2025 news history in this repo; that requires a separate archive source and a decision on
   terms of use.
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
6. **Holidays.** The health job flags weekdays with zero articles for a source; Tet and public
   holidays will raise expected alerts.

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
- `config/vn30_history.csv`: **verified deltas only** (2021-08, 2026-02, 2026-05, 2026-08). Deltas for 2020-01..2021-07 and 2021-08..2026-01 (other reviews) are NOT yet collected; official full lists are published as images by HOSE.
- Consequence: for point-in-time universe before 2026 the history is incomplete. Until completed, treat pre-2026 backtests as using a survivorship-biased universe and report it as a limitation.
