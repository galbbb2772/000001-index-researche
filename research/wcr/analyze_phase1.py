import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

DB="ashare_pit.duckdb"
OUT=Path("wcr_phase1")
OUT.mkdir(exist_ok=True)

con=duckdb.connect(DB, read_only=True)

annual=con.execute(r"""
WITH a AS (
  SELECT
    b.security_id,
    EXTRACT(year FROM b.trade_date)::INTEGER AS year,
    COUNT(*) FILTER (WHERE b.tradestatus=1) AS n_trade_days,
    SUM(CASE WHEN b.isST=1 AND b.tradestatus=1 THEN 1 ELSE 0 END) AS st_days,
    EXP(SUM(
      CASE
        WHEN b.tradestatus=1 AND b.pctChg IS NOT NULL AND b.pctChg > -99.99
        THEN LN(1.0 + b.pctChg/100.0)
        ELSE 0
      END
    )) - 1.0 AS annual_ret,
    AVG(CASE WHEN b.tradestatus=1 THEN b.turn END) AS avg_turn,
    SUM(CASE WHEN b.tradestatus=1 THEN b.amount ELSE 0 END) AS annual_amount,
    MIN(CASE WHEN b.tradestatus=1 THEN b.trade_date END) AS first_trade,
    MAX(CASE WHEN b.tradestatus=1 THEN b.trade_date END) AS last_trade
  FROM bars b
  WHERE EXTRACT(year FROM b.trade_date) BETWEEN 2010 AND 2026
  GROUP BY 1,2
)
SELECT
  a.*,
  s.exchange,
  s.symbol,
  s.name,
  s.list_date,
  s.delist_date
FROM a
JOIN security_master s USING(security_id)
ORDER BY year, security_id
""").df()

annual["year"]=annual["year"].astype(int)
annual["list_date"]=pd.to_datetime(annual["list_date"])
annual["delist_date"]=pd.to_datetime(annual["delist_date"])
annual["st_share"]=annual["st_days"]/annual["n_trade_days"].replace(0,np.nan)

def year_start(y):
    return pd.Timestamp(year=int(y),month=1,day=1)
def year_end(y):
    return pd.Timestamp(year=int(y),month=12,day=31)

annual["seasoned"]=annual.apply(lambda r: pd.notna(r.list_date) and r.list_date < year_start(r.year),axis=1)
annual["active_year_end"]=annual.apply(lambda r: pd.isna(r.delist_date) or r.delist_date > year_end(r.year),axis=1)

def add_deciles(df):
    df=df.copy()
    def dec(s):
        if len(s)<20: return pd.Series(np.nan,index=s.index)
        rank=s.rank(method="first")
        return pd.qcut(rank,10,labels=False)+1
    df["decile"]=df.groupby("year",group_keys=False)["annual_ret"].apply(dec).astype("Int64")
    return df

universes={
  "seasoned180": annual[(annual.seasoned)&(annual.active_year_end)&(annual.n_trade_days>=180)].copy(),
  "all120": annual[(annual.active_year_end)&(annual.n_trade_days>=120)].copy(),
  "nonst180": annual[(annual.seasoned)&(annual.active_year_end)&(annual.n_trade_days>=180)&(annual.st_share==0)].copy(),
}

def auc_rank(y,score):
    y=np.asarray(y,dtype=int); score=np.asarray(score,dtype=float)
    ok=np.isfinite(score)
    y=y[ok]; score=score[ok]
    n1=y.sum(); n0=len(y)-n1
    if n1==0 or n0==0: return np.nan
    ranks=pd.Series(score).rank(method="average").to_numpy()
    return float((ranks[y==1].sum()-n1*(n1+1)/2)/(n1*n0))

def bootstrap_year_metric(year_df, col, seed=20261115, B=10000):
    vals=year_df[col].dropna().to_numpy(float)
    if len(vals)<2: return {"mean":float(np.nanmean(vals)) if len(vals) else None,"ci95":[None,None],"n_years":int(len(vals))}
    rng=np.random.default_rng(seed)
    means=np.empty(B)
    for i in range(B):
        means[i]=rng.choice(vals,size=len(vals),replace=True).mean()
    return {"mean":float(vals.mean()),"ci95":[float(np.quantile(means,.025)),float(np.quantile(means,.975))],"n_years":int(len(vals))}

headline={}
all_outputs=[]

for uname,u0 in universes.items():
    u=add_deciles(u0)
    # complete annual years only; 2026 remains forward-only
    u_complete=u[u.year<=2025].copy()

    nxt=u_complete[["security_id","year","annual_ret","decile","n_trade_days"]].copy()
    nxt["formation_year"]=nxt["year"]-1
    nxt=nxt.rename(columns={"annual_ret":"next_ret","decile":"next_decile","n_trade_days":"next_n_trade_days"})
    nxt=nxt.drop(columns=["year"])

    f=u_complete[u_complete.year.between(2010,2024)].copy()
    tr=f.merge(nxt,on=["security_id","formation_year"],how="left") if "formation_year" in f.columns else None
    # pandas merge key convenience
    if tr is None:
        f["formation_year"]=f["year"]
        tr=f.merge(nxt,on=["security_id","formation_year"],how="left")
    else:
        pass

    # Above branch never happens because formation_year absent; ensure it exists
    if "formation_year" not in tr.columns:
        raise RuntimeError("formation_year merge failed")

    tr["delist_next"]=tr.apply(
        lambda r: pd.notna(r.delist_date) and year_start(r.formation_year+1) <= r.delist_date <= year_end(r.formation_year+1),
        axis=1
    )
    tr["next_eligible"]=tr["next_decile"].notna()
    obs=tr[tr.next_eligible].copy()
    obs["next_decile"]=obs["next_decile"].astype(int)
    obs["decile"]=obs["decile"].astype(int)

    # decile summary
    rows=[]
    for d in range(1,11):
        full=tr[tr.decile==d]
        x=obs[obs.decile==d]
        rows.append({
            "formation_decile":d,
            "formation_n":len(full),
            "next_eligible_n":len(x),
            "retention_rate":len(x)/len(full) if len(full) else np.nan,
            "delist_next_rate":full.delist_next.mean() if len(full) else np.nan,
            "next_mean_ret":x.next_ret.mean(),
            "next_median_ret":x.next_ret.median(),
            "p_next_D1":(x.next_decile==1).mean(),
            "p_next_D1_D2":(x.next_decile<=2).mean(),
            "p_next_D10":(x.next_decile==10).mean(),
            "p_crash_30":(x.next_ret<=-0.30).mean(),
            "p_crash_50":(x.next_ret<=-0.50).mean(),
        })
    summ=pd.DataFrame(rows)
    summ.to_csv(OUT/f"{uname}_decile_summary.csv",index=False)

    trans=pd.crosstab(obs.decile,obs.next_decile,normalize="index").reindex(index=range(1,11),columns=range(1,11),fill_value=0)
    trans.index.name="formation_decile"
    trans.to_csv(OUT/f"{uname}_transition_matrix.csv")

    # per-year metrics for D10 and D1
    yr=[]
    for y,g in obs.groupby("formation_year"):
        d10=g[g.decile==10]; d1=g[g.decile==1]
        full10=tr[(tr.formation_year==y)&(tr.decile==10)]
        yr.append({
            "formation_year":int(y),
            "n":len(g),
            "d10_n":len(d10),
            "d10_next_mean":d10.next_ret.mean(),
            "d10_next_median":d10.next_ret.median(),
            "d10_to_D1":(d10.next_decile==1).mean() if len(d10) else np.nan,
            "d10_to_D1_D2":(d10.next_decile<=2).mean() if len(d10) else np.nan,
            "d10_to_D10":(d10.next_decile==10).mean() if len(d10) else np.nan,
            "d10_crash30":(d10.next_ret<=-0.30).mean() if len(d10) else np.nan,
            "d10_delist_next":full10.delist_next.mean() if len(full10) else np.nan,
            "d1_n":len(d1),
            "d1_to_D10":(d1.next_decile==10).mean() if len(d1) else np.nan,
            "d1_next_mean":d1.next_ret.mean(),
            "all_next_mean":g.next_ret.mean(),
            "d10_minus_all":d10.next_ret.mean()-g.next_ret.mean() if len(d10) else np.nan,
            "d1_minus_all":d1.next_ret.mean()-g.next_ret.mean() if len(d1) else np.nan,
        })
    yr=pd.DataFrame(yr)
    yr.to_csv(OUT/f"{uname}_by_year.csv",index=False)

    # AUC: higher past return predicts future bottom; lower past return predicts future top.
    auc_bottom=auc_rank((obs.next_decile==1).astype(int),obs.annual_ret)
    auc_top_from_weak=auc_rank((obs.next_decile==10).astype(int),-obs.annual_ret)

    d10=summ[summ.formation_decile==10].iloc[0]
    d1=summ[summ.formation_decile==1].iloc[0]
    h={
        "universe":uname,
        "formation_years":[2010,2024],
        "transition_observations":int(len(obs)),
        "formation_observations":int(len(tr)),
        "D10":{
            "next_mean_ret":float(d10.next_mean_ret),
            "next_median_ret":float(d10.next_median_ret),
            "p_next_D1":float(d10.p_next_D1),
            "p_next_D1_D2":float(d10.p_next_D1_D2),
            "p_next_D10":float(d10.p_next_D10),
            "p_crash_30":float(d10.p_crash_30),
            "p_crash_50":float(d10.p_crash_50),
            "delist_next_rate":float(d10.delist_next_rate),
        },
        "D1":{
            "next_mean_ret":float(d1.next_mean_ret),
            "p_next_D10":float(d1.p_next_D10),
            "delist_next_rate":float(d1.delist_next_rate),
        },
        "predictability":{
            "auc_future_bottom_from_past_strength":float(auc_bottom),
            "auc_future_top_from_past_weakness":float(auc_top_from_weak),
        },
        "year_bootstrap":{
            "D10_to_D1":bootstrap_year_metric(yr,"d10_to_D1"),
            "D1_to_D10":bootstrap_year_metric(yr,"d1_to_D10"),
            "D10_minus_all_next_return":bootstrap_year_metric(yr,"d10_minus_all"),
        }
    }
    headline[uname]=h

    obs[["security_id","symbol","name","formation_year","annual_ret","decile","next_ret","next_decile","delist_next"]].to_csv(
        OUT/f"{uname}_transitions.csv",index=False
    )

# subperiod summary using primary universe
primary=add_deciles(universes["seasoned180"])
f=primary[primary.year.between(2010,2024)].copy(); f["formation_year"]=f["year"]
n=primary[primary.year.between(2011,2025)][["security_id","year","annual_ret","decile"]].copy()
n["formation_year"]=n["year"]-1
n=n.rename(columns={"annual_ret":"next_ret","decile":"next_decile"}).drop(columns=["year"])
tr=f.merge(n,on=["security_id","formation_year"],how="inner")
tr["decile"]=tr["decile"].astype(int); tr["next_decile"]=tr["next_decile"].astype(int)
def period_label(y):
    if y<=2014:return "2010-2014"
    if y<=2019:return "2015-2019"
    return "2020-2024"
tr["subperiod"]=tr.formation_year.map(period_label)
sp=[]
for p,g in tr.groupby("subperiod"):
    d10=g[g.decile==10]; d1=g[g.decile==1]
    sp.append({
      "subperiod":p,"n":len(g),
      "D10_next_mean":d10.next_ret.mean(),
      "D10_to_D1":(d10.next_decile==1).mean(),
      "D10_to_D1_D2":(d10.next_decile<=2).mean(),
      "D1_to_D10":(d1.next_decile==10).mean(),
      "D10_to_D10":(d10.next_decile==10).mean(),
    })
pd.DataFrame(sp).to_csv(OUT/"seasoned180_subperiod.csv",index=False)

# 2025 -> 2026 YTD forward observation (not part of fitted sample)
p=add_deciles(universes["seasoned180"])
f25=p[p.year==2025][["security_id","symbol","name","annual_ret","decile"]].copy()
y26=annual[annual.year==2026][["security_id","annual_ret","n_trade_days"]].rename(columns={"annual_ret":"ret_2026_ytd","n_trade_days":"days_2026"})
fw=f25.merge(y26,on="security_id",how="left")
fw.to_csv(OUT/"forward_2025_to_2026_ytd.csv",index=False)
fw_obs=fw.dropna(subset=["ret_2026_ytd"])
headline["forward_2025_to_2026_ytd"]={
  "cutoff":"2026-09-24",
  "status":"FORWARD_ONLY_NOT_IN_MODEL_SELECTION",
  "n":int(len(fw_obs)),
  "D10_n":int((fw_obs.decile==10).sum()),
  "D10_mean_ytd":float(fw_obs.loc[fw_obs.decile==10,"ret_2026_ytd"].mean()),
  "all_mean_ytd":float(fw_obs.ret_2026_ytd.mean()),
  "D10_minus_all":float(fw_obs.loc[fw_obs.decile==10,"ret_2026_ytd"].mean()-fw_obs.ret_2026_ytd.mean()),
}

(OUT/"headline.json").write_text(json.dumps(headline,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(headline,ensure_ascii=False,indent=2))
