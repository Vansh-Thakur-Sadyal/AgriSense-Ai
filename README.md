# AgriSense AI – Smart Farming Intelligence

Live: https://ai.software.microeagle.online

FastAPI backend + single-page dashboard. Every number on screen comes from a trained model, a
live public data source, or the signed-in user's own records. There is no demo data.

## What is real

| Feature | How it works | Measured quality |
|---|---|---|
| Crop recommendation | 5 classifiers compared on `Crop_recommendation.csv`; best by 5-fold CV kept | see `app/models/crop_model.json` |
| Yield prediction | LightGBM on India Agriculture Crop Production 1997–2020, predicting the correction to the 3-year district mean; temporal test (train < 2017-18) against 3 baselines; SHAP per prediction | see `app/models/yield_model.json` |
| Fertiliser | Logistic Regression on N, P, K trained on Fertilizer Prediction.csv (99 rows, 7 fertilisers; `ml/train_fertiliser.py`). Soil values go through a shortfall step first (typical level = crop median or Soil Health Card band). Names a fertiliser, never a dose | 100% (5x5 repeated CV) |
| Leaf disease | EfficientNet-B0 fine-tuned on the 55,448-image non-augmented PlantVillage-derived set (39 classes incl. "no leaf"), temperature-calibrated, refuses below a validation-chosen threshold | see `app/models/leaf_disease.json` |
| Weather | Open-Meteo live forecast; NASA POWER daily history (labelled as gridded estimates) | – |
| Soil | ISRIC SoilGrids 2.0 via the WCS map service, 6 depths with 90% ranges (labelled as modelled, not a lab test) | – |
| Assistant | Mistral chat (ministral-14b → 8b → 3b fallback), grounded in the user's farms and predictions, English/Hindi | – |

The yield dataset has no weather or soil columns, so the yield model does not use them and the UI says so.
The soil zip files supplied were SoilGrids metadata records only (no values), so soil is fetched live.

## Sign-in with e-mail codes (OTP)

Sign-up, sign-in and password reset need a 6-digit code e-mailed by the n8n workflow
`AgriSense_OTP_Delivery` (id `AgriSenseOTP0001`, webhook `/webhook/agrisense-otp`, a clone of
`Saarthi_OTP_Delivery`, e-mail branch only). Set in `config/api_keys.env`:

```
OTP_WEBHOOK_URL=http://n8n-kmar-n8n-1:5678/webhook/agrisense-otp
OTP_SHARED_SECRET=<the value in the workflow's "Shared secret matches?" node>
```

Without both values the app falls back to password-only sign-in (local development). Every
auth step is written to the `auth_events` table; uploaded leaf photos go to `uploads`.

## Layout

```
app/            FastAPI app (main.py), models/, data/production.sqlite, static/ (UI)
ml/             training scripts: train_crop.py, train_yield.py, train_leaf.py
data/raw/       datasets (not deployed)
config/         api_keys.env (MISTRAL_API_KEY) – never committed, mounted read-only in Docker
deploy/         Traefik route for the VPS
```

## Run locally

```
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --port 8150
```

Retrain: `python ml/train_crop.py`, `python ml/train_yield.py` (both evaluate on held-out data, then
refit on all rows), `python ml/train_leaf_full.py --epochs 8` (CUDA; both leaf sets, leak-guarded
evaluation, then a final fit on all 61,486 images, written to `ml/staging/`).
Report: `python docs/build_report.py` -> `docs/AgriSense_AI_Model_Report.pdf`.

## Deploy (VPS)

`/opt/stacks/agrisense`: `docker compose up -d --build`. Traefik file `deploy/agrisense.yml` goes to
`/opt/stacks/traefik/dynamic/`. User data lives in the `agrisense_agrisense_data` volume.
