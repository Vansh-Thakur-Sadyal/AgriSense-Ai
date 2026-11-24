"""Farms, the four decision tools, history, reports and data isolation."""
import io
import os
import sqlite3
from pathlib import Path

from PIL import Image

from conftest import leaf_image, new_client, signup

DB = Path(os.environ["AGRISENSE_STORAGE"]) / "agrisense.db"
RICE = {"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82, "ph": 6.5, "rainfall": 203}


# ---------------- farms ----------------
def test_tc020_add_farm(farm):
    """TC-020 | Farm management | Add a farm with a map location
    pre: Signed in
    data: North Field, Punjab / LUDHIANA, 30.90 N 75.85 E, 3 ha, Loamy
    steps: 1. Fill the Add farm form. 2. Save. 3. Open Farm Management.
    expected: Farm saved and listed with the same values."""
    c, f = farm
    assert f["name"] == "North Field" and f["area_ha"] == 3
    assert [x["name"] for x in c.get("/api/farms").json()["farms"]] == ["North Field"]


def test_tc021_farm_requires_name(user):
    """TC-021 | Farm management | Farm name is required
    pre: Signed in
    data: empty name
    steps: 1. Save a farm without a name.
    expected: HTTP 422, field error on name."""
    c, _ = user
    r = c.post("/api/farms", json={"name": " ", "state": "Punjab"})
    assert r.status_code == 422 and "name" in r.json()["fields"]


def test_tc022_farm_coordinates_inside_india(user):
    """TC-022 | Farm management | Coordinates outside India are refused
    pre: Signed in
    data: lat 51.5, lon -0.12 (London)
    steps: 1. Save a farm with London's coordinates.
    expected: HTTP 422 "Coordinates must be inside India"."""
    c, _ = user
    r = c.post("/api/farms", json={"name": "Abroad", "lat": 51.5, "lon": -0.12})
    assert r.status_code == 422 and "India" in r.json()["error"]


def test_tc023_edit_and_delete_farm(farm):
    """TC-023 | Farm management | Edit and delete a farm
    pre: A farm exists
    data: new area 4.5 ha
    steps: 1. Edit the farm area. 2. Delete the farm. 3. List farms.
    expected: Area updated to 4.5; after delete the list is empty."""
    c, f = farm
    r = c.put(f"/api/farms/{f['id']}", json={**{k: f[k] for k in ("name", "state", "district", "lat", "lon")}, "area_ha": 4.5})
    assert r.json()["farm"]["area_ha"] == 4.5
    assert c.delete(f"/api/farms/{f['id']}").json()["ok"]
    assert c.get("/api/farms").json()["farms"] == []


# ---------------- crop ----------------
def test_tc024_crop_recommendation(user):
    """TC-024 | Crop recommendation | Recommend a crop for rice-like conditions
    pre: Signed in
    data: N 90, P 42, K 43, 21 degC, 82% humidity, pH 6.5, 203 mm
    steps: 1. Enter the values. 2. Press Predict Suitable Crop.
    expected: Crop "rice" with confidence >= 0.9, top alternatives listed, saved to history."""
    c, _ = user
    r = c.post("/api/crop/recommend", json=RICE).json()
    assert r["crop"] == "rice" and r["confidence"] >= 0.9 and len(r["top"]) >= 3
    assert c.get("/api/predictions?kind=crop").json()["predictions"][0]["id"] == r["id"]


def test_tc025_crop_different_inputs(user):
    """TC-025 | Crop recommendation | Dry, low-humidity input gives a different crop
    pre: Signed in
    data: N 20, P 60, K 20, 28 degC, 40% humidity, pH 6.5, 60 mm
    steps: 1. Enter the values. 2. Predict.
    expected: A crop other than rice; probabilities of the top list sum to <= 1."""
    c, _ = user
    r = c.post("/api/crop/recommend", json={"N": 20, "P": 60, "K": 20, "temperature": 28, "humidity": 40,
                                             "ph": 6.5, "rainfall": 60}).json()
    assert r["crop"] != "rice" and sum(t["probability"] for t in r["top"]) <= 1.0001


def test_tc026_crop_validation(user):
    """TC-026 | Crop recommendation | Out-of-range and missing inputs
    pre: Signed in
    data: pH 15, humidity missing
    steps: 1. Enter pH 15 and leave humidity empty. 2. Predict.
    expected: HTTP 422 with field errors for ph and humidity; nothing saved."""
    c, _ = user
    bad = {**RICE, "ph": 15}
    bad.pop("humidity")
    r = c.post("/api/crop/recommend", json=bad)
    assert r.status_code == 422 and {"ph", "humidity"} <= set(r.json()["fields"])


# ---------------- yield ----------------
def test_tc027_yield_prediction(user):
    """TC-027 | Yield prediction | Wheat, Rabi, Ludhiana, 3 ha
    pre: Signed in
    data: Punjab, LUDHIANA, Wheat, Rabi, 2021, 3 ha
    steps: 1. Choose the values. 2. Press Predict Crop Yield.
    expected: Yield between 3 and 7 t/ha, 80% interval contains it, production = yield x 3 ha, SHAP contributions returned."""
    c, _ = user
    r = c.post("/api/yield/predict", json={"state": "Punjab", "district": "LUDHIANA", "crop": "Wheat",
                                            "season": "Rabi", "year": 2021, "area_ha": 3}).json()
    lo, hi = r["interval_80"]
    assert 3 < r["yield_t_ha"] < 7 and lo <= r["yield_t_ha"] <= hi
    assert abs(r["production_t"] - r["yield_t_ha"] * 3) < 0.1 and len(r["contributions"]) > 0


def test_tc028_yield_area_scales_production_only(user):
    """TC-028 | Yield prediction | Farm area changes production, not yield per hectare
    pre: Signed in
    data: same inputs with 1 ha and 10 ha
    steps: 1. Predict with 1 ha. 2. Predict with 10 ha.
    expected: Same t/ha; production 10 times larger."""
    c, _ = user
    base = {"state": "Punjab", "district": "LUDHIANA", "crop": "Wheat", "season": "Rabi", "year": 2021}
    a = c.post("/api/yield/predict", json={**base, "area_ha": 1}).json()
    b = c.post("/api/yield/predict", json={**base, "area_ha": 10}).json()
    assert a["yield_t_ha"] == b["yield_t_ha"] and abs(b["production_t"] - 10 * a["production_t"]) < 0.2


def test_tc029_yield_validation(user):
    """TC-029 | Yield prediction | Required fields, year and area checks
    pre: Signed in
    data: no crop, year 1990, area 0
    steps: 1. Submit the form.
    expected: HTTP 422 with errors on crop, year and area_ha."""
    c, _ = user
    r = c.post("/api/yield/predict", json={"state": "Punjab", "district": "LUDHIANA", "season": "Rabi",
                                            "year": 1990, "area_ha": 0})
    assert r.status_code == 422 and {"crop", "year", "area_ha"} <= set(r.json()["fields"])


def test_tc030_yield_options(user):
    """TC-030 | Yield prediction | Drop-down options come from the dataset
    pre: Signed in
    data: -
    steps: 1. Open the Yield page (loads /api/yield/options and districts of Punjab).
    expected: States include Punjab, crops include Wheat and Rice, Punjab districts include LUDHIANA."""
    c, _ = user
    o = c.get("/api/yield/options").json()
    assert "Punjab" in o["State"] and {"Wheat", "Rice"} <= set(o["Crop"])
    assert "LUDHIANA" in str(c.get("/api/yield/districts?state=Punjab").json())


# ---------------- fertiliser ----------------
def test_tc031_fertiliser_soil_test(user):
    """TC-031 | Fertiliser | Soil-test numbers (kg/ha) -> shortfall -> fertiliser named by the ML model
    pre: Signed in
    data: rice, N 210, P 18, K 95 (kg/ha)
    steps: 1. Choose "Soil test report". 2. Enter the values. 3. Get Recommendation.
    expected: N and K short, P adequate against the Soil Health Card medium band; the named fertiliser supplies N and K; no dose (kg) anywhere."""
    c, _ = user
    r = c.post("/api/fertiliser", json={"basis": "soil_test", "crop": "rice", "N": 210, "P": 18, "K": 95}).json()
    assert r["status"] == {"N": "short", "P": "adequate", "K": "short"}
    f = r["fertiliser"]
    assert f["name"] in {"17-17-17", "14-35-14", "10-26-26"} and r["category"] == f["name"]
    assert 0 < f["confidence"] <= 1 and f["grade"].count("-") == 2
    assert "kg/ha" not in " ".join(r["notes"]) + r["summary"]


def test_tc032_fertiliser_all_adequate(user):
    """TC-032 | Fertiliser | Balanced soil needs no corrective fertiliser
    pre: Signed in
    data: wheat, N 400, P 18, K 200
    steps: 1. Enter the values. 2. Get Recommendation.
    expected: N, P, K all adequate; no fertiliser is named and the model is not asked."""
    c, _ = user
    r = c.post("/api/fertiliser", json={"basis": "soil_test", "crop": "wheat", "N": 400, "P": 18, "K": 200}).json()
    assert set(r["status"].values()) == {"adequate"}
    assert r["category"] == "No fertiliser needed" and r["fertiliser"]["name"] is None


def test_tc033_fertiliser_validation(user):
    """TC-033 | Fertiliser | Validation of nutrients, pH and crop
    pre: Signed in
    data: N missing, pH 12, no crop
    steps: 1. Submit the form.
    expected: HTTP 422 with errors on N, ph and crop."""
    c, _ = user
    r = c.post("/api/fertiliser", json={"basis": "soil_test", "P": 18, "K": 95, "ph": 12})
    assert r.status_code == 422 and {"N", "ph", "crop"} <= set(r.json()["fields"])


# ---------------- disease ----------------
def _upload(c, data, name="leaf.jpg", ctype="image/jpeg"):
    return c.post("/api/disease", files={"image": (name, data, ctype)})


def test_tc034_disease_detected(user):
    """TC-034 | Disease detection | Tomato early blight leaf
    pre: Signed in
    data: dataset image Tomato___Early_blight #5
    steps: 1. Upload the photo. 2. Press Analyse Image.
    expected: Verdict diseased, class Tomato___Early_blight above the 96% threshold, cause/symptoms/next steps shown."""
    c, _ = user
    r = _upload(c, leaf_image("Tomato___Early_blight", 5)).json()
    assert r["verdict"] == "diseased" and r["best"]["class"] == "Tomato___Early_blight"
    assert r["best"]["probability"] >= r["threshold"] and r["info"]["cause"]


def test_tc035_disease_healthy(user):
    """TC-035 | Disease detection | Healthy potato leaf
    pre: Signed in
    data: dataset image Potato___healthy #3
    steps: 1. Upload. 2. Analyse.
    expected: Verdict healthy, class Potato___healthy."""
    c, _ = user
    r = _upload(c, leaf_image("Potato___healthy", 3)).json()
    assert r["verdict"] == "healthy" and r["best"]["class"] == "Potato___healthy"


def test_tc036_disease_refuses_unclear(user):
    """TC-036 | Disease detection | Blank grey image is not given a disease name
    pre: Signed in
    data: 256x256 plain grey PNG
    steps: 1. Upload. 2. Analyse.
    expected: Verdict "uncertain" or "no_leaf"; saved with status "needs review"."""
    c, _ = user
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (120, 120, 120)).save(buf, "PNG")
    r = _upload(c, buf.getvalue(), "grey.png", "image/png").json()
    assert r["verdict"] in ("uncertain", "no_leaf")
    assert c.get(f"/api/predictions/{r['id']}").json()["status"] == "needs review"


def test_tc037_disease_file_type(user):
    """TC-037 | Disease detection | Only JPG/PNG accepted
    pre: Signed in
    data: a .txt file
    steps: 1. Upload a text file.
    expected: HTTP 415 "Upload a JPG or PNG image"."""
    c, _ = user
    assert _upload(c, b"hello", "notes.txt", "text/plain").status_code == 415


def test_tc038_disease_photo_stored(user):
    """TC-038 | Data storage | Uploaded leaf photo is stored with its prediction
    pre: Signed in
    data: dataset image Apple___Apple_scab #0
    steps: 1. Upload and analyse. 2. Read the uploads table. 3. Download it via /api/uploads/{id}.
    expected: One uploads row linked to the prediction with the same bytes (SHA-256)."""
    c, _ = user
    data = leaf_image("Apple___Apple_scab", 0)
    pid = _upload(c, data).json()["id"]
    row = sqlite3.connect(DB).execute("select id, size from uploads where prediction_id=?", (pid,)).fetchone()
    assert row and row[1] == len(data)
    assert c.get(f"/api/uploads/{row[0]}").content == data


# ---------------- history, overview, reports ----------------
def test_tc039_history_filters(user):
    """TC-039 | Prediction history | Filter by type
    pre: Signed in, one crop and one fertiliser prediction
    data: kind=crop
    steps: 1. Run a crop and a fertiliser prediction. 2. Filter history by Crop.
    expected: Only the crop prediction is listed."""
    c, _ = user
    c.post("/api/crop/recommend", json=RICE)
    c.post("/api/fertiliser", json={"basis": "soil_test", "crop": "rice", "N": 210, "P": 18, "K": 95})
    kinds = {p["kind"] for p in c.get("/api/predictions?kind=crop").json()["predictions"]}
    assert kinds == {"crop"}


def test_tc040_delete_prediction(user):
    """TC-040 | Prediction history | Delete a prediction
    pre: One prediction exists
    data: -
    steps: 1. Delete it from history. 2. Reload history.
    expected: History is empty."""
    c, _ = user
    pid = c.post("/api/crop/recommend", json=RICE).json()["id"]
    c.delete(f"/api/predictions/{pid}")
    assert c.get("/api/predictions").json()["predictions"] == []


def test_tc041_overview_kpis(user):
    """TC-041 | Overview | KPI counters follow the user's activity
    pre: Signed in
    data: 2 crop predictions
    steps: 1. Run 2 crop predictions. 2. Open Overview.
    expected: kpis.crop = 2 and total = 2; recent list has 2 rows."""
    c, _ = user
    c.post("/api/crop/recommend", json=RICE)
    c.post("/api/crop/recommend", json=RICE)
    o = c.get("/api/overview").json()
    assert o["kpis"]["crop"] == 2 and o["kpis"]["total"] == 2 and len(o["recent"]) == 2


def test_tc042_reports_pdf_csv(user):
    """TC-042 | Reports | Export predictions as PDF and CSV
    pre: One prediction exists
    data: -
    steps: 1. Reports & Analytics -> PDF. 2. -> CSV.
    expected: PDF starts with %PDF; CSV has a header row and the prediction row."""
    c, _ = user
    c.post("/api/crop/recommend", json=RICE)
    pdf = c.get("/api/reports/pdf")
    csv = c.get("/api/reports/csv")
    assert pdf.content[:4] == b"%PDF" and csv.text.count("\n") >= 2 and "rice" in csv.text.lower()


def test_tc043_analytics_series(user):
    """TC-043 | Analytics | District production series from the government dataset
    pre: Signed in
    data: state Punjab, crop Wheat
    steps: 1. Open Overview analytics with Punjab / Wheat.
    expected: More than 10 yearly points."""
    c, _ = user
    assert len(c.get("/api/analytics/production?state=Punjab&crop=Wheat").json()["series"]) > 10


# ---------------- security ----------------
def test_tc044_requires_sign_in():
    """TC-044 | Security | Protected endpoints need a session
    pre: Not signed in
    data: -
    steps: 1. Call farms, predictions, crop, disease and chat endpoints without a session.
    expected: HTTP 401 for every one."""
    c = new_client()
    assert c.get("/api/farms").status_code == 401
    assert c.get("/api/predictions").status_code == 401
    assert c.post("/api/crop/recommend", json=RICE).status_code == 401
    assert c.post("/api/chat", data={"message": "hi"}).status_code == 401


def test_tc045_user_isolation(farm):
    """TC-045 | Security | One user cannot read or change another user's data
    pre: User A has a farm, a prediction and an upload
    data: User B's session
    steps: 1. As B, open A's farm, prediction and upload by id. 2. As B, edit and delete A's farm.
    expected: HTTP 404 for every request; A's data unchanged."""
    a, f = farm
    pid = _upload(a, leaf_image("Tomato___Early_blight", 1)).json()["id"]
    uid = sqlite3.connect(DB).execute("select id from uploads where prediction_id=?", (pid,)).fetchone()[0]
    b, _ = signup()
    assert b.get(f"/api/farms/{f['id']}").status_code == 404
    assert b.get(f"/api/predictions/{pid}").status_code == 404
    assert b.get(f"/api/uploads/{uid}").status_code == 404
    assert b.put(f"/api/farms/{f['id']}", json={"name": "hijack"}).status_code == 404
    assert b.delete(f"/api/farms/{f['id']}").status_code == 404
    assert a.get(f"/api/farms/{f['id']}").json()["farm"]["name"] == "North Field"


def test_tc046_session_cookie_flags():
    """TC-046 | Security | Session cookie is HttpOnly and SameSite=Lax
    pre: -
    data: -
    steps: 1. Complete a sign-in. 2. Inspect the Set-Cookie header.
    expected: Cookie agrisense_session with HttpOnly and SameSite=lax (Secure is added in production)."""
    c = new_client()
    r = c.post("/api/auth/register", json={"name": "Cookie Test", "email": "tc046@agrisense.test", "password": "Farm12345"})
    from conftest import last_code
    r = c.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": last_code("tc046@agrisense.test")})
    sc = r.headers["set-cookie"].lower()
    assert "agrisense_session=" in sc and "httponly" in sc and "samesite=lax" in sc


def test_tc047_status_and_health():
    """TC-047 | System | Health check and model status
    pre: -
    data: -
    steps: 1. GET /healthz. 2. GET /api/status.
    expected: healthz 200; all four tools ready; otp true."""
    c = new_client()
    assert c.get("/healthz").status_code == 200
    s = c.get("/api/status").json()
    assert all(m["ready"] for m in s["models"].values()) and s["otp"] is True


def test_tc069_static_assets_self_hosted():
    """TC-069 | System | Fonts and front-end libraries are served by the app with correct types
    pre: -
    data: -
    steps: 1. GET / and inspect asset links. 2. GET one icon font file, the font stylesheet and the Tailwind script.
    expected: No Google Fonts or CDN links in the page; font served as font/woff2, CSS as text/css, script as text/javascript."""
    import re
    c = new_client()
    html = c.get("/").text
    assert "fonts.googleapis" not in html.split("-->")[-1] and "cdn.tailwindcss" not in html and "cdnjs" not in html
    css = c.get("/fonts/fonts.css")
    assert css.headers["content-type"].startswith("text/css")
    font = re.search(r"/fonts/[a-f0-9]+\.woff2", css.text).group(0)
    assert c.get(font).headers["content-type"] == "font/woff2"
    assert "javascript" in c.get("/vendor/tailwind-3.4.16.js").headers["content-type"]


def test_tc070_dataset_samples(user):
    """TC-070 | Automatic input | Random real samples from the datasets
    pre: Signed in
    data: -
    steps: 1. Request 6 crop samples. 2. Request a yield sample and predict with it. 3. Request a leaf sample and download it. 4. Try a path outside the sample folder.
    expected: Crop samples are real CSV rows (valid label, 7 values) and not all the same; the yield sample predicts without error and carries the recorded yield; the leaf photo downloads as an image; the outside path is refused (404)."""
    c, _ = user
    rows = [c.get("/api/samples/crop").json() for _ in range(6)]
    assert all(len(r["values"]) == 7 and r["label"] for r in rows) and len({r["row"] for r in rows}) > 1
    y = c.get("/api/samples/yield").json()
    p = c.post("/api/yield/predict", json={k: y[k] for k in ("state", "district", "crop", "season", "year", "area_ha")})
    assert p.status_code == 200 and y["recorded_yield_t_ha"] > 0
    s = c.get("/api/samples/leaf").json()
    img = c.get(s["url"])
    assert img.status_code == 200 and img.headers["content-type"].startswith("image/") and len(img.content) > 1000
    assert c.get("/api/samples/leaf/..%2F..%2Fmodels/crop_model.json").status_code == 404


def test_tc071_crop_to_fertiliser_chain(user):
    """TC-071 | Automatic input | Dataset sample -> crop model -> fertiliser for the recommended crop
    pre: Signed in
    data: one random crop sample
    steps: 1. Take a crop sample. 2. Run crop recommendation on it. 3. Run the fertiliser check for the recommended crop on the same N, P, K (dataset scale).
    expected: Both results are saved; the fertiliser result rates N, P and K for the recommended crop and names a fertiliser (or says none is needed)."""
    c, _ = user
    s = c.get("/api/samples/crop").json()
    cr = c.post("/api/crop/recommend", json=s["values"]).json()
    fe = c.post("/api/fertiliser", json={"basis": "crop_profile", "crop": cr["crop"], **{k: s["values"][k] for k in ("N", "P", "K", "ph")}}).json()
    assert set(fe["status"]) == {"N", "P", "K"} and fe["category"]
    short = {n for n, v in fe["need"].items() if v > 0}
    assert (fe["fertiliser"]["name"] is None) == (not short)
    kinds = [p["kind"] for p in c.get("/api/predictions").json()["predictions"]]
    assert kinds.count("crop") == 1 and kinds.count("fertiliser") == 1


def test_tc077_translation_api_and_cache():
    """TC-077 | Translation | Azure-backed UI translation is cached and validated
    pre: AZURE_TRANSLATOR_KEY configured
    data: "Crop Recommendation", "Predict Suitable Crop", "42" into Tamil; language "xx"
    steps: 1. List languages. 2. Translate into Tamil. 3. Repeat the request. 4. Ask for an unsupported language.
    expected: 15 languages (English + 14); Tamil text returned and "42" skipped; the repeat is served from the translations table; unsupported language gives HTTP 422."""
    import os
    import sqlite3
    import time
    from pathlib import Path
    c = new_client()
    langs = c.get("/api/i18n/languages").json()
    assert len(langs["languages"]) == 15 and langs["configured"]
    r = c.post("/api/i18n/translate", json={"lang": "ta", "texts": ["Crop Recommendation", "Predict Suitable Crop", "42"]}).json()["translations"]
    assert set(r) == {"Crop Recommendation", "Predict Suitable Crop"} and all(any("\u0b80" <= ch <= "\u0bff" for ch in v) for v in r.values())
    db = sqlite3.connect(Path(os.environ["AGRISENSE_STORAGE"]) / "agrisense.db")
    assert db.execute("select count(*) from translations where lang='ta' and src='Crop Recommendation'").fetchone()[0] == 1
    t = time.time()
    again = c.post("/api/i18n/translate", json={"lang": "ta", "texts": ["Crop Recommendation"]}).json()["translations"]
    assert again["Crop Recommendation"] == r["Crop Recommendation"] and time.time() - t < 0.5
    assert c.post("/api/i18n/translate", json={"lang": "xx", "texts": ["Hello there"]}).status_code == 422


def test_tc078_profile_accepts_all_languages(user):
    """TC-078 | Profile | Every offered interface language can be saved on the profile
    pre: Signed in
    data: all 15 language codes, then "fr"
    steps: 1. Save each language on the profile. 2. Try an unsupported code.
    expected: All 15 are stored; "fr" gives HTTP 422."""
    c, _ = user
    codes = [l["code"] for l in c.get("/api/i18n/languages").json()["languages"]]
    for code in codes:
        assert c.put("/api/me", json={"language": code}).json()["user"]["language"] == code
    assert c.put("/api/me", json={"language": "fr"}).status_code == 422


def test_tc086_fertiliser_model_card(user):
    """TC-086 | Fertiliser | The fertiliser model is trained on Fertilizer Prediction.csv and reproduces it
    pre: fertiliser_model.json/.joblib built by ml/train_fertiliser.py
    data: all 99 rows of the dataset, entered on its own scale
    steps: 1. GET /api/status and /api/models/fertiliser. 2. Send every dataset row with basis "fertiliser_dataset".
    expected: Model ready; 99 rows, 7 fertilisers, cross-validated accuracy >= 95%; every row returns the fertiliser it records."""
    import csv
    from app.main import HERE
    c, _ = user
    st = c.get("/api/status").json()["models"]["fertiliser"]
    assert st["ready"] and st["cv_accuracy"] >= 0.95
    card = c.get("/api/models/fertiliser").json()
    assert card["rows"] == 99 and len(card["classes"]) == 7
    rows = [{k.strip(): v for k, v in r.items()} for r in csv.DictReader(open(HERE / "data" / "fertiliser_samples.csv", encoding="utf-8"))]
    from app import fertiliser
    for r in rows:
        out = fertiliser.recommend({"basis": "fertiliser_dataset", "crop": r["Crop Type"], "N": r["Nitrogen"],
                                    "P": r["Phosphorous"], "K": r["Potassium"]}, {})
        assert out["category"] == r["Fertilizer Name"].strip()


def test_tc087_fertiliser_matches_shortfall(user):
    """TC-087 | Fertiliser | The named fertiliser supplies the nutrient that is short
    pre: Signed in
    data: rice (typical N 80, P 47, K 40 in the crop dataset): only N short; only P short; P and K short
    steps: 1. Send each case with basis "crop_profile".
    expected: N only -> Urea; P only -> DAP; P and K -> a complex that supplies both; every result names its grade."""
    c, _ = user
    post = lambda n, p, k: c.post("/api/fertiliser", json={"basis": "crop_profile", "crop": "rice", "N": n, "P": p, "K": k}).json()
    assert post(20, 60, 50)["fertiliser"]["name"] == "Urea"
    assert post(90, 20, 50)["fertiliser"]["name"] == "DAP"
    r = post(90, 20, 20)
    assert r["fertiliser"]["name"] in {"14-35-14", "10-26-26", "17-17-17"} and r["bridge"]


def test_tc088_fertiliser_dataset_sample(user):
    """TC-088 | Automatic input | Random real row of Fertilizer Prediction.csv
    pre: Signed in
    data: -
    steps: 1. GET /api/samples/fertiliser. 2. Send its N, P, K with basis "fertiliser_dataset".
    expected: The row carries the fertiliser it records; the model names the same fertiliser."""
    c, _ = user
    s = c.get("/api/samples/fertiliser").json()
    assert s["of"] == 99 and s["label"]
    r = c.post("/api/fertiliser", json={"basis": "fertiliser_dataset", "crop": s["crop_type"], **{k: s["values"][k] for k in "NPK"}}).json()
    assert r["fertiliser"]["name"] == s["label"]
