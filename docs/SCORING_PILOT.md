# Scoring rubric and G5 pilot protocol

Purpose: validate that LLM scores (event label, sentiment, fear) are reliable *before* scoring all ~122k articles. Gate G5 passes when Krippendorff's alpha (ordinal) for `fear` and for `sentiment`, LLM vs human, has a bootstrap 95% CI lower bound >= 0.667 on a 300-article pilot. `event_label` is reported with nominal alpha (target >= 0.667 as well, but not blocking). A necessary precondition is that the two human raters reach the same bar against each other (the reliability ceiling, section 4 step 3).

## 0. Version history

| Version | Date | Status | Change |
|---|---|---|---|
| v1.0 | 2026-11-17 | Retired after round 1 | Initial rubric (scale definitions and 4 decision rules) |
| v1.1 | 2026-11-17 | Draft, to be tested on a fresh sample (seed 43) | Cue-based `fear` rule; ordered decision procedure for `event_label`. `sentiment` unchanged |

### Round 1 result (v1.0, seed 42, 300 articles, two human raters, Krippendorff alpha with bootstrap 95% CI)

| Scale | alpha | 95% CI | Exact agreement | Outcome |
|---|---|---|---|---|
| sentiment (ordinal) | 0.778 | 0.719-0.827 | 72.3% | PASS (frozen, unchanged in v1.1) |
| fear (ordinal) | 0.592 | 0.475-0.696 | 81.0% | FAIL |
| event_label (nominal) | 0.636 | 0.571-0.695 | 69.7% | Below target, not blocking |

Diagnosis: 45 of 57 `fear` disagreements were 0 versus >= 1 (is there any alarm signal at all?), with rater 1 scoring higher in 43 articles against 14 the other way. 207 of 300 articles were 0 for both raters, so alpha is very sensitive to the few articles that carry real fear. For `event_label` the main confusions were corporate_action vs market_commentary (14), corporate_earnings vs market_commentary (10), corporate_earnings vs corporate_action (10); lowest agreement on macro_policy (6/25) and public_health_disaster (1/8). The v1.1 changes target exactly these points. The seed-42 sample is now a **development set** (used for examples and adjudication); it is not reused for the retest.

## 1. Scale definitions (annotate from the text only)

**event_label** (closed set, choose the single dominant event; use the ordered procedure in section 1a):
`macro_policy` (national-level economic policy: GDP, budget, tax, FDI, public investment), `monetary_credit` (interest rates, credit room, liquidity, central bank), `regulation_legal` (laws, decrees, sanctions, inspections, listing status, court cases about market participants), `corporate_earnings` (profit, revenue, results, profit plans), `corporate_action` (issuance, M&A, dividends, insider or major-holder trades, appointments, company announcements), `market_commentary` (index or market-level wrap-ups, outlooks, technical views, analyst opinions on stocks or sectors, daily derivative or warrant reports), `fund_flow` (aggregate foreign, proprietary-desk, fund or ETF buying and selling), `global_geopolitics` (Fed, US, China, wars, global commodity prices), `public_health_disaster` (an epidemic or natural disaster is itself the event), `real_estate_bond_credit` (real estate, corporate bonds, bad debt), `other` (no market-relevant event).

**sentiment** (ordinal, valence of the information for equity investors in the entity or market the article concerns; unchanged from v1.0):
-2 strongly negative | -1 negative | 0 neutral or mixed | +1 positive | +2 strongly positive.

**fear** (ordinal, how much alarm, uncertainty or loss-aversion the **wording** conveys; distinct from negative sentiment):
- 0 none: routine, neutral or upbeat reporting. **No fear cue present.**
- 1 mild caution: hedged wording, "watch out", modest worry.
- 2 clear concern: explicit risks, sharp drops described as worrying, uncertainty about direction.
- 3 strong alarm: crash or sell-off language, margin-call or default risk, systemic worries.
- 4 panic or crisis: market-wide collapse, trading halts, contagion, emergency measures.

### 1a. event_label: ordered decision procedure (v1.1)

Apply the steps in order and stop at the first that matches. "Title event" means the event named **first** in the title.

1. **Not investment-relevant** (PR, promotions, product launches without market impact, general knowledge or explainer, politics or personnel not tied to markets, warnings unrelated to investing such as scam alerts) -> `other`.
2. **An epidemic or natural disaster is itself the event** -> `public_health_disaster`. A fire, accident or outage at one company is `corporate_action`, not a disaster.
3. **Regulator or court acts on a named company or person** (sanction, listing or trading status, prosecution, inspection) -> `regulation_legal`. National laws and decrees of general scope -> `regulation_legal`.
4. **National-level economic policy** (GDP targets, budget, tax rates, FDI, public investment) -> `macro_policy`. Interest rates, credit room, liquidity, central-bank appointments -> `monetary_credit`.
5. **Real estate, corporate bonds or bad debt is the subject** -> `real_estate_bond_credit`.
6. **Global factors** (Fed, US or China policy, wars, world commodity prices) -> `global_geopolitics`.
7. **Aggregate flows** (foreign investors, proprietary desks, funds or ETFs buying or selling as a group, index rebalancing) -> `fund_flow`. A single large holder buying or selling one stock is `corporate_action`.
8. **A single named company is the subject of the title**: `corporate_earnings` if the title event is profit, revenue, results or a profit plan; otherwise `corporate_action` (this includes dividends, issuance, M&A, listing, appointments, insider or major-holder trades). If both appear, the first-named event in the title decides.
9. **Market, index, sector or analyst view** (session wrap-ups, outlooks, technical analysis, stock or sector recommendations, daily derivative or warrant reports, lists of stocks) -> `market_commentary`.
10. Otherwise `other`.

### 1b. fear: cue-based rule (v1.1)

Fear above 0 requires a **cue**: a word or phrase in the title or summary that expresses caution, concern, risk, uncertainty, alarm or panic about **losses or risk for investors**. The rater must copy the cue verbatim into `notes` for every article scored >= 1. An article scored >= 1 with no cue in `notes` is invalid and is returned to the rater.

Initial cue lexicon (Vietnamese; indicative, extended after adjudication of round 1, additions need a new version number):

| Level | Cue examples |
|---|---|
| 1 | thận trọng, cẩn trọng, dè dặt, cần lưu ý, áp lực, rung lắc, biến động mạnh, bất định |
| 2 | lo ngại, lo lắng, rủi ro, nguy cơ, bi quan, đáng lo, bất ổn, suy thoái, điều chỉnh sâu |
| 3 | bán tháo, call margin, nguy cơ vỡ nợ, giảm sàn hàng loạt, sụp đổ (trong một phiên), lo ngại mang tính hệ thống |
| 4 | hoảng loạn, khủng hoảng, ngừng giao dịch, dừng giao dịch khẩn cấp, lan truyền, biện pháp khẩn cấp |

Decision rules (apply to all scales):
1. Rate what the text says, not what happened afterwards. Do not look up later prices or news.
2. **No cue, no fear.** A bad but routine number (for example a profit decline stated flatly) is negative sentiment with fear 0. Numbers alone are never a cue.
3. A negated or resolved cue does not count: "không đáng lo ngại", "đã đi qua vùng hoảng loạn" are scored on any remaining cue, otherwise 0.
4. The cue must concern investor loss or risk. Warnings about topics outside investing (scams, safety notices) are `other`, sentiment 0, fear 0.
5. Quoted cues describing the past or another party's state count only if the text endorses the concern; a cue describing a rival view ("some worry, but...") is scored at the lower level.
6. Fear can coexist with positive sentiment (for example a rebound that "may be a trap"): rate both scales independently.
7. When torn between two levels, choose the **lower** and write both in `notes`.
8. If the article has no investment-relevant content, use event_label `other`, sentiment 0, fear 0.
9. Use the title and summary only; do not open the URL.

## 2. LLM scoring prompt (template; store its SHA-256 as `prompt_hash`; v1.1 draft, freeze only after a PASS)

```
You are annotating Vietnamese financial news for a research study. Use ONLY the text below.
Do not use outside knowledge of later events. Return a single JSON object, no commentary.

Scales:
- event_label: apply these steps in order and stop at the first match:
  1 other if not investment-relevant; 2 public_health_disaster if an epidemic or natural disaster is itself the event;
  3 regulation_legal if a regulator or court acts on a named company or person, or national laws apply;
  4 macro_policy for national economic policy, monetary_credit for rates, credit and central bank;
  5 real_estate_bond_credit; 6 global_geopolitics; 7 fund_flow for aggregate flows only;
  8 corporate_earnings if the first-named event about one company is profit or revenue, else corporate_action;
  9 market_commentary for index, sector or analyst views; 10 other.
- sentiment: integer -2..2 (-2 strongly negative ... +2 strongly positive) for equity investors.
- fear: integer 0..4 (0 none, 1 mild caution, 2 clear concern, 3 strong alarm, 4 panic/crisis).
  Fear above 0 requires an explicit cue in the text (caution, concern, risk, uncertainty, alarm or panic
  about investor losses). If there is no such cue, fear is 0. Negated or resolved cues do not count.
- fear_cue: the exact words copied from the text that justify fear above 0, or "" if fear is 0.
Fear is separate from sentiment; rate each independently.

Title: {title}
Summary: {summary}

JSON: {"event_label": "...", "sentiment": 0, "fear": 0, "fear_cue": ""}
```

Never include the publication date, source name or URL in the prompt: they let the model recall the market outcome. Automatic validity checks: `fear_cue` must be a substring of the title or summary when `fear` > 0, and must be empty when `fear` = 0; violations are logged and re-scored once.

## 3. Score record schema (`fear_scores` file, one row per article and run)

`article_id, model_id, model_training_cutoff, prompt_hash, temperature (use 0), scored_at, event_label, sentiment, fear, fear_cue`. Keep every run; never overwrite. `model_training_cutoff` is the documented cutoff of the exact model version used; articles published after it form the contamination-free subset.

## 4. Pilot procedure

1. `python scripts/sample_pilot.py --n 300 --seed 43` (year x before/after-15:00 strata, equal allocation; outputs stay out of git). Seed 42 is the development set from round 1 and is not reused.
2. **Calibration (before the main pass):** both raters label 20 articles drawn outside the pilot sample and reconcile their reading of sections 1a and 1b without discussing pilot articles.
3. Two human raters label `pilot_annotation.csv` independently, blind to each other and to LLM output, in the shuffled order given. Import the `id` column as text (not number) to avoid spreadsheet corruption of long ids, and save as UTF-8 CSV. Report human-human alpha as the reliability ceiling. **Gate H:** human-human alpha CI lower bound >= 0.667 for `fear` and `sentiment`. If Gate H fails, revise the rubric (new version) and redraw a fresh sample; do not proceed to the LLM.
4. Adjudicate disagreements into a consensus label set (the adjudicator is not one of the two raters). Use only the development set for few-shot examples.
5. Score the same 300 articles with the LLM using the prompt above.
6. Run, for each of `fear` and `sentiment` with `--level ordinal`, and `event_label` with `--level nominal`:
   `python scripts/agreement.py --raters human1.csv human2.csv llm.csv --col fear --level ordinal`
   and the same with only `human1.csv llm.csv` and `human2.csv llm.csv`.
7. Decision: PASS if the CI lower bound >= 0.667 for `fear` and `sentiment`. BORDERLINE (point estimate passes, lower bound does not): add 100 articles from the weakest strata before deciding. FAIL: revise the rubric wording or add few-shot examples (re-draw a fresh sample for the retest, do not reuse the 300).
8. Freeze the rubric and `prompt_hash` after PASS; any later change requires a new pilot.
9. Fallback, to be declared in the limitations section if used: if `fear` still misses the bar because the 0 class dominates, report a 3-level collapse (0, 1-2, 3-4) or a binary indicator alongside the 5-level scale, and say so explicitly. This is not the default.

## 5. Caveats

- 300 articles give a wide alpha CI; the bootstrap CI is the honest report.
- Alpha is sensitive to skewed distributions (about 70% of articles are fear 0): report the label distribution next to alpha.
- The cue lexicon was written before adjudication and may bias scoring towards listed words; extend it only through a new version.
- The pilot validates reliability, not predictive value. Predictive value is tested in the forecasting block.
