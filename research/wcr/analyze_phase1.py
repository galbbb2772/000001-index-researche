import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

DB = "ashare_pit.duckdb"
OUT = Path("wcr_phase1")
OUT.mkdir(exist_ok=True)

con = duckdb.connect(DB, read_only=True)

# Annual return is compounded from BaoStock daily pctChg rather than inferred
# from today's survivor list or raw year-end price ratios. The PIT database
# contains delisted securities and historical status fields.
annual = con.execute(r"""
WITH a AS (
  SELECT
    b.security_id,
    EXTRACT(year FROM b.trade_date)::INTEGER AS year,
    COUNT(*) FILTER (WHERE b.tradestatus = 1) AS n_trade_days,
    SUM(CASE WHEN b.isST = 1 AND b.tradestatus = 1 THEN 1 ELSE 0 END) AS st_days,
    EXP(SUM(
      CASE
        WHEN b.tradestatus = 1
         AND b.pctChg IS NOT NULL
         AND b.pctChg > -99.99
        THEN LN(1.0 + b.pctChg / 100.0)
        ELSE 0
      END
    )) - 1.0 AS annual_ret,
    AVG(CASE WHEN b.tradestatus = 1 THEN b.turn END) AS avg_turn,
    SUM(CASE WHEN b.tradestatus = 1 THEN b.amount ELSE 0 END) AS annual_amount,
    MIN(CASE WHEN b.tradestatus = 1 THEN b.trade_date END) AS first_trade,
    MAX(CASE WHEN b.tradestatus = 1 THEN b.trade_date END) AS last_trade
  FROM bars b
  WHERE EXTRACT(year FROM b.trade_date) BETWEEN 2010 AND 2026
  GROUP BY 1, 2
)
SELECT
  a.*,
  s.exchange,
  s.symbol,
  s.name,
  s.list_date,
  s.delist_date
FROM a
JOIN security_master s USING (security_id)
ORDER BY year, security_id
""").df()

annual["year"] = annual["year"].astype(int)
annual["list_date"] = pd.to_datetime(annual["list_date"])
annual["delist_date"] = pd.to_datetime(annual["delist_date"])
annual["st_share"] = annual["st_days"] / annual["n_trade_days"].replace(0, np.nan)


def year_start(y):
    return pd.Timestamp(year=int(y), month=1, day=1)


def year_end(y):
    return pd.Timestamp(year=int(y), month=12, day=31)


annual["seasoned"] = annual.apply(
    lambda r: pd.notna(r.list_date) and r.list_date < year_start(r.year), axis=1
)
annual["active_year_start"] = annual.apply(
    lambda r: (
        pd.notna(r.list_date)
        and r.list_date < year_start(r.year)
        and (pd.isna(r.delist_date) or r.delist_date >= year_start(r.year))
    ),
    axis=1,
)
annual["active_year_end"] = annual.apply(
    lambda r: pd.isna(r.delist_date) or r.delist_date > year_end(r.year), axis=1
)
annual["delisted_in_year"] = annual.apply(
    lambda r: (
        pd.notna(r.delist_date)
        and year_start(r.year) <= r.delist_date <= year_end(r.year)
    ),
    axis=1,
)


def add_deciles(df, return_col="annual_ret", out_col="decile"):
    df = df.copy()

    def dec(s):
        s = s.dropna()
        if len(s) < 20:
            return pd.Series(np.nan, index=s.index)
        rank = s.rank(method="first")
        return pd.qcut(rank, 10, labels=False) + 1

    ranked = df.groupby("year", group_keys=False)[return_col].apply(dec)
    df[out_col] = ranked.reindex(df.index).astype("Int64")
    return df


# Formation universes require the stock to still exist at formation year-end.
# This is correct for a rule formed at the end of that year.
formation_universes = {
    "seasoned180": annual[
        annual.seasoned & annual.active_year_end & (annual.n_trade_days >= 180)
    ].copy(),
    "all120": annual[
        annual.active_year_end & (annual.n_trade_days >= 120)
    ].copy(),
    "nonst180": annual[
        annual.seasoned
        & annual.active_year_end
        & (annual.n_trade_days >= 180)
        & (annual.st_share == 0)
    ].copy(),
}

# IMPORTANT: outcome universe must NOT require survival to next year-end.
# Otherwise a prior winner that crashes and delists in the following year
# disappears from the transition matrix, recreating survivorship bias.
#
# For ordinary stocks require >=60 observed trading days. A stock that delists
# during the year is retained even with fewer days; delisting is separately
# flagged because final observed market return may not equal liquidation value.
outcome_base = annual[
    annual.active_year_start
    & ((annual.n_trade_days >= 60) | annual.delisted_in_year)
    & annual.annual_ret.notna()
].copy()
outcome_base = add_deciles(outcome_base)


def auc_rank(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    ok = np.isfinite(score)
    y = y[ok]
    score = score[ok]
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    ranks = pd.Series(score).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def bootstrap_year_metric(year_df, col, seed=20261115, B=10000):
    vals = year_df[col].dropna().to_numpy(float)
    if len(vals) < 2:
        return {
            "mean": float(np.nanmean(vals)) if len(vals) else None,
            "ci95": [None, None],
            "n_years": int(len(vals)),
        }
    rng = np.random.default_rng(seed)
    means = np.empty(B)
    for i in range(B):
        means[i] = rng.choice(vals, size=len(vals), replace=True).mean()
    return {
        "mean": float(vals.mean()),
        "ci95": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))],
        "n_years": int(len(vals)),
    }


def make_transition(uname, formation):
    formation = add_deciles(formation)
    f = formation[formation.year.between(2010, 2024)].copy()
    f["formation_year"] = f["year"]

    nxt = outcome_base[outcome_base.year.between(2011, 2025)][
        [
            "security_id",
            "year",
            "annual_ret",
            "decile",
            "n_trade_days",
            "delisted_in_year",
            "last_trade",
        ]
    ].copy()
    nxt["formation_year"] = nxt["year"] - 1
    nxt = nxt.rename(
        columns={
            "annual_ret": "next_ret",
            "decile": "next_decile",
            "n_trade_days": "next_n_trade_days",
            "delisted_in_year": "delist_next",
            "last_trade": "next_last_trade",
        }
    ).drop(columns=["year"])

    tr = f.merge(nxt, on=["security_id", "formation_year"], how="left")
    tr["next_eligible"] = tr["next_decile"].notna()
    tr["missing_next"] = ~tr["next_eligible"]
    tr["delist_next"] = tr["delist_next"].fillna(False).astype(bool)

    obs = tr[tr.next_eligible].copy()
    obs["decile"] = obs["decile"].astype(int)
    obs["next_decile"] = obs["next_decile"].astype(int)

    # Central hypothesis: last year's D10 migrates to next year's D1.
    # Secondary left-tail definitions are kept explicit rather than silently
    # treating every delisting as a crash (some delistings are mergers).
    obs["left_tail_D1"] = obs["next_decile"] == 1
    obs["left_tail_30"] = obs["next_ret"] <= -0.30
    obs["left_tail_50"] = obs["next_ret"] <= -0.50
    obs["negative_delist"] = obs["delist_next"] & (obs["next_ret"] < 0)
    obs["crash_transition"] = obs["left_tail_D1"] | obs["negative_delist"]

    rows = []
    for d in range(1, 11):
        full = tr[tr.decile == d]
        x = obs[obs.decile == d]
        rows.append(
            {
                "formation_decile": d,
                "formation_n": len(full),
                "next_eligible_n": len(x),
                "next_coverage_rate": len(x) / len(full) if len(full) else np.nan,
                "missing_next_rate": full.missing_next.mean() if len(full) else np.nan,
                "delist_next_rate": full.delist_next.mean() if len(full) else np.nan,
                "next_mean_ret": x.next_ret.mean(),
                "next_median_ret": x.next_ret.median(),
                "p_next_D1": x.left_tail_D1.mean(),
                "p_next_D1_D2": (x.next_decile <= 2).mean(),
                "p_next_D10": (x.next_decile == 10).mean(),
                "p_crash_30": x.left_tail_30.mean(),
                "p_crash_50": x.left_tail_50.mean(),
                "p_negative_delist": x.negative_delist.mean(),
                "p_crash_transition": x.crash_transition.mean(),
            }
        )
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / f"{uname}_decile_summary.csv", index=False)

    trans = (
        pd.crosstab(obs.decile, obs.next_decile, normalize="index")
        .reindex(index=range(1, 11), columns=range(1, 11), fill_value=0)
    )
    trans.index.name = "formation_decile"
    trans.to_csv(OUT / f"{uname}_transition_matrix.csv")

    # An alternative state table keeps delisting visible as its own outcome
    # instead of hiding it inside a decile.
    obs["next_state"] = np.where(
        obs.delist_next, "DELIST", "D" + obs.next_decile.astype(str)
    )
    state_order = [f"D{i}" for i in range(1, 11)] + ["DELIST"]
    tstate = (
        pd.crosstab(obs.decile, obs.next_state, normalize="index")
        .reindex(index=range(1, 11), columns=state_order, fill_value=0)
    )
    tstate.index.name = "formation_decile"
    tstate.to_csv(OUT / f"{uname}_transition_with_delist.csv")

    yr = []
    for y, g in obs.groupby("formation_year"):
        d10 = g[g.decile == 10]
        d1 = g[g.decile == 1]
        all_form = tr[tr.formation_year == y]
        full10 = all_form[all_form.decile == 10]
        yr.append(
            {
                "formation_year": int(y),
                "n": len(g),
                "d10_n": len(d10),
                "d10_next_mean": d10.next_ret.mean(),
                "d10_next_median": d10.next_ret.median(),
                "d10_to_D1": d10.left_tail_D1.mean() if len(d10) else np.nan,
                "d10_to_D1_D2": (d10.next_decile <= 2).mean() if len(d10) else np.nan,
                "d10_to_D10": (d10.next_decile == 10).mean() if len(d10) else np.nan,
                "d10_crash30": d10.left_tail_30.mean() if len(d10) else np.nan,
                "d10_crash_transition": d10.crash_transition.mean() if len(d10) else np.nan,
                "d10_delist_next": full10.delist_next.mean() if len(full10) else np.nan,
                "d1_n": len(d1),
                "d1_to_D10": (d1.next_decile == 10).mean() if len(d1) else np.nan,
                "d1_next_mean": d1.next_ret.mean(),
                "all_next_mean": g.next_ret.mean(),
                "d10_minus_all": d10.next_ret.mean() - g.next_ret.mean()
                if len(d10)
                else np.nan,
                "d1_minus_all": d1.next_ret.mean() - g.next_ret.mean()
                if len(d1)
                else np.nan,
                "spearman_past_next": g[["annual_ret", "next_ret"]]
                .corr(method="spearman")
                .iloc[0, 1],
                "auc_bottom_from_strength": auc_rank(
                    (g.next_decile == 1).astype(int), g.annual_ret
                ),
                "auc_top_from_weakness": auc_rank(
                    (g.next_decile == 10).astype(int), -g.annual_ret
                ),
            }
        )
    yr = pd.DataFrame(yr)
    yr.to_csv(OUT / f"{uname}_by_year.csv", index=False)

    pooled_auc_bottom = auc_rank(
        (obs.next_decile == 1).astype(int), obs.annual_ret
    )
    pooled_auc_top_weak = auc_rank(
        (obs.next_decile == 10).astype(int), -obs.annual_ret
    )

    d10 = summ[summ.formation_decile == 10].iloc[0]
    d1 = summ[summ.formation_decile == 1].iloc[0]
    baseline_d1 = float((obs.next_decile == 1).mean())
    baseline_crash = float(obs.crash_transition.mean())

    headline = {
        "universe": uname,
        "formation_years": [2010, 2024],
        "formation_observations": int(len(tr)),
        "transition_observations": int(len(obs)),
        "next_outcome_missing_rate": float(tr.missing_next.mean()),
        "baseline": {
            "p_next_D1": baseline_d1,
            "p_crash_transition": baseline_crash,
        },
        "D10": {
            "next_mean_ret": float(d10.next_mean_ret),
            "next_median_ret": float(d10.next_median_ret),
            "p_next_D1": float(d10.p_next_D1),
            "D1_lift_vs_baseline": float(d10.p_next_D1 / baseline_d1)
            if baseline_d1
            else None,
            "p_next_D1_D2": float(d10.p_next_D1_D2),
            "p_next_D10": float(d10.p_next_D10),
            "p_crash_30": float(d10.p_crash_30),
            "p_crash_50": float(d10.p_crash_50),
            "p_negative_delist": float(d10.p_negative_delist),
            "p_crash_transition": float(d10.p_crash_transition),
            "crash_lift_vs_baseline": float(d10.p_crash_transition / baseline_crash)
            if baseline_crash
            else None,
            "delist_next_rate": float(d10.delist_next_rate),
        },
        "D1": {
            "next_mean_ret": float(d1.next_mean_ret),
            "p_next_D10": float(d1.p_next_D10),
            "delist_next_rate": float(d1.delist_next_rate),
        },
        "predictability": {
            "pooled_auc_future_bottom_from_past_strength": float(
                pooled_auc_bottom
            ),
            "pooled_auc_future_top_from_past_weakness": float(
                pooled_auc_top_weak
            ),
            "mean_year_auc_future_bottom_from_past_strength": float(
                yr.auc_bottom_from_strength.mean()
            ),
            "mean_year_auc_future_top_from_past_weakness": float(
                yr.auc_top_from_weakness.mean()
            ),
            "mean_year_spearman_past_vs_next_return": float(
                yr.spearman_past_next.mean()
            ),
        },
        "year_bootstrap": {
            "D10_to_D1": bootstrap_year_metric(yr, "d10_to_D1"),
            "D10_crash_transition": bootstrap_year_metric(
                yr, "d10_crash_transition"
            ),
            "D1_to_D10": bootstrap_year_metric(yr, "d1_to_D10"),
            "D10_minus_all_next_return": bootstrap_year_metric(
                yr, "d10_minus_all"
            ),
        },
    }

    obs[
        [
            "security_id",
            "symbol",
            "name",
            "formation_year",
            "annual_ret",
            "decile",
            "next_ret",
            "next_decile",
            "next_n_trade_days",
            "delist_next",
            "crash_transition",
        ]
    ].to_csv(OUT / f"{uname}_transitions.csv", index=False)

    return headline, yr, obs


headlines = {}
year_frames = {}
obs_frames = {}
for uname, formation in formation_universes.items():
    h, yr, obs = make_transition(uname, formation)
    headlines[uname] = h
    year_frames[uname] = yr
    obs_frames[uname] = obs

# Subperiod stability on primary universe.
obs = obs_frames["seasoned180"].copy()


def period_label(y):
    if y <= 2014:
        return "2010-2014"
    if y <= 2019:
        return "2015-2019"
    return "2020-2024"


obs["subperiod"] = obs.formation_year.map(period_label)
sp = []
for p, g in obs.groupby("subperiod"):
    d10 = g[g.decile == 10]
    d1 = g[g.decile == 1]
    sp.append(
        {
            "subperiod": p,
            "n": len(g),
            "D10_next_mean": d10.next_ret.mean(),
            "D10_next_median": d10.next_ret.median(),
            "D10_to_D1": d10.left_tail_D1.mean(),
            "D10_to_D1_D2": (d10.next_decile <= 2).mean(),
            "D10_crash_transition": d10.crash_transition.mean(),
            "D1_to_D10": (d1.next_decile == 10).mean(),
            "D10_to_D10": (d10.next_decile == 10).mean(),
            "AUC_down": auc_rank((g.next_decile == 1).astype(int), g.annual_ret),
            "AUC_up": auc_rank((g.next_decile == 10).astype(int), -g.annual_ret),
        }
    )
pd.DataFrame(sp).to_csv(OUT / "seasoned180_subperiod.csv", index=False)

# 2025 -> 2026 YTD is FORWARD ONLY. It is excluded from all fitted/statistical
# headline metrics above.
p25 = add_deciles(formation_universes["seasoned180"])
f25 = p25[p25.year == 2025][
    ["security_id", "symbol", "name", "annual_ret", "decile"]
].copy()
y26 = annual[annual.year == 2026][
    ["security_id", "annual_ret", "n_trade_days", "delisted_in_year"]
].rename(
    columns={
        "annual_ret": "ret_2026_ytd",
        "n_trade_days": "days_2026",
        "delisted_in_year": "delisted_2026_ytd",
    }
)
fw = f25.merge(y26, on="security_id", how="left")
fw.to_csv(OUT / "forward_2025_to_2026_ytd.csv", index=False)
fw_obs = fw.dropna(subset=["ret_2026_ytd"])
headlines["forward_2025_to_2026_ytd"] = {
    "cutoff": "2026-09-24",
    "status": "FORWARD_ONLY_NOT_IN_MODEL_SELECTION",
    "n": int(len(fw_obs)),
    "D10_n": int((fw_obs.decile == 10).sum()),
    "D10_mean_ytd": float(
        fw_obs.loc[fw_obs.decile == 10, "ret_2026_ytd"].mean()
    ),
    "all_mean_ytd": float(fw_obs.ret_2026_ytd.mean()),
    "D10_minus_all": float(
        fw_obs.loc[fw_obs.decile == 10, "ret_2026_ytd"].mean()
        - fw_obs.ret_2026_ytd.mean()
    ),
}

methodology = {
    "version": "WCR_PHASE1_V2",
    "annual_return": "compound daily bars.pctChg",
    "formation": "rank each formation year into D1..D10; D10 = past winner",
    "primary_universe": "seasoned before Jan 1, alive at formation year-end, >=180 trading days",
    "outcome": "must be active at next-year start; >=60 trading days OR delisted during next year",
    "survivorship_fix": "next-year outcome does not require survival to year-end",
    "central_test": "P(next D1 | prior D10) and lift vs baseline",
    "asymmetry_test": "AUC future D1 from past strength vs AUC future D10 from past weakness",
    "delisting_note": "delisting is reported separately; observed market return may not equal liquidation/merger consideration",
    "forward_only": "2025 formation -> 2026 YTD, cutoff 2026-09-24",
}
(OUT / "methodology.json").write_text(
    json.dumps(methodology, ensure_ascii=False, indent=2), encoding="utf-8"
)
(OUT / "headline.json").write_text(
    json.dumps(headlines, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(json.dumps(headlines, ensure_ascii=False, indent=2))
