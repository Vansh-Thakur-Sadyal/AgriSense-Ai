"""Model micro-benchmark: time each model directly (no HTTP, no database), one call at a time.

Run inside the server container so the numbers are for the production CPU:
    docker exec -i <container> python - < tests/load/model_bench.py > bench.json
Inputs are real dataset rows (bundled samples), not made-up values.
"""
import csv
import json
import random
import statistics
import time
from pathlib import Path

from app import fertiliser, ml

HERE = Path(ml.__file__).resolve().parent / "data"
rng = random.Random(7)


def timed(fn, n):
    times = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    return {"calls": n, "mean_ms": round(statistics.mean(times), 2), "p50_ms": round(times[len(times) // 2], 2),
            "p95_ms": round(times[int(len(times) * 0.95) - 1], 2), "max_ms": round(times[-1], 2),
            "per_second_one_core": round(1000 / statistics.mean(times), 1)}


crop_rows = list(csv.DictReader(open(HERE / "crop_samples.csv", encoding="utf-8")))
FEATS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
profiles = ml.card("crop_model")["crop_profiles"]
yrows = ml.prod_rows("SELECT State, District, Crop, Season, year FROM production WHERE year BETWEEN 2008 AND 2020 "
                     "AND Area >= 50 ORDER BY RANDOM() LIMIT 200")
leaf_files = sorted(p for p in (HERE / "leaf_samples").rglob("*") if p.is_file())
leaf_bytes = [p.read_bytes() for p in rng.sample(leaf_files, 20)]


def crop_once():
    r = rng.choice(crop_rows)
    ml.recommend_crop(ml.validate({k: r[k] for k in FEATS})[0])


def fert_once():
    r = rng.choice(crop_rows)
    fertiliser.recommend({"basis": "crop_profile", "crop": r["label"], "N": r["N"], "P": r["P"], "K": r["K"]}, profiles)


def yield_once():
    r = rng.choice(yrows)
    ml.predict_yield(r["State"], r["District"], r["Crop"], r["Season"], int(r["year"]), 2.0)


def leaf_once():
    ml.diagnose(rng.choice(leaf_bytes))


# warm-up: first call loads each model from disk
t0 = time.perf_counter(); crop_once(); fert_once(); yield_once(); leaf_once(); warm = (time.perf_counter() - t0) * 1000
out = {"warm_up_ms_all_models": round(warm, 1),
       "crop_recommendation": timed(crop_once, 300),
       "fertiliser": timed(fert_once, 300),
       "yield_prediction": timed(yield_once, 200),
       "leaf_disease": timed(leaf_once, 60)}
print(json.dumps(out))
