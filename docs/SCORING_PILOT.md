# Scoring rubric and G5 pilot protocol

Purpose: validate that LLM scores (event label, sentiment, fear) are reliable *before* scoring all ~122k articles. Gate G5 passes when Krippendorff's alpha (ordinal) for `fear` and for `sentiment`, LLM vs human, has a bootstrap 95% CI lower bound >= 0.667 on the 300-article pilot. `event_label` is reported with nominal alpha (target >= 0.667 as well, but not blocking).

## 1. Scale definitions (annotate from the text only)

**event_label** (closed set, choose the single dominant event):
`macro_policy`, `monetary_credit`, `regulation_legal`, `corporate_earnings`, `corporate_action` (issuance, M&A, insider or major-holder trades, dividends), `market_commentary` (session wrap-ups, outlooks, technical views), `fund_flow` (foreign/institutional/ETF flows), `global_geopolitics`, `public_health_disaster`, `real_estate_bond_credit`, `other` (no market-relevant event).

**sentiment** (ordinal, valence of the information for equity investors in the entity or market the article concerns):
-2 strongly negative | -1 negative | 0 neutral or mixed | +1 positive | +2 strongly positive.

**fear** (ordinal, how much alarm, uncertainty or loss-aversion the text conveys; distinct from negative sentiment):
- 0 none: routine, neutral or upbeat reporting.
- 1 mild caution: hedged wording, "watch out", modest worry.
- 2 clear concern: explicit risks, sharp drops described as worrying, uncertainty about direction.
- 3 strong alarm: crash/sell-off language, margin-call or default risk, systemic worries.
- 4 panic or crisis: market-wide collapse, trading halts, contagion, emergency measures.

Decision rules:
1. Rate what the text says, not what happened afterwards. Do not look up later prices or news.
2. A bad but routine number (for example a profit decline stated flatly) is negative sentiment with fear 0-1; fear needs alarm or uncertainty language.
3. Fear can coexist with positive sentiment (for example a rebound that "may be a trap"): rate both scales independently.
4. If the article has no investment-relevant content, use event_label `other`, sentiment 0, fear 0.
5. Use the title and summary only; do not open the URL.

## 2. LLM scoring prompt (template; store its SHA-256 as `prompt_hash`)

```
You are annotating Vietnamese financial news for a research study. Use ONLY the text below.
Do not use outside knowledge of later events. Return a single JSON object, no commentary.

Scales:
- event_label: one of [macro_policy, monetary_credit, regulation_legal, corporate_earnings,
  corporate_action, market_commentary, fund_flow, global_geopolitics, public_health_disaster,
  real_estate_bond_credit, other]
- sentiment: integer -2..2 (-2 strongly negative ... +2 strongly positive) for equity investors.
- fear: integer 0..4 (0 none, 1 mild caution, 2 clear concern, 3 strong alarm, 4 panic/crisis).
Fear is separate from sentiment; rate each independently.

Title: {title}
Summary: {summary}

JSON: {"event_label": "...", "sentiment": 0, "fear": 0}
```

Never include the publication date, source name or URL in the prompt: they let the model recall the market outcome.

## 3. Score record schema (`fear_scores` file, one row per article and run)

`article_id, model_id, model_training_cutoff, prompt_hash, temperature (use 0), scored_at, event_label, sentiment, fear`. Keep every run; never overwrite. `model_training_cutoff` is the documented cutoff of the exact model version used; articles published after it form the contamination-free subset.

## 4. Pilot procedure

1. `python scripts/sample_pilot.py --n 300 --seed 42` (year x before/after-15:00 strata, equal allocation; outputs stay out of git).
2. Two human raters label `pilot_annotation.csv` independently, blind to each other and to LLM output, in the shuffled order given. Report human-human alpha as the reliability ceiling.
3. Score the same 300 articles with the LLM using the prompt above.
4. Run, for each of `fear` and `sentiment` with `--level ordinal`, and `event_label` with `--level nominal`:
   `python scripts/agreement.py --raters human1.csv human2.csv llm.csv --col fear --level ordinal`
   and the same with only `human1.csv llm.csv` and `human2.csv llm.csv`.
5. Decision: PASS if the CI lower bound >= 0.667 for `fear` and `sentiment`. BORDERLINE (point estimate passes, lower bound does not): add 100 articles from the weakest strata before deciding. FAIL: revise the rubric wording or add few-shot examples (re-draw a fresh sample for the retest, do not reuse the 300).
6. Freeze the rubric and `prompt_hash` after PASS; any later change requires a new pilot.

## 5. Caveats

- 300 articles give a wide alpha CI; the bootstrap CI is the honest report.
- Alpha is sensitive to skewed distributions (most articles will have fear 0-1): report the label distribution next to alpha.
- The pilot validates reliability, not predictive value. Predictive value is tested in the forecasting block.
