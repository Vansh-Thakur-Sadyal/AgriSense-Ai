"""Fertiliser recommendation: an ML model trained on Fertilizer Prediction.csv names the fertiliser.

The model (ml/train_fertiliser.py) is Logistic Regression on N, P and K - in that dataset the other
columns (weather, moisture, soil and crop type) carry no information about the label. Its N, P, K
describe the nutrient NEED to be supplied (Urea rows: high N, zero P and K), on the dataset's own
scale (N and P 0-42, K 0-19). They are not soil contents, so three input bases are supported:

* basis="fertiliser_dataset": the user already has numbers on that scale - they go to the model as-is.
* basis="crop_profile": soil values on the Crop_recommendation dataset's scale. Each nutrient is
  compared with the chosen crop's TYPICAL (median) level in that dataset.
* basis="soil_test": a lab soil test of available nutrients in kg/ha. Each nutrient is compared with
  the middle of the Soil Health Card "medium" band.

For the last two, the shortfall below the typical level (as a fraction of it) is mapped onto the
fertiliser dataset's range for that nutrient - that is the "need" the model sees. The mapping is a
documented bridge between two datasets with different units, not a measured quantity, and it is
returned with every result. When nothing is short, no fertiliser is named.

The output names a fertiliser. It never states a dose or a schedule.
"""
from functools import lru_cache
import json
from pathlib import Path

MODELS = Path(__file__).resolve().parent / "models"
NAMES = {"N": "Nitrogen", "P": "Phosphorus", "K": "Potassium"}
MIN_SHORTFALL = 0.05  # shortfalls under 5 % of the typical level are treated as none

SHC = {  # kg/ha available nutrient
    "N": {"low": 280, "high": 560},
    "P": {"low": 10, "high": 25},
    "K": {"low": 110, "high": 280},
}
SHC_SOURCE = ("Soil Health Card rating ranges (Govt. of India), after Muhr et al. (1965): "
              "N <280 low, 280-560 medium, >560 high; P <10 low, 10-25 medium, >25 high; "
              "K <110 low, 110-280 medium, >280 high (kg/ha). Typical level = middle of the medium band.")

OPTIONS_HIGH = {
    "N": "Nitrogen is above the typical level: skip extra nitrogen; excess N favours lodging and some pests.",
    "P": "Phosphorus is above the typical level: skip phosphatic fertiliser; high P can lock up zinc.",
    "K": "Potassium is above the typical level: skip potassic fertiliser this season.",
}


@lru_cache
def _model():
    import joblib
    p = MODELS / "fertiliser_model.joblib"
    if not p.exists():
        return None, None
    return joblib.load(p), json.loads((MODELS / "fertiliser_model.json").read_text())


def ready():
    return _model()[0] is not None


def card():
    return _model()[1]


def supplies(name):
    """Nutrients a fertiliser grade supplies, e.g. DAP 18-46-0 -> {"N", "P"}."""
    g = card()["grades"].get(name, {}).get("grade", "")
    parts = g.split("-")
    return {n for n, v in zip("NPK", parts) if v.strip() not in ("0", "")} if len(parts) == 3 else set()


def predict(need, require=()):
    """need: {"N","P","K"} on the fertiliser dataset scale -> name, confidence, top 3.

    require: nutrients the fertiliser must supply; the model's highest-ranked fertiliser that supplies
    all of them is chosen (the model's own first choice is returned too)."""
    import numpy as np
    import pandas as pd
    model, c = _model()
    if model is None:
        raise RuntimeError("The fertiliser model is not trained yet")
    feats = c["features"]
    base = np.array([float(need[k]) for k in feats])
    proba = model.predict_proba(pd.DataFrame([base], columns=feats))[0]
    ranked = [{"name": str(model.classes_[i]), "probability": round(float(proba[i]), 4),
               **c["grades"].get(str(model.classes_[i]), {})} for i in proba.argsort()[::-1]]
    ok = [r for r in ranked if set(require) <= supplies(r["name"])] or ranked
    pick = ok[0]
    out_of_range = [k for k in feats if not c["ranges"][k]["min"] <= need[k] <= c["ranges"][k]["max"]]
    return {"name": pick["name"], "confidence": pick["probability"], "top": ranked[:3],
            "grade": pick.get("grade"), "supplies": pick.get("supplies"), "model_input": {k: float(need[k]) for k in feats},
            "outside_training_range": out_of_range, "model_first_choice": ranked[0]["name"],
            "filtered": pick["name"] != ranked[0]["name"]}


def _typical(basis, crop, crop_profiles):
    if basis == "soil_test":
        return {n: (SHC[n]["low"] + SHC[n]["high"]) / 2 for n in NAMES}, "kg/ha"
    return {n: float(crop_profiles[crop][n]["median"]) for n in NAMES}, "dataset scale"


def recommend(inputs, crop_profiles):
    basis = inputs.get("basis", "soil_test")
    crop = inputs.get("crop")
    c = card()
    values = {k: float(inputs[k]) for k in NAMES}
    if basis == "crop_profile" and crop not in crop_profiles:
        raise ValueError("Choose one of the 22 crops in the crop-recommendation dataset for this basis")
    if basis not in ("soil_test", "crop_profile", "fertiliser_dataset"):
        raise ValueError("Unknown basis")

    status, why, notes = {}, [], []
    if basis == "fertiliser_dataset":
        need = dict(values)
        typical, unit, shortfall = None, "fertiliser dataset scale", None
        for n, v in values.items():
            status[n] = "needed" if v > 0 else "none"
            why.append(f"{NAMES[n]} need {v:g} on the fertiliser dataset's scale "
                       f"({c['ranges'][n]['min']:g}-{c['ranges'][n]['max']:g} in the data).")
        bridge = "Numbers were entered on the fertiliser dataset's own scale, so they went to the model unchanged."
    else:
        typical, unit = _typical(basis, crop, crop_profiles)
        shortfall, need = {}, {}
        for n, v in values.items():
            t = typical[n]
            s = max(0.0, (t - v) / t) if t > 0 else 0.0
            shortfall[n] = round(0.0 if s < MIN_SHORTFALL else s, 3)
        top_s = max(shortfall.values())
        for n, v in values.items():
            s = shortfall[n]
            # keep the proportions between nutrients; the most-short one sits at the top of the dataset range
            need[n] = round(s / top_s * c["need_profile"][n]["max"], 2) if top_s > 0 else 0.0
            status[n] = "short" if s > 0 else ("above" if v > typical[n] * 1.5 else "adequate")
            why.append(f"{NAMES[n]} {v:g} vs typical {typical[n]:g} {unit}: "
                       + (f"{s * 100:.0f}% short." if s > 0 else "no shortfall."))
        for n in NAMES:
            if status[n] == "above":
                notes.append(OPTIONS_HIGH[n])
        bridge = ("Each nutrient's shortfall below the typical level"
                  + (f" for {crop}" if basis == "crop_profile" else "")
                  + " was turned into a nutrient need on the fertiliser dataset's scale ("
                  + ", ".join(f"{n} 0-{c['need_profile'][n]['max']:g}" for n in NAMES)
                  + "), keeping the proportions between nutrients: the most-short nutrient is placed at the top "
                  "of its range. The two datasets use different units, so this tells the model WHICH nutrients "
                  "are needed and in what proportion - not how much. Only fertilisers that supply every nutrient "
                  "making up at least a quarter of the largest shortfall are considered.")

    if all(v <= 0 for v in need.values()):
        fert = {"name": None, "confidence": None, "top": [], "grade": None, "supplies": None, "outside_training_range": []}
        headline = "No fertiliser needed"
        explanation = "None of N, P or K is below the typical level, so the model was not asked to name a fertiliser."
    else:
        # a nutrient must be supplied when it is a real part of the need (>= 1/4 of the largest shortfall)
        require = [n for n in NAMES if shortfall is None and need[n] > 0
                   or shortfall is not None and shortfall[n] >= 0.25 * max(shortfall.values())]
        fert = predict(need, require)
        headline = fert["name"]
        explanation = f"{fert['name']} ({fert['grade']}) - {fert['supplies']}."
        if fert["confidence"] < 0.5:
            notes.append(f"The model is not sure ({fert['confidence'] * 100:.0f}%). Ask the assistant to talk the "
                         "options through, and confirm with a soil test or your KVK.")
        if fert["outside_training_range"]:
            notes.append("The nutrient need is outside the range the model was trained on ("
                         + ", ".join(fert["outside_training_range"]) + "), so treat the suggestion with extra care.")

    ph = inputs.get("ph")
    if ph not in (None, ""):
        ph = float(ph)
        if ph < 5.5:
            notes.append("Soil is strongly acidic (pH < 5.5): liming is commonly advised before fertiliser "
                         "response improves - confirm the lime requirement with a soil lab.")
        elif ph > 8.5:
            notes.append("Soil is alkaline/sodic range (pH > 8.5): gypsum and organic matter are the usual "
                         "remedies - confirm with a soil lab.")
    oc = inputs.get("organic_carbon")
    if oc not in (None, ""):
        oc = float(oc)
        oc_status = "low" if oc < 0.5 else "high" if oc > 0.75 else "medium"
        notes.append(f"Organic carbon {oc}% is {oc_status} on the Soil Health Card scale (<0.5 low, 0.5-0.75 medium, >0.75 high).")

    return {
        "category": headline,  # kept for older clients and the history list
        "fertiliser": fert, "summary": explanation,
        "status": status, "values": values, "typical": typical, "shortfall": shortfall, "need": need,
        "unit": unit, "bridge": bridge, "notes": notes, "explanation": why, "basis": basis,
        "source": {"soil_test": SHC_SOURCE,
                   "crop_profile": f"Typical level = median of '{crop}' in Crop_recommendation.csv (a dataset statistic, not an agronomic standard).",
                   "fertiliser_dataset": "Fertilizer Prediction.csv"}[basis],
        "engine": f"{c['name']} trained on {c['dataset']} ({c['rows']} rows, cross-validated accuracy "
                  f"{c['chosen']['cv_accuracy_mean'] * 100:.1f}%)",
    }
