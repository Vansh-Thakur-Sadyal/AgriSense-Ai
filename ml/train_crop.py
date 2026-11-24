"""Crop recommendation: compare five classifiers on Crop_recommendation.csv, keep the best.

Writes app/models/crop_model.joblib and app/models/crop_model.json (the model card).
The card is generated here - never hand-edit it.
"""
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "Crop_recommendation.csv"
OUT = ROOT / "app" / "models"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
SEED = 42


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA)
    X, y = df[FEATURES].values, df["label"].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)

    candidates = {
        "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)),
        "K-Nearest Neighbours": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5)),
        "SVM (RBF)": make_pipeline(StandardScaler(), SVC(C=10, probability=True, random_state=SEED)),
        "Random Forest": RandomForestClassifier(n_estimators=400, random_state=SEED, n_jobs=-1),
        "LightGBM": LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                                   random_state=SEED, verbose=-1),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    comparison = []
    for name, model in candidates.items():
        t0 = time.time()
        scores = cross_val_score(model, X_tr, y_tr, cv=cv, scoring="accuracy", n_jobs=1)
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        comparison.append({
            "model": name,
            "cv_accuracy_mean": round(float(scores.mean()), 4),
            "cv_accuracy_std": round(float(scores.std()), 4),
            "test_accuracy": round(float(accuracy_score(y_te, pred)), 4),
            "test_macro_f1": round(float(f1_score(y_te, pred, average="macro")), 4),
            "train_seconds": round(time.time() - t0, 2),
        })
        print(comparison[-1])

    # Selection rule declared before the runs: highest mean CV accuracy (test set only reported).
    best = max(comparison, key=lambda r: (r["cv_accuracy_mean"], -r["cv_accuracy_std"]))
    model = candidates[best["model"]]
    pred = model.predict(X_te)
    report = classification_report(y_te, pred, output_dict=True, zero_division=0)
    classes = list(model.classes_)
    cm = confusion_matrix(y_te, pred, labels=classes)

    imp = permutation_importance(model, X_te, y_te, n_repeats=10, random_state=SEED, n_jobs=1)
    importance = sorted(
        [{"feature": f, "importance": round(float(m), 4)} for f, m in zip(FEATURES, imp.importances_mean)],
        key=lambda r: -r["importance"])

    # Per-crop feature ranges from the training data: used for the suitability radar and the
    # fertiliser nutrient-gap engine. These are dataset statistics, not agronomic standards.
    profiles = {}
    for crop, g in df.groupby("label"):
        profiles[crop] = {f: {"p10": round(float(g[f].quantile(0.10)), 2),
                              "median": round(float(g[f].median()), 2),
                              "p90": round(float(g[f].quantile(0.90)), 2),
                              "min": round(float(g[f].min()), 2),
                              "max": round(float(g[f].max()), 2)} for f in FEATURES}
    feature_ranges = {f: {"min": float(df[f].min()), "max": float(df[f].max())} for f in FEATURES}

    # Final fit: the accuracy above was measured on the held-out 20%; now that it is known, the same
    # model is refit on all 2,200 rows so no supplied data is left unused.
    from sklearn.base import clone
    final = clone(candidates[best["model"]]).fit(X, y)
    joblib.dump(final, OUT / "crop_model.joblib")
    card = {
        "name": "Crop recommendation",
        "dataset": "Crop_recommendation.csv (2,200 rows, 22 crops, 100 per crop)",
        "features": FEATURES,
        "units_note": "N, P, K are the dataset's soil nutrient ratios as published (commonly read as kg/ha); "
                      "temperature degC, humidity %, rainfall mm.",
        "split": "80/20 stratified, seed 42; model chosen on 5-fold CV accuracy of the training part",
        "selected_model": best["model"],
        "deployed_fit": {"rows": int(len(df)), "note": "refit on all rows after evaluation; metrics below are "
                         "from the held-out 20% and remain the honest estimate"},
        "comparison": comparison,
        "test_accuracy": best["test_accuracy"],
        "test_macro_f1": best["test_macro_f1"],
        "per_class": {c: {k: round(float(v), 4) for k, v in report[c].items()} for c in classes},
        "classes": classes,
        "confusion_matrix": cm.tolist(),
        "permutation_importance": importance,
        "crop_profiles": profiles,
        "feature_ranges": feature_ranges,
        "trained_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    (OUT / "crop_model.json").write_text(json.dumps(card, indent=1))
    print("selected", best)


if __name__ == "__main__":
    main()
