# WCR Phase 1 Findings — Winner Crash / Asymmetric Predictability

> Status: first-pass empirical result  
> Dataset: survivorship-safe Shanghai/Shenzhen A-share snapshot, 2010-01-04 to 2026-09-24  
> Primary formation years: 2010–2024; next-year outcomes: 2011–2025  
> Primary comparable transitions: 44,672 stock-years

## 1. Primary universe

Primary universe `seasoned180`:
- stock was already listed before the formation year began;
- still listed at formation-year end;
- at least 180 trading observations in the formation year;
- annual return constructed by compounding BaoStock daily `pctChg`;
- each formation year sorted into D1–D10 by annual return;
- D1 = worst 10%, D10 = best 10%.

Next-year rank transition is computed only when the stock has a comparable eligible next-year observation.
Next-year delisting is tracked separately rather than silently deleting the stock.

Sensitivity universes:
- `all120`: includes newer listings with >=120 trading days;
- `nonst180`: seasoned primary universe with ST observations excluded.

All three universes produce the same qualitative finding.

## 2. Main result: the asymmetry is real in this sample

### Past D10 (previous-year best 10%)

Primary `seasoned180` results:
- next-year mean return: **+6.68%**
- next-year median return: **-6.18%**
- probability of next-year D1: **18.78%**
- probability of next-year D1/D2: **32.28%**
- probability of remaining next-year D10: **11.10%**
- probability next-year return <= -30%: **20.62%**
- probability next-year return <= -50%: **4.07%**
- next-year delisting rate: **0.34%**

Among all comparable stock-years:
- next-year D1 baseline: about **9.15%**
- next-year D1/D2 baseline: about **18.73%**
- <= -30% baseline: **13.74%**
- <= -50% baseline: **2.03%**

Therefore:
- D10 -> D1 lift ≈ **2.05x**
- D10 -> D1/D2 lift ≈ **1.72x**
- D10 <= -30% crash-risk lift ≈ **1.50x**
- D10 <= -50% crash-risk lift ≈ **2.00x**

This is a left-tail transition effect, not a statement that every prior winner loses money.

## 3. Downside is more predictable than upside

Using previous-year return as the only ranking signal:

- AUC for predicting next-year bottom decile from prior strength: **0.570**
- year-cluster bootstrap 95% interval: **[0.532, 0.614]**

Using previous-year weakness to predict next-year top decile:

- AUC: **0.496**
- year-cluster bootstrap 95% interval: **[0.461, 0.528]**

Difference:
- downside AUC - upside AUC ≈ **0.076**
- year-cluster bootstrap 95% interval: **[0.046, 0.107]**

Interpretation:

> Previous strength contains modest but repeatable information about future extreme downside.  
> Previous weakness contains essentially no information about future extreme upside.

This is much closer to “downside has structure, upside is hard to predict” than to a symmetric long-short reversal effect.

## 4. The effect is present every formation year

For all 15 complete formation years 2010–2024:
- D10 -> D1 probability is above 10% in **15/15 years**;
- D10 -> D1/D2 probability is above 20% in **15/15 years**.

Year-cluster mean D10 -> D1:
- **19.75%**
- bootstrap 95% interval **[16.38%, 23.52%]**

D1 -> D10:
- **9.50%**
- bootstrap 95% interval **[7.45%, 11.50%]**

D10 underperforms the full cross-section by an average of about **5.94 percentage points** in next-year return across years:
- bootstrap 95% interval about **[-11.23 pp, -0.61 pp]**.

## 5. Subperiod robustness

D10 -> D1:
- 2010–2014: **23.98%**
- 2015–2019: **15.17%**
- 2020–2024: **18.69%**

D10 -> D1/D2:
- 2010–2014: **36.88%**
- 2015–2019: **26.86%**
- 2020–2024: **33.51%**

The effect weakens/strengthens by regime but does not disappear.

## 6. Extreme-winner gradient

Among stocks with a comparable next-year observation, the more extreme the prior-year winner, the larger the future left-tail probability:

| Prior-year rank | P(next D1) | P(next D1/D2) | Next-year median | P(return <= -30%) |
|---|---:|---:|---:|---:|
| Top 20% | 15.6% | 28.6% | -3.8% | 18.1% |
| Top 10% | 18.8% | 32.4% | -6.2% | 20.7% |
| Top 5% | 22.8% | 36.5% | -9.2% | 23.1% |
| Top 3% | 25.5% | 38.6% | -11.5% | 25.4% |
| Top 1% | **31.0%** | **42.6%** | **-16.8%** | **32.7%** |

This is the strongest Phase-1 evidence for a Winner-Crash transition anomaly.

## 7. Important nuance: prior winners retain a right tail

D10 is not simply a “short everything” basket.

Next-year D10:
- top-decile continuation probability is still about **11.1%**, close to the 10% base rate;
- probability of next-year return >= +50% is roughly similar to the full market;
- extremely large continued winners still exist.

Thus the distribution is better described as:

> **fatter future left tail while preserving a meaningful right tail**

rather than deterministic mean reversion.

This is why the next research problem should be:
**within prior winners, distinguish Crash candidates from Continuation winners.**

## 8. 2025 -> 2026 YTD forward-only observation

Cutoff: 2026-09-24. This period is NOT used in model selection.

Among 2025 D10 stocks with 2026 YTD observations:
- n = 510
- mean 2026 YTD return: **+9.28%**
- median 2026 YTD return: **-12.23%**
- current YTD D1 share: **23.53%**
- current YTD D1/D2 share: **34.31%**
- current YTD D10 share: **19.22%**
- <= -30% YTD loss share: **29.80%**

This is a highly polarized forward observation: some prior winners continue spectacularly, while a large minority collapse into the left tail. It supports studying **Crash vs Continuation classification**, not shorting all winners.

## 9. What Phase 1 does NOT establish

Phase 1 does not yet prove the mechanism is caused by:
- short-sale constraints;
- retail speculation;
- lottery preference;
- industry rotation;
- valuation;
- turnover/crowding;
- RPC market regime.

Those are Phase-2 mechanism tests.

## 10. Next frozen research question

Within prior-year top winners, predict:

```
CRASH = next-year D1 / D2 or severe drawdown
vs
CONTINUATION = next-year D9 / D10
```

Candidate explanatory blocks:
1. extremeness of prior return;
2. turnover / volume / volatility;
3. market cap and liquidity;
4. industry-neutral excess return;
5. ST / price-limit / suspension behavior;
6. short-sale eligibility and financing/securities-lending variables where available;
7. RPC market state;
8. lottery-like characteristics.

Do not use 2026 forward outcomes to choose Phase-2 thresholds.

## Sources / provenance

Primary public snapshot:
https://github.com/noblechang/a-share-data

BaoStock adjustment methodology:
https://www.baostock.com/helpdocs/pdf/BaoStock%E5%A4%8D%E6%9D%83%E5%9B%A0%E5%AD%90%E7%AE%80%E4%BB%8B.pdf

BaoStock uses a return-based adjustment methodology designed to measure the return on initial capital while avoiding artificial ex-right/ex-dividend jumps. Phase 1 therefore compounds the daily `pctChg` field rather than raw close-to-close prices.
