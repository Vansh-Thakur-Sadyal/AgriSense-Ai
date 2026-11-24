"""Crop yield (t/ha) from the India Agriculture Crop Production dataset (1997-2020).

Validation is TEMPORAL: train on crop years up to 2016-17, test on 2017-18 onward, so the test
measures forecasting a season the model has never seen. Three honest baselines are reported
alongside the model.

The dataset has no weather or soil columns, so the model does not take any. The app shows
weather and soil separately and never pretends they fed this prediction.

Writes app/models/yield_model.txt (LightGBM), app/models/yield_model.json (card) and
app/data/production.sqlite (cleaned rows, for analytics and lag lookups).
"""
import json
import sqlite3
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "yield" / "India Agriculture Crop Production.csv"
OUT = ROOT / "app" / "models"
DB = ROOT / "app" / "data" / "production.sqlite"
TEST_FROM = 2017
CATS = ["State", "District", "Crop", "Season"]
FEATS = CATS + ["log_area", "lag1", "lag2", "lag_trend", "lag_mean3", "lag_count",
                "dist_crop_mean", "state_crop_lag1", "area_change"]


def clean(df):
    n0 = len(df)
    df = df[df["Production Units"] == "Tonnes"].copy()
    df = df.dropna(subset=["Crop", "Season", "Area", "Production"])
    df = df[(df.Area >= 1) & (df.Production > 0)]
    for c in ["State", "District", "Crop", "Season"]:
        df[c] = df[c].astype(str).str.strip()
    df["District"] = df["District"].str.upper()
    df["year"] = df.Year.str[:4].astype(int)
    df["yield"] = df.Production / df.Area
    # Per-crop outlier trim: the raw file has yields up to 43,958 t/ha, which are entry errors.
    lo = df.groupby("Crop")["yield"].transform(lambda s: s.quantile(0.005))
    hi = df.groupby("Crop")["yield"].transform(lambda s: s.quantile(0.995))
    df = df[(df["yield"] >= lo) & (df["yield"] <= hi)]
    # Duplicate (district, crop, season, year) rows exist; aggregate them.
    df = (df.groupby(["State", "District", "Crop", "Season", "year"], as_index=False)
            .agg(Area=("Area", "sum"), Production=("Production", "sum")))
    df["yield"] = df.Production / df.Area
    print(f"rows: raw {n0} -> clean {len(df)}")
    return df


def add_lags(df):
    df = df.sort_values("year").copy()
    key = ["District", "Crop", "Season"]
    g = df.groupby(key)["yield"]
    df["lag1"] = g.shift(1)
    df["lag_mean3"] = g.transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df["lag_count"] = df.groupby(key).cumcount()
    # Long-run district-crop mean from PREVIOUS years only (expanding), so no target leakage.
    df["dist_crop_mean"] = df.groupby(["District", "Crop"])["yield"].transform(
        lambda s: s.shift(1).expanding().mean())
    df["lag2"] = g.shift(2)
    df["lag_trend"] = df.lag1 - df.lag2
    df["area_change"] = np.log1p(df.Area) - np.log1p(df.groupby(key)["Area"].shift(1))
    # State-wide yield of the crop in the previous year (area-weighted) - captures regional shocks.
    st = (df.groupby(["State", "Crop", "year"]).apply(lambda g: g.Production.sum() / g.Area.sum(),
          include_groups=False).rename("st").reset_index())
    st["year"] = st["year"] + 1
    df = df.merge(st.rename(columns={"st": "state_crop_lag1"}), on=["State", "Crop", "year"], how="left")
    df["log_area"] = np.log1p(df.Area)
    return df


def base_of(d, crop_mean):
    """Persistence base: 3-yr mean -> long-run district mean -> state last year -> national crop mean."""
    b = d["lag_mean3"].copy()
    b = b.fillna(d["dist_crop_mean"]).fillna(d["state_crop_lag1"])
    return b.fillna(d["Crop"].map(crop_mean).astype(float)).fillna(float(crop_mean.mean()))


def metrics(y, p):
    return {"r2": round(float(r2_score(y, p)), 4), "mae_t_ha": round(float(mean_absolute_error(y, p)), 4),
            "mape_median_pct": round(float(np.median(np.abs(p - y) / np.maximum(y, 1e-6)) * 100), 2)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    df = add_lags(clean(pd.read_csv(RAW)))
    for c in CATS:
        df[c] = df[c].astype("category")
    categories = {c: list(df[c].cat.categories) for c in CATS}

    tr, te = df[df.year < TEST_FROM], df[df.year >= TEST_FROM]
    val = tr[tr.year == TEST_FROM - 1]
    fit = tr[tr.year < TEST_FROM - 1]
    params = dict(objective="regression_l1", learning_rate=0.05, num_leaves=127, min_data_in_leaf=40,
                  feature_fraction=0.85, bagging_fraction=0.85, bagging_freq=1, cat_smooth=20,
                  verbose=-1, seed=42)
    # Target is the log-ratio to a persistence base, so the model learns corrections to
    # "the recent normal" instead of re-learning yield levels from scratch.
    crop_mean = tr.groupby("Crop", observed=True)["yield"].mean()
    for d in (tr, te, fit, val):
        d["base"] = base_of(d, crop_mean)
    tgt = lambda d: np.log1p(d["yield"]) - np.log1p(d["base"])
    dfit = lgb.Dataset(fit[FEATS], tgt(fit), categorical_feature=CATS)
    dval = lgb.Dataset(val[FEATS], tgt(val), categorical_feature=CATS, reference=dfit)
    booster = lgb.train(params, dfit, 3000, valid_sets=[dval],
                        callbacks=[lgb.early_stopping(100, verbose=False)])
    best_iter = max(booster.best_iteration, 50)
    dall = lgb.Dataset(tr[FEATS], tgt(tr), categorical_feature=CATS)
    booster = lgb.train(params, dall, best_iter)

    y = te["yield"].values
    pred = np.expm1(booster.predict(te[FEATS]) + np.log1p(te["base"].values))
    res = {"LightGBM (this model)": metrics(y, pred)}
    has_lag = te.lag1.notna()
    res["Baseline: last year's yield"] = {**metrics(y[has_lag], te.lag1[has_lag].values),
                                         "rows": int(has_lag.sum())}
    has_m = te.lag_mean3.notna()
    res["Baseline: mean of previous 3 years"] = {**metrics(y[has_m], te.lag_mean3[has_m].values),
                                                "rows": int(has_m.sum())}
    res["Baseline: national crop mean"] = metrics(y, te.Crop.map(crop_mean).astype(float).fillna(tr["yield"].mean()).values)
    res["LightGBM on rows with a lag"] = metrics(y[has_lag], pred[has_lag])

    # Residual spread on the test years per crop -> an empirical 80% interval, not a model guess.
    resid = np.log1p(y) - np.log1p(pred)
    te_res = pd.DataFrame({"Crop": te.Crop.astype(str).values, "r": resid})
    intervals = {c: {"lo": round(float(g.r.quantile(0.10)), 4), "hi": round(float(g.r.quantile(0.90)), 4),
                     "n": int(len(g))} for c, g in te_res.groupby("Crop")}
    overall = {"lo": round(float(np.quantile(resid, 0.10)), 4), "hi": round(float(np.quantile(resid, 0.90)), 4)}
    coverage = float(np.mean((resid >= overall["lo"]) & (resid <= overall["hi"])))

    gain = booster.feature_importance("gain")
    importance = sorted([{"feature": f, "importance": round(float(g / gain.sum()), 4)}
                         for f, g in zip(FEATS, gain)], key=lambda r: -r["importance"])
    per_crop = []
    for c, g in te.assign(pred=pred).groupby("Crop", observed=True):
        if len(g) >= 50:
            per_crop.append({"crop": c, "rows": int(len(g)), **metrics(g["yield"].values, g.pred.values)})
    per_crop.sort(key=lambda r: -r["rows"])

    # Final fit on EVERY year (incl. the 2017-2020 test years) with the evaluated recipe and round
    # count, so the latest seasons inform predictions. Metrics above stay the honest estimate.
    crop_mean_all = df.groupby("Crop", observed=True)["yield"].mean()
    df["base"] = base_of(df, crop_mean_all)
    final_rounds = int(round(best_iter * len(df) / len(tr)))
    booster = lgb.train(params, lgb.Dataset(df[FEATS], tgt(df), categorical_feature=CATS), final_rounds)
    booster.save_model(str(OUT / "yield_model.txt"))
    crop_mean = crop_mean_all
    card = {
        "name": "Crop yield prediction",
        "dataset": "India Agriculture Crop Production (data.gov.in, 1997-98 to 2020-21)",
        "cleaning": "Tonnes-only crops (bales/nuts dropped), area >= 1 ha, per-crop 0.5-99.5 percentile "
                    "yield trim, duplicates summed",
        "rows_clean": int(len(df)), "rows_train": int(len(tr)), "rows_test": int(len(te)),
        "validation": f"temporal: train crop years < {TEST_FROM}-{(TEST_FROM + 1) % 100:02d}, test >= that",
        "features": FEATS,
        "not_in_dataset": ["rainfall", "temperature", "humidity", "soil pH", "soil nitrogen",
                           "organic carbon", "irrigation", "variety"],
        "best_iteration": int(best_iter),
        "deployed_fit": {"rows": int(len(df)), "iterations": final_rounds,
                         "years": f"{int(df.year.min())}-{int(df.year.max())}",
                         "note": "refit on all years after the temporal test; metrics are from that test"},
        "results": res,
        "interval_80": {"overall": overall, "per_crop": intervals, "test_coverage": round(coverage, 4),
                        "note": "From log-residual quantiles on the held-out test years"},
        "importance_gain": importance,
        "per_crop_test": per_crop,
        "categories": categories,
        "target": "log1p(yield) - log1p(base); base = 3-yr mean -> district mean -> state last year -> national crop mean",
        "crop_mean": {str(k): round(float(v), 4) for k, v in crop_mean.items()},
        "trained_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    (OUT / "yield_model.json").write_text(json.dumps(card, indent=1))

    store = df[["State", "District", "Crop", "Season", "year", "Area", "Production", "yield"]].copy()
    for c in CATS:
        store[c] = store[c].astype(str)
    if DB.exists():
        DB.unlink()
    with sqlite3.connect(DB) as con:
        store.to_sql("production", con, index=False)
        con.execute("CREATE INDEX ix_dcs ON production(District, Crop, Season, year)")
        con.execute("CREATE INDEX ix_sc ON production(State, Crop, year)")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
