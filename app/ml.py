"""Model serving: crop recommendation, yield, leaf disease. Model cards are read, never written."""
import io
import json
import sqlite3
from functools import lru_cache
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODELS = HERE / "models"
PROD_DB = HERE / "data" / "production.sqlite"


def card(name):
    p = MODELS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


# ---------------- crop recommendation ----------------
@lru_cache
def _crop():
    import joblib
    return joblib.load(MODELS / "crop_model.joblib"), card("crop_model")


CROP_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
LIMITS = {"N": (0, 200), "P": (0, 200), "K": (0, 250), "temperature": (-5, 55),
          "humidity": (0, 100), "ph": (3, 10), "rainfall": (0, 4000)}


def validate(inputs, limits=LIMITS):
    errs = {}
    out = {}
    for k, (lo, hi) in limits.items():
        v = inputs.get(k)
        try:
            v = float(v)
        except (TypeError, ValueError):
            errs[k] = "required number"
            continue
        if not lo <= v <= hi:
            errs[k] = f"must be between {lo} and {hi}"
        out[k] = v
    return out, errs


def suitability(profile, x):
    """0-100 per feature: 100 inside the crop's p10-p90 band in the training data, falling off
    linearly to 0 at the crop's observed min/max widened by one band width."""
    s = {}
    for f in CROP_FEATURES:
        p = profile[f]
        lo, hi = p["p10"], p["p90"]
        width = max(hi - lo, 1e-6)
        v = x[f]
        if lo <= v <= hi:
            s[f] = 100.0
        else:
            d = (lo - v) if v < lo else (v - hi)
            s[f] = max(0.0, 100.0 * (1 - d / width))
        s[f] = round(s[f], 1)
    return s


def recommend_crop(x):
    model, c = _crop()
    X = np.array([[x[f] for f in CROP_FEATURES]])
    proba = model.predict_proba(X)[0]
    order = np.argsort(proba)[::-1]
    classes = list(model.classes_)
    top = [{"crop": classes[i], "probability": round(float(proba[i]), 4),
            "suitability": suitability(c["crop_profiles"][classes[i]], x)} for i in order[:4]]
    best = top[0]
    prof = c["crop_profiles"][best["crop"]]
    out_of_band = [f for f, v in best["suitability"].items() if v < 100]
    in_band = [f for f in CROP_FEATURES if f not in out_of_band]
    # Training range check: the model never saw inputs beyond the dataset's min/max.
    outside = [f for f in CROP_FEATURES
               if not c["feature_ranges"][f]["min"] <= x[f] <= c["feature_ranges"][f]["max"]]
    return {
        "crop": best["crop"], "confidence": best["probability"], "top": top,
        "profile": {f: prof[f] for f in CROP_FEATURES},
        "in_band": in_band, "out_of_band": out_of_band, "outside_training_range": outside,
        "model": c["selected_model"], "model_accuracy": c["test_accuracy"],
    }


# ---------------- yield ----------------
@lru_cache
def _yield():
    import lightgbm as lgb
    return lgb.Booster(model_file=str(MODELS / "yield_model.txt")), card("yield_model")


def prod_rows(sql, args=()):
    con = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args).fetchall()]
    finally:
        con.close()


def yield_options():
    c = card("yield_model")
    return {k: c["categories"][k] for k in ("State", "Crop", "Season")}


def districts(state):
    return [r["District"] for r in prod_rows(
        "SELECT DISTINCT District FROM production WHERE State=? ORDER BY District", (state,))]


def predict_yield(state, district, crop, season, year, area_ha):
    import pandas as pd
    booster, c = _yield()
    cats = c["categories"]
    district = district.upper()
    for k, v in (("State", state), ("District", district), ("Crop", crop), ("Season", season)):
        if v not in cats[k]:
            raise ValueError(f"{k} '{v}' is not in the training data")
    hist = prod_rows("SELECT year, yield, Area FROM production WHERE District=? AND Crop=? AND Season=? "
                     "AND year < ? ORDER BY year", (district, crop, season, year))
    ys = [h["yield"] for h in hist]
    allh = prod_rows("SELECT AVG(yield) m FROM production WHERE District=? AND Crop=? AND year < ?",
                     (district, crop, year))
    st = prod_rows("SELECT SUM(Production)/SUM(Area) y FROM production WHERE State=? AND Crop=? AND year=?",
                   (state, crop, year - 1))
    lag1 = ys[-1] if ys and hist[-1]["year"] == year - 1 else (ys[-1] if ys else None)
    row = {
        "State": state, "District": district, "Crop": crop, "Season": season,
        # The model's area feature is the DISTRICT's cultivated area for this crop (that is what
        # the training rows hold). A farm's few hectares would be far out of distribution, so the
        # district's latest recorded area is used and the farm area only scales production.
        "log_area": float(np.log1p(hist[-1]["Area"])) if hist else None,
        "lag1": lag1, "lag2": ys[-2] if len(ys) >= 2 else None,
        "lag_mean3": float(np.mean(ys[-3:])) if ys else None,
        "lag_count": len(ys),
        "dist_crop_mean": allh[0]["m"] if allh and allh[0]["m"] is not None else None,
        "state_crop_lag1": st[0]["y"] if st and st[0]["y"] is not None else None,
        "area_change": 0.0 if hist else None,
    }
    row["lag_trend"] = (row["lag1"] - row["lag2"]) if row["lag1"] is not None and row["lag2"] is not None else None
    feats = c["features"]
    X = pd.DataFrame([{f: row[f] for f in feats}])
    for k in ("State", "District", "Crop", "Season"):
        X[k] = pd.Categorical(X[k], categories=cats[k])
    for f in feats:
        if f not in ("State", "District", "Crop", "Season"):
            X[f] = X[f].astype(float)
    base = next((row[k] for k in ("lag_mean3", "dist_crop_mean", "state_crop_lag1") if row[k] is not None),
                c["crop_mean"].get(crop))
    log_ratio = float(booster.predict(X)[0])
    pred = float(np.expm1(log_ratio + np.log1p(base)))
    contrib = booster.predict(X, pred_contrib=True)[0]
    shap = sorted([{"feature": f, "value": None if row[f] is None or isinstance(row[f], str) else round(row[f], 3),
                    "label": row[f] if isinstance(row[f], str) else None,
                    "contribution": round(float(v), 4)} for f, v in zip(feats, contrib[:-1])],
                  key=lambda r: -abs(r["contribution"]))
    iv = c["interval_80"]["per_crop"].get(crop)
    if not iv or iv["n"] < 30:
        iv = c["interval_80"]["overall"]
    lo = float(np.expm1(np.log1p(pred) + iv["lo"]))
    hi = float(np.expm1(np.log1p(pred) + iv["hi"]))
    hist_mean = float(np.mean(ys)) if ys else None
    category = None
    if hist_mean:
        r = pred / hist_mean
        category = "above district average" if r > 1.1 else "below district average" if r < 0.9 else "near district average"
    return {
        "yield_t_ha": round(pred, 3), "interval_80": [round(lo, 3), round(hi, 3)],
        "production_t": round(pred * area_ha, 1) if area_ha else None,
        "base_t_ha": round(base, 3), "base_source": next((k for k in ("lag_mean3", "dist_crop_mean", "state_crop_lag1")
                                                          if row[k] is not None), "crop_mean"),
        "district_history": [{"year": h["year"], "yield": round(h["yield"], 3)} for h in hist],
        "district_mean_t_ha": round(hist_mean, 3) if hist_mean else None,
        "category": category, "contributions": shap,
        "explanation_base": round(float(contrib[-1]), 4),
        "years_of_history": len(ys),
    }


def production_series(state=None, district=None, crop=None, season=None):
    where, args = [], []
    for col, v in (("State", state), ("District", district.upper() if district else None),
                   ("Crop", crop), ("Season", season)):
        if v:
            where.append(f"{col}=?")
            args.append(v)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    series = prod_rows(f"SELECT year, SUM(Area) area, SUM(Production) production, "
                       f"SUM(Production)/SUM(Area) yield, COUNT(*) n FROM production {w} GROUP BY year ORDER BY year",
                       tuple(args))
    # Crop mix ignores the crop filter (otherwise it is always 100% of the chosen crop) and uses the
    # latest COMPLETE year (2020-21 is partial in the source).
    w2, a2 = [], []
    for col, v in (("State", state), ("District", district.upper() if district else None), ("Season", season)):
        if v:
            w2.append(f"{col}=?")
            a2.append(v)
    wc = " AND ".join(w2 + ["year=2019"])
    top = prod_rows(f"SELECT Crop crop, SUM(Area) area FROM production WHERE {wc} "
                    f"GROUP BY Crop ORDER BY area DESC LIMIT 8", tuple(a2))
    return {"series": series, "top_crops_by_area": top}


# ---------------- leaf disease ----------------
@lru_cache
def _leaf():
    import onnxruntime as ort
    c = card("leaf_disease")
    sess = ort.InferenceSession(str(MODELS / "leaf_disease.onnx"), providers=["CPUExecutionProvider"])
    return sess, c


def leaf_ready():
    return (MODELS / "leaf_disease.onnx").exists() and (MODELS / "leaf_disease.json").exists()


def _prep(img, c):
    s = c["input"]["size"]
    a = np.asarray(img.resize((s, s), resample=2), dtype=np.float32) / 255.0  # 2 = BILINEAR
    a = (a - np.array(c["input"]["mean"], dtype=np.float32)) / np.array(c["input"]["std"], dtype=np.float32)
    return a.transpose(2, 0, 1)


def pretty(cls):
    crop, _, cond = cls.partition("___")
    crop = crop.replace("_", " ").replace(",", "").strip()
    cond = cond.replace("_", " ").strip()
    return crop, cond


def diagnose(image_bytes):
    from PIL import Image, ImageOps
    sess, c = _leaf()
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    x = _prep(img, c)
    batch = np.stack([x, x[:, :, ::-1]])  # flip test-time augmentation
    logits = sess.run(None, {"image": batch})[0].mean(0)
    z = logits / c["temperature"]
    p = np.exp(z - z.max())
    p /= p.sum()
    order = np.argsort(p)[::-1]
    top = []
    for i in order[:5]:
        crop, cond = pretty(c["classes"][i])
        top.append({"class": c["classes"][i], "crop": crop, "condition": cond, "probability": round(float(p[i]), 4)})
    best = top[0]
    if best["class"] == "Background_without_leaves":
        verdict = "no_leaf"
    elif best["probability"] < c["threshold"]:
        verdict = "uncertain"
    else:
        verdict = "healthy" if best["condition"].lower() == "healthy" else "diseased"
    return {"verdict": verdict, "top": top, "threshold": c["threshold"], "best": best}
