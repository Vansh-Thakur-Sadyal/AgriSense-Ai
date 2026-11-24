"""Collect verified numbers, five raw records per dataset and real sample outputs for the AI/ML report.
Writes out/aiml_facts.json. Every value comes from the datasets, the model cards or a live model call."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))
RAW = ROOT / "data" / "raw"
OUT = {}

from app import ml, fertiliser  # noqa: E402
from train_yield import clean  # noqa: E402

# ---------------- crop
crop = pd.read_csv(RAW / "Crop_recommendation.csv")
OUT["crop"] = {
    "rows": len(crop), "features": len(crop.columns) - 1, "classes": crop.label.nunique(),
    "per_class": int(crop.label.value_counts().iloc[0]), "majority_share": round(crop.label.value_counts().max() / len(crop), 4),
    "records": crop.groupby("label").head(1).sample(5, random_state=7).to_dict("records"),
    "columns": list(crop.columns),
}

# ---------------- fertiliser
fert = pd.read_csv(RAW / "fertiliser" / "Fertilizer_Prediction.csv")
OUT["fert"] = {
    "rows": len(fert), "features": len(fert.columns) - 1, "columns": list(fert.columns),
    "counts": fert["Fertilizer Name"].value_counts().to_dict(),
    "majority_share": round(fert["Fertilizer Name"].value_counts().max() / len(fert), 4),
    "records": fert.groupby("Fertilizer Name").head(1).sample(5, random_state=3).to_dict("records"),
}

# ---------------- yield
yraw = pd.read_csv(RAW / "yield" / "India Agriculture Crop Production.csv", low_memory=False)
yc = clean(yraw.copy())
OUT["yield"] = {
    "raw_rows": len(yraw), "columns": list(yraw.columns), "clean_rows": len(yc),
    "crops": yc.Crop.nunique(), "districts": yc.District.nunique(), "states": yc.State.nunique(),
    "years": f"{yc.year.min()}-{yc.year.max()}",
    "yield_mean": round(yc["yield"].mean(), 3), "yield_sd": round(yc["yield"].std(), 3),
    "yield_median": round(yc["yield"].median(), 3), "yield_min": round(yc["yield"].min(), 4), "yield_max": round(yc["yield"].max(), 2),
    "records": yraw[yraw.Crop.isin(["Rice", "Wheat", "Maize", "Potato", "Gram"]) & (yraw["Production Units"] == "Tonnes")]
    .groupby("Crop").head(1).to_dict("records"),
}

# ---------------- leaf
leaf_root = RAW / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"
from PIL import Image  # noqa: E402
classes = sorted(p.name for p in leaf_root.iterdir() if p.is_dir())
counts = {c: sum(1 for _ in (leaf_root / c).iterdir()) for c in classes}
picks = ["Tomato___Late_blight", "Potato___Early_blight", "Corn___Common_rust", "Apple___healthy", "Grape___Black_rot"]
recs = []
for c in picks:
    f = sorted((leaf_root / c).iterdir())[0]
    im = Image.open(f)
    recs.append({"file": f.name, "folder (label)": c, "width x height": f"{im.width} x {im.height}", "mode": im.mode,
                 "size_kb": round(f.stat().st_size / 1024, 1)})
lc = ml.card("leaf_disease")
cm = np.array(lc["confusion_matrix"])
OUT["leaf"] = {
    "classes": len(classes), "images": sum(counts.values()), "largest": max(counts, key=counts.get),
    "largest_n": max(counts.values()), "smallest": min(counts, key=counts.get), "smallest_n": min(counts.values()),
    "test_n": int(cm.sum()), "majority_share": round(cm.sum(1).max() / cm.sum(), 4), "records": recs,
    "lowest_recall": sorted(lc["per_class_recall"].items(), key=lambda kv: kv[1])[:6],
}

# ---------------- sample outputs (real model calls)
samples = []
for r in crop.sample(3, random_state=11).to_dict("records"):
    x = {k: float(r[k]) for k in ml.CROP_FEATURES}
    o = ml.recommend_crop(x)
    samples.append({"model": "Crop", "input": ", ".join(f"{k}={r[k]:.4g}" for k in ml.CROP_FEATURES),
                    "truth": r["label"], "output": f"{o['crop']} ({o['confidence']:.0%})"})
fc = ml.card("crop_model")
for r in fert.sample(3, random_state=5).to_dict("records"):
    inp = {"basis": "fertiliser_dataset", "N": r["Nitrogen"], "P": r["Phosphorous"], "K": r["Potassium"]}
    o = fertiliser.recommend(inp, fc["crop_profiles"])
    samples.append({"model": "Fertiliser", "input": f"Nitrogen={r['Nitrogen']}, Phosphorous={r['Phosphorous']}, Potassium={r['Potassium']}",
                    "truth": r["Fertilizer Name"], "output": f"{o['fertiliser']['name']} ({o['fertiliser']['confidence']:.0%})"})
for c in picks[:3]:
    f = sorted((leaf_root / c).iterdir())[1]
    o = ml.diagnose(f.read_bytes())
    samples.append({"model": "Leaf disease", "input": f"{c}/{f.name}", "truth": c,
                    "output": f"{o['best']['class']} ({o['best']['probability']:.1%}, {o['verdict']})"})
for st, di, cr, se in (("Punjab", "LUDHIANA", "Rice", "Kharif"), ("Uttar Pradesh", "AGRA", "Wheat", "Rabi")):
    o = ml.predict_yield(st, di, cr, se, 2021, 100)
    samples.append({"model": "Yield", "input": f"{st}, {di}, {cr}, {se}, 2021-22, 100 ha", "truth": f"district mean {o['district_mean_t_ha']} t/ha",
                    "output": f"{o['yield_t_ha']} t/ha (80% range {o['interval_80'][0]}-{o['interval_80'][1]})"})
# chain: crop -> shortfall -> fertiliser
r = crop[crop.label == "maize"].iloc[0].to_dict()
low = dict(r, N=30.0)
co = ml.recommend_crop({k: float(low[k]) for k in ml.CROP_FEATURES})
fo = fertiliser.recommend({"basis": "crop_profile", "crop": "maize", "N": 30, "P": low["P"], "K": low["K"]}, fc["crop_profiles"])
OUT["chain"] = {"crop_out": co["crop"], "conf": co["confidence"], "input": {k: low[k] for k in ("N", "P", "K")},
                "fert": fo["fertiliser"]["name"] if fo.get("fertiliser") else None, "status": fo.get("status"), "summary": fo.get("summary"),
                "typical": fo.get("typical"), "shortfall": fo.get("shortfall"), "category": fo.get("category")}
OUT["samples"] = samples

(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "aiml_facts.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str)[:6000])
