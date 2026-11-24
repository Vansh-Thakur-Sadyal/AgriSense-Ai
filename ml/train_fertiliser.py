"""Fertiliser recommendation: compare classifiers on Fertilizer Prediction.csv, keep the best.

The dataset has 99 rows, 7 fertilisers. Two feature sets are compared:
  * "N, P, K"      - the nutrient columns only
  * "all features" - plus temperature, humidity, moisture, soil type and crop type
With so few rows a single hold-out split is noisy, so model choice uses 5x5 repeated stratified
cross-validation; a 20 % hold-out is still reported. The chosen model is then refit on all 99 rows.

Writes app/models/fertiliser_model.joblib and app/models/fertiliser_model.json (the model card).
The card is generated here - never hand-edit it.
"""
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "fertiliser" / "Fertilizer_Prediction.csv"
OUT = ROOT / "app" / "models"
SEED = 42
NPK = ["N", "P", "K"]
NUM_ALL = ["N", "P", "K", "temperature", "humidity", "moisture"]
CAT_ALL = ["soil_type", "crop_type"]
RENAME = {"Temparature": "temperature", "Humidity": "humidity", "Moisture": "moisture", "Soil Type": "soil_type",
          "Crop Type": "crop_type", "Nitrogen": "N", "Potassium": "K", "Phosphorous": "P", "Fertilizer Name": "fertiliser"}

# Standard Indian fertiliser grades (N-P2O5-K2O %); what each label in the dataset means.
GRADES = {
    "Urea": {"grade": "46-0-0", "supplies": "Nitrogen only"},
    "DAP": {"grade": "18-46-0", "supplies": "Phosphorus, with some nitrogen (diammonium phosphate)"},
    "14-35-14": {"grade": "14-35-14", "supplies": "Phosphorus-rich NPK complex"},
    "28-28": {"grade": "28-28-0", "supplies": "Nitrogen and phosphorus in equal parts, no potassium"},
    "17-17-17": {"grade": "17-17-17", "supplies": "Balanced nitrogen, phosphorus and potassium"},
    "20-20": {"grade": "20-20-0", "supplies": "Nitrogen and phosphorus, no potassium"},
    "10-26-26": {"grade": "10-26-26", "supplies": "Phosphorus and potassium-rich NPK complex"},
}


def load():
    d = pd.read_csv(DATA)
    d.columns = [c.strip() for c in d.columns]
    d = d.rename(columns=RENAME)
    for c in CAT_ALL + ["fertiliser"]:
        d[c] = d[c].astype(str).str.strip()
    return d


def candidates(features):
    if features == "npk":
        pre = lambda: "passthrough"
        cols = NPK
    else:
        pre = lambda: ColumnTransformer([("num", "passthrough", NUM_ALL),
                                         ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_ALL)])
        cols = NUM_ALL + CAT_ALL
    scaled = lambda m: make_pipeline(pre(), StandardScaler(with_mean=False), m)
    return cols, {
        "Decision Tree": make_pipeline(pre(), DecisionTreeClassifier(random_state=SEED)),
        "Random Forest": make_pipeline(pre(), RandomForestClassifier(n_estimators=400, random_state=SEED)),
        "Logistic Regression": scaled(LogisticRegression(max_iter=5000)),
        "K-Nearest Neighbours": scaled(KNeighborsClassifier(n_neighbors=3)),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    y = d["fertiliser"].values
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=SEED)
    comparison, best = [], None
    for fs, label in (("npk", "N, P, K"), ("all", "all features")):
        cols, models = candidates(fs)
        X = d[cols]
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
        for name, model in models.items():
            t0 = time.time()
            s = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
            model.fit(X_tr, y_tr)
            pred = model.predict(X_te)
            row = {"model": name, "features": label, "cv_accuracy_mean": round(float(s.mean()), 4),
                   "cv_accuracy_std": round(float(s.std()), 4),
                   "holdout_accuracy": round(float(accuracy_score(y_te, pred)), 4),
                   "holdout_macro_f1": round(float(f1_score(y_te, pred, average="macro")), 4),
                   "seconds": round(time.time() - t0, 2)}
            comparison.append(row)
            print(row)
            # prefer higher CV accuracy; on a tie prefer the smaller feature set (listed first)
            if best is None or row["cv_accuracy_mean"] > best[0]["cv_accuracy_mean"] + 1e-9:
                best = (row, fs, cols)

    row, fs, cols = best
    _, models = candidates(fs)
    model = models[row["model"]]
    # hold-out confusion matrix for the chosen model, then refit on every row for deployment
    X_tr, X_te, y_tr, y_te = train_test_split(d[cols], y, test_size=0.2, stratify=y, random_state=SEED)
    model.fit(X_tr, y_tr)
    classes = sorted(set(y))
    cm = confusion_matrix(y_te, model.predict(X_te), labels=classes).tolist()

    # how much each column matters, measured on the all-features random forest
    allcols, allmodels = candidates("all")
    rf = allmodels["Random Forest"].fit(d[allcols], y)
    imp = permutation_importance(rf, d[allcols], y, n_repeats=20, random_state=SEED)
    importance = sorted(({"feature": c, "importance": round(float(m), 4)} for c, m in zip(allcols, imp.importances_mean)),
                        key=lambda r: -r["importance"])

    model.fit(d[cols], y)
    joblib.dump(model, OUT / "fertiliser_model.joblib")
    ranges = {c: {"min": float(d[c].min()), "max": float(d[c].max())} for c in NUM_ALL}
    card = {
        "name": f"{row['model']} on {row['features']}",
        "dataset": "Fertilizer Prediction.csv",
        "rows": int(len(d)),
        "classes": classes,
        "class_counts": {k: int(v) for k, v in d["fertiliser"].value_counts().items()},
        "grades": GRADES,
        "features": cols,
        "chosen": row,
        "comparison": comparison,
        "holdout_confusion_matrix": {"labels": classes, "matrix": cm},
        "permutation_importance_all_features": importance,
        "ranges": ranges,
        "need_profile": {k: {"min": ranges[k]["min"], "max": ranges[k]["max"]} for k in NPK},
        "soil_types": sorted(d["soil_type"].unique()),
        "crop_types": sorted(d["crop_type"].unique()),
        "notes": ["99 rows: accuracy figures carry wide uncertainty.",
                  "In this dataset the fertiliser is decided by N, P and K; weather, moisture, soil and crop type "
                  "add little (see permutation importance).",
                  "N, P and K here describe the nutrient to be supplied (Urea rows have high N and zero P and K), "
                  "on the dataset's own scale - not kg/ha and not the crop dataset's scale."],
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "seed": SEED,
    }
    (OUT / "fertiliser_model.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print("chosen:", card["name"], row["cv_accuracy_mean"])
    print("importance:", importance)


if __name__ == "__main__":
    main()
