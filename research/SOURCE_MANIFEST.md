# Source Manifest

This file records the main evidence classes used by the RPC research.

## Official / primary-source families

### Shanghai Stock Exchange (SSE)
Used for:
- historical A-share account statistics;
- annual statistical yearbooks;
- monthly investor/account statistics;
- Shanghai Composite monthly index/market overview.

Key official domains:
- https://www.sse.com.cn/
- https://star.sse.com.cn/

### China Securities Depository and Clearing Corporation (ChinaClear)
Used for:
- investor-count definitions;
- new-investor statistics after the 2015 multi-account regime change;
- annual statistical reports.

Key official domain:
- https://www.chinaclear.cn/

### CSRC
Used for:
- 2015 one-person-multiple-accounts policy/regime-break interpretation.

Key official domain:
- https://www.csrc.gov.cn/

## Reproducibility mirrors used during research calculations

These are convenient machine-readable mirrors, not substitutes for official provenance.

### Monthly investor dataset
https://github.com/1376524890/bigdata_fin/blob/master/real_data/03_%E5%B8%82%E5%9C%BA%E6%83%85%E7%BB%AA/investor_account_stats.csv

Coverage used in strict post-2015 calculations:
- 2015-04 to 2023-08

Fields used:
- 新增投资者-数量
- 期末投资者-总量
- 上证指数-收盘
- 上证指数-涨跌幅

### Margin financing dataset
https://github.com/1376524890/bigdata_fin/blob/master/real_data/03_%E5%B8%82%E5%9C%BA%E6%83%85%E7%BB%AA/margin_account.csv

Used for:
- financing balance;
- ~20 trading-day financing balance change.

### Shanghai Composite daily close mirror
https://github.com/sky910140/financial-agent-takehome/blob/main/data/market/sse_composite.csv

Used for:
- daily close;
- moving averages;
- daily forward return calculations;
- adverse excursion calculations.

## Data-quality rules

1. Official primary sources control definitions.
2. Mirrors are used for reproducible calculations only.
3. Pre/post-2015 account/investor values are not directly comparable in absolute terms.
4. Event counts must be de-duplicated by independent cycle.
5. Forward returns start after the information date; no future data may enter the signal.
6. 2024–2026 are frozen Forward/OOS-only and may not be used for parameter tuning.
7. 2008 is retained as a pre-sample external check because the strict 24-month warm-up is unavailable.
