"""AgriSense AI - FastAPI backend + static dashboard."""
import csv
import datetime as dt
import io
import json
import mimetypes
import os
import random
from functools import lru_cache
import re
import time
from pathlib import Path

# python:3.12-slim has no /etc/mime.types, so self-hosted fonts went out as text/plain.
for _ext, _type in {".woff2": "font/woff2", ".woff": "font/woff", ".svg": "image/svg+xml", ".js": "text/javascript",
                    ".css": "text/css", ".png": "image/png", ".json": "application/json"}.items():
    mimetypes.add_type(_type, _ext)

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import assistant, db, external, fertiliser, ml, otp, translate
from .disease_info import INFO

HERE = Path(__file__).resolve().parent
ENV = HERE.parent / "config" / "api_keys.env"
if ENV.exists():
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

COOKIE = "agrisense_session"
SECURE = os.environ.get("AGRISENSE_SECURE_COOKIE", "0") == "1"
app = FastAPI(title="AgriSense AI", docs_url="/api/docs", openapi_url="/api/openapi.json")
db.init()


def err(status, msg, **extra):
    raise HTTPException(status, {"error": msg, **extra})


@app.exception_handler(HTTPException)
async def http_exc(_, e: HTTPException):
    body = e.detail if isinstance(e.detail, dict) else {"error": str(e.detail)}
    return JSONResponse(body, status_code=e.status_code)


def session_token(request: Request):
    """Browser: HttpOnly cookie. Mobile app: `Authorization: Bearer <token>` (same session table, same rules)."""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(COOKIE)


def is_app(request: Request):
    return (request.headers.get("x-client") or "").lower() == "android"


def user(request: Request):
    u = db.session_user(session_token(request))
    if not u:
        err(401, "Please sign in")
    return u


def public_user(u):
    return {k: u[k] for k in ("id", "name", "email", "phone", "state", "district", "role", "language",
                              "units", "notify_weather", "share_farm_with_assistant")}


def save_prediction(u, kind, inputs, result, summary, crop=None, confidence=None, farm_id=None, version="", status="completed"):
    pid = db.run("INSERT INTO predictions(user_id,farm_id,kind,inputs,result,summary,crop,confidence,model_version,"
                 "status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                 (u["id"], farm_id, kind, json.dumps(inputs), json.dumps(result), summary, crop, confidence,
                  version, status, time.time()))
    return pid


def own_farm(u, farm_id):
    if farm_id in (None, "", 0, "0"):
        return None
    f = db.one("SELECT * FROM farms WHERE id=? AND user_id=?", (int(farm_id), u["id"]))
    if not f:
        err(404, "Farm not found")
    return f


# ---------------- auth ----------------
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE = re.compile(r"^\+?\d{10,13}$")


def _ip(request):
    return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()


def _otp_call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except otp.OTPError as e:
        err(e.status, e.msg)


def _sign_in(u, response, request, days, how):
    tok = db.new_session(u["id"], days)
    db.run("UPDATE users SET last_login_at=? WHERE id=?", (time.time(), u["id"]))
    db.log_event("login", u["id"], u["email"], how, request)
    out = {"user": public_user(db.one("SELECT * FROM users WHERE id=?", (u["id"],)))}
    if is_app(request):          # the Android app keeps the token in encrypted storage instead of a cookie
        out["token"] = tok
        out["expires_in_days"] = days
    else:
        response.set_cookie(COOKIE, tok, max_age=days * 86400, httponly=True, samesite="lax", secure=SECURE)
    return out


def _password_problem(pw):
    if len(pw) < 8 or not re.search(r"\d", pw) or not re.search(r"[A-Za-z]", pw):
        return "At least 8 characters with letters and numbers"
    return None


# ---------------- interface translation (Azure AI Translator + cache) ----------------
@app.get("/api/i18n/languages")
def i18n_languages():
    return {"languages": translate.languages(), "configured": translate.configured()}


@app.post("/api/i18n/translate")
async def i18n_translate(request: Request):
    """Public (the sign-in page is translated too) but rate-limited, budget-capped and cached."""
    b = await request.json()
    texts = b.get("texts") or []
    if not isinstance(texts, list):
        err(422, "texts must be a list")
    try:
        return {"lang": b.get("lang"), "translations": translate.translate([str(t) for t in texts], b.get("lang") or "", _ip(request))}
    except translate.TranslateError as e:
        err(e.status, e.msg)


@app.post("/api/auth/register")
async def register(request: Request, response: Response):
    b = await request.json()
    name = (b.get("name") or "").strip()
    email = (b.get("email") or "").strip().lower() or None
    phone = re.sub(r"[\s-]", "", b.get("phone") or "") or None
    pw = b.get("password") or ""
    fields = {}
    if len(name) < 2:
        fields["name"] = "Enter your full name"
    if otp.enabled() and not email:
        fields["email"] = "Email is required (we send a verification code to it)"
    elif not email and not phone:
        fields["email"] = "Email or phone is required"
    if email and not EMAIL.match(email):
        fields["email"] = "Enter a valid email"
    if phone and not PHONE.match(phone):
        fields["phone"] = "Enter a 10-13 digit phone number"
    if _password_problem(pw):
        fields["password"] = _password_problem(pw)
    role = b.get("role") if b.get("role") in ("farmer", "agri_officer", "researcher") else "farmer"
    if fields:
        err(422, "Please fix the highlighted fields", fields=fields)
    if email and db.one("SELECT id FROM users WHERE email=?", (email,)):
        err(409, "An account with this email already exists", fields={"email": "Already registered"})
    if phone and db.one("SELECT id FROM users WHERE phone=?", (phone,)):
        err(409, "An account with this phone already exists", fields={"phone": "Already registered"})
    record = {"name": name, "email": email, "phone": phone, "pw_hash": db.hash_pw(pw), "state": b.get("state"),
              "district": b.get("district"), "role": role}
    if otp.enabled():
        db.log_event("signup_started", None, email, None, request)
        return _otp_call(otp.start, email, "signup", None, record, _ip(request))
    return _create_user(record, response, request, verified=False)


def _create_user(r, response, request, verified):
    if r["email"] and db.one("SELECT id FROM users WHERE email=?", (r["email"],)):
        err(409, "An account with this email already exists", fields={"email": "Already registered"})
    if r["phone"] and db.one("SELECT id FROM users WHERE phone=?", (r["phone"],)):
        err(409, "An account with this phone already exists", fields={"phone": "Already registered"})
    uid = db.run("INSERT INTO users(name,email,phone,pw_hash,state,district,role,created_at,email_verified_at) "
                 "VALUES(?,?,?,?,?,?,?,?,?)", (r["name"], r["email"], r["phone"], r["pw_hash"], r["state"],
                                               r["district"], r["role"], time.time(), time.time() if verified else None))
    db.log_event("signup_completed", uid, r["email"], "email verified" if verified else "no OTP (dev)", request)
    return _sign_in(db.one("SELECT * FROM users WHERE id=?", (uid,)), response, request, 14, "after sign-up")


@app.post("/api/auth/login")
async def login(request: Request, response: Response):
    b = await request.json()
    ident = (b.get("identifier") or "").strip().lower()
    ph = re.sub(r"[\s-]", "", ident)
    u = db.one("SELECT * FROM users WHERE email=? OR phone=?", (ident, ph))
    if not u or not db.check_pw(b.get("password") or "", u["pw_hash"]):
        db.log_event("login_failed", u and u["id"], ident if "@" in ident else None, "wrong password", request)
        err(401, "Email/phone or password is incorrect")
    days = 30 if b.get("remember") else 1
    if not otp.enabled():
        return _sign_in(u, response, request, days, "password (OTP off)")
    if not u["email"]:
        err(403, "This account has no e-mail address, so a sign-in code cannot be sent. Ask the administrator.")
    db.log_event("login_password_ok", u["id"], u["email"], "code requested", request)
    return _otp_call(otp.start, u["email"], "login", u["id"], {"days": days}, _ip(request))


@app.post("/api/auth/otp/verify")
async def otp_verify(request: Request, response: Response):
    b = await request.json()
    c = _otp_call(otp.verify, b.get("challenge_id"), b.get("code"))
    if c["purpose"] == "signup":
        return _create_user(c["payload"], response, request, verified=True)
    u = db.one("SELECT * FROM users WHERE id=?", (c["user_id"],))
    if not u:
        err(410, "This account no longer exists")
    if not u["email_verified_at"]:
        db.run("UPDATE users SET email_verified_at=? WHERE id=?", (time.time(), u["id"]))
    if c["purpose"] == "login":
        return _sign_in(u, response, request, int(c["payload"].get("days", 1)), "password + e-mail code")
    # reset: the new password was validated and hashed before the code was sent
    db.run("UPDATE users SET pw_hash=? WHERE id=?", (c["payload"]["pw_hash"], u["id"]))
    db.run("DELETE FROM sessions WHERE user_id=?", (u["id"],))
    db.log_event("password_reset", u["id"], u["email"], "via e-mail code", request)
    return _sign_in(u, response, request, 1, "after password reset")


@app.post("/api/auth/otp/resend")
async def otp_resend(request: Request):
    b = await request.json()
    return _otp_call(otp.resend, b.get("challenge_id") or "")


@app.post("/api/auth/forgot")
async def forgot(request: Request):
    """Same answer whether or not the address exists, so it cannot be used to discover accounts."""
    if not otp.enabled():
        err(503, "Password reset needs the e-mail service, which is not configured here.")
    b = await request.json()
    email = (b.get("email") or "").strip().lower()
    pw = b.get("new_password") or ""
    if not EMAIL.match(email):
        err(422, "Enter a valid email", fields={"email": "Enter a valid email"})
    if _password_problem(pw):
        err(422, "Please fix the highlighted fields", fields={"new_password": _password_problem(pw)})
    u = db.one("SELECT * FROM users WHERE email=?", (email,))
    db.log_event("reset_requested", u and u["id"], email, None if u else "unknown address", request)
    return _otp_call(otp.start, email, "reset", u and u["id"], {"pw_hash": db.hash_pw(pw)}, _ip(request),
                     send=bool(u))


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    tok = session_token(request)
    lu = db.session_user(tok)
    if lu:
        db.log_event("logout", lu["id"], lu["email"], None, request)
    db.end_session(tok)
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(u=Depends(user)):
    return {"user": public_user(u)}


@app.put("/api/me")
async def update_me(request: Request, u=Depends(user)):
    b = await request.json()
    allowed = {"name", "state", "district", "language", "units", "notify_weather", "share_farm_with_assistant"}
    sets = {k: v for k, v in b.items() if k in allowed}
    if "language" in sets and sets["language"] not in translate.LANGS:
        err(422, "Unsupported language")
    if sets:
        db.run(f"UPDATE users SET {', '.join(k + '=?' for k in sets)} WHERE id=?", (*sets.values(), u["id"]))
    return {"user": public_user(db.one("SELECT * FROM users WHERE id=?", (u["id"],)))}


@app.put("/api/me/password")
async def change_pw(request: Request, u=Depends(user)):
    b = await request.json()
    if not db.check_pw(b.get("current") or "", u["pw_hash"]):
        err(403, "Current password is incorrect", fields={"current": "Incorrect"})
    new = b.get("new") or ""
    if len(new) < 8 or not re.search(r"\d", new) or not re.search(r"[A-Za-z]", new):
        err(422, "At least 8 characters with letters and numbers", fields={"new": "Too weak"})
    db.run("UPDATE users SET pw_hash=? WHERE id=?", (db.hash_pw(new), u["id"]))
    db.run("DELETE FROM sessions WHERE user_id=?", (u["id"],))
    return {"ok": True, "signed_out": True}


@app.post("/api/me/delete")
async def delete_me(request: Request, response: Response, u=Depends(user)):
    b = await request.json()
    if not db.check_pw(b.get("password") or "", u["pw_hash"]):
        err(403, "Password is incorrect")
    for t in ("predictions", "farms", "chats", "sessions", "uploads", "auth_events", "otp_challenges"):
        db.run(f"DELETE FROM {t} WHERE user_id=?", (u["id"],))
    if u["email"]:
        db.run("DELETE FROM otp_challenges WHERE email=?", (u["email"],))
    db.run("DELETE FROM users WHERE id=?", (u["id"],))
    response.delete_cookie(COOKIE)
    return {"ok": True}


# ---------------- status / model cards ----------------
@app.get("/api/status")
def status():
    crop, yld, leaf = ml.card("crop_model"), ml.card("yield_model"), ml.card("leaf_disease")
    return {
        "models": {
            "crop": {"ready": crop is not None, "name": crop and crop["selected_model"],
                     "test_accuracy": crop and crop["test_accuracy"]},
            "yield": {"ready": yld is not None, "name": "LightGBM (correction to 3-yr mean)",
                      "test_mae": yld and yld["results"]["LightGBM (this model)"]["mae_t_ha"],
                      "test_r2": yld and yld["results"]["LightGBM (this model)"]["r2"]},
            "disease": {"ready": ml.leaf_ready(), "name": leaf and leaf["architecture"],
                        "test_accuracy": leaf and leaf["test"]["accuracy"]},
            "fertiliser": {"ready": fertiliser.ready(), "name": fertiliser.ready() and fertiliser.card()["name"],
                           "cv_accuracy": fertiliser.ready() and fertiliser.card()["chosen"]["cv_accuracy_mean"]},
        },
        "assistant": assistant.configured(),
        "otp": otp.enabled(),
        "translation": translate.configured(),
    }


@app.get("/api/models/{name}")
def model_card(name: str, u=Depends(user)):
    files = {"crop": "crop_model", "yield": "yield_model", "disease": "leaf_disease", "fertiliser": "fertiliser_model"}
    if name not in files:
        err(404, "Unknown model")
    c = ml.card(files[name])
    if not c:
        err(503, "Model not trained yet")
    c = dict(c)
    for k in ("crop_profiles", "categories", "confusion_matrix", "crop_mean"):
        c.pop(k, None)
    return c


# ---------------- farms ----------------
FARM_FIELDS = ["name", "state", "district", "village", "lat", "lon", "area_ha", "soil_type", "current_crop",
               "irrigation", "notes", "crop_history"]


def _farm_payload(b):
    f = {k: b.get(k) for k in FARM_FIELDS}
    if not (f["name"] or "").strip():
        err(422, "Farm name is required", fields={"name": "Required"})
    for k in ("lat", "lon", "area_ha"):
        if f[k] in ("", None):
            f[k] = None
        else:
            try:
                f[k] = float(f[k])
            except ValueError:
                err(422, f"{k} must be a number", fields={k: "Number"})
    if f["lat"] is not None and not (6 <= f["lat"] <= 38 and 68 <= (f["lon"] or 0) <= 98):
        err(422, "Coordinates must be inside India", fields={"lat": "Outside India"})
    f["crop_history"] = json.dumps(f["crop_history"] or [])
    return f


def _farm_out(f):
    f = dict(f)
    f["crop_history"] = json.loads(f.get("crop_history") or "[]")
    return f


@app.get("/api/farms")
def farms(u=Depends(user)):
    return {"farms": [_farm_out(f) for f in db.rows("SELECT * FROM farms WHERE user_id=? ORDER BY id", (u["id"],))]}


@app.post("/api/farms")
async def add_farm(request: Request, u=Depends(user)):
    f = _farm_payload(await request.json())
    fid = db.run(f"INSERT INTO farms(user_id,{','.join(FARM_FIELDS)},updated_at) VALUES(?{',?' * len(FARM_FIELDS)},?)",
                 (u["id"], *[f[k] for k in FARM_FIELDS], time.time()))
    return {"farm": _farm_out(db.one("SELECT * FROM farms WHERE id=?", (fid,)))}


@app.get("/api/farms/{fid}")
def get_farm(fid: int, u=Depends(user)):
    f = own_farm(u, fid)
    preds = db.rows("SELECT id,kind,crop,summary,confidence,created_at FROM predictions WHERE farm_id=? AND user_id=? "
                    "ORDER BY id DESC LIMIT 50", (fid, u["id"]))
    return {"farm": _farm_out(f), "predictions": preds}


@app.put("/api/farms/{fid}")
async def edit_farm(fid: int, request: Request, u=Depends(user)):
    own_farm(u, fid)
    f = _farm_payload(await request.json())
    db.run(f"UPDATE farms SET {', '.join(k + '=?' for k in FARM_FIELDS)}, updated_at=? WHERE id=? AND user_id=?",
           (*[f[k] for k in FARM_FIELDS], time.time(), fid, u["id"]))
    return {"farm": _farm_out(db.one("SELECT * FROM farms WHERE id=?", (fid,)))}


@app.delete("/api/farms/{fid}")
def del_farm(fid: int, u=Depends(user)):
    own_farm(u, fid)
    db.run("UPDATE predictions SET farm_id=NULL WHERE farm_id=? AND user_id=?", (fid, u["id"]))
    db.run("DELETE FROM farms WHERE id=? AND user_id=?", (fid, u["id"]))
    return {"ok": True}


# ---------------- crop recommendation ----------------
@app.post("/api/crop/recommend")
async def crop_recommend(request: Request, u=Depends(user)):
    b = await request.json()
    x, errs = ml.validate(b)
    if errs:
        err(422, "Please fix the highlighted fields", fields=errs)
    farm = own_farm(u, b.get("farm_id"))
    r = ml.recommend_crop(x)
    pid = save_prediction(u, "crop", x, r, f"{r['crop'].title()} ({r['confidence'] * 100:.0f}%)", r["crop"],
                          r["confidence"], farm and farm["id"], f"crop/{r['model']}")
    return {"id": pid, **r}


@app.get("/api/crop/info")
def crop_info(u=Depends(user)):
    c = ml.card("crop_model")
    return {"classes": c["classes"], "feature_ranges": c["feature_ranges"], "profiles": c["crop_profiles"]}


# ---------------- yield ----------------
@app.get("/api/yield/options")
def y_options(u=Depends(user)):
    return ml.yield_options()


@app.get("/api/yield/districts")
def y_districts(state: str, u=Depends(user)):
    return {"districts": ml.districts(state)}


@app.post("/api/yield/predict")
async def y_predict(request: Request, u=Depends(user)):
    b = await request.json()
    fields = {}
    for k in ("state", "district", "crop", "season"):
        if not b.get(k):
            fields[k] = "Required"
    try:
        year = int(b.get("year") or 0)
        if not 1998 <= year <= dt.date.today().year + 1:
            fields["year"] = f"1998 to {dt.date.today().year + 1}"
    except ValueError:
        fields["year"] = "Number"
    try:
        area = float(b.get("area_ha") or 0)
        if not 0 < area <= 1e6:
            fields["area_ha"] = "Area must be above 0"
    except ValueError:
        fields["area_ha"] = "Number"
    if fields:
        err(422, "Please fix the highlighted fields", fields=fields)
    farm = own_farm(u, b.get("farm_id"))
    try:
        r = ml.predict_yield(b["state"], b["district"], b["crop"], b["season"], year, area)
    except ValueError as e:
        err(422, str(e))
    inputs = {k: b.get(k) for k in ("state", "district", "crop", "season")} | {"year": year, "area_ha": area}
    pid = save_prediction(u, "yield", inputs, r, f"{r['yield_t_ha']:.2f} t/ha", b["crop"], None,
                          farm and farm["id"], "yield/lightgbm-v1")
    return {"id": pid, **r}


# ---------------- fertiliser ----------------
@app.post("/api/fertiliser")
async def fert(request: Request, u=Depends(user)):
    b = await request.json()
    fields = {}
    for k in ("N", "P", "K"):
        try:
            v = float(b.get(k))
            if not 0 <= v <= 2000:
                fields[k] = "0 to 2000"
        except (TypeError, ValueError):
            fields[k] = "Required number"
    for k, (lo, hi) in {"ph": (3, 10), "organic_carbon": (0, 10), "moisture": (0, 100),
                        "temperature": (-5, 55), "humidity": (0, 100)}.items():
        if b.get(k) not in (None, ""):
            try:
                if not lo <= float(b[k]) <= hi:
                    fields[k] = f"{lo} to {hi}"
            except ValueError:
                fields[k] = "Number"
    if not b.get("crop") and b.get("basis") != "fertiliser_dataset":
        fields["crop"] = "Required"
    if fields:
        err(422, "Please fix the highlighted fields", fields=fields)
    farm = own_farm(u, b.get("farm_id"))
    if not fertiliser.ready():
        err(503, "The fertiliser model is not available yet")
    try:
        r = fertiliser.recommend(b, ml.card("crop_model")["crop_profiles"])
    except ValueError as e:
        err(422, str(e))
    inputs = {k: b.get(k) for k in ("basis", "crop", "soil_type", "N", "P", "K", "ph", "organic_carbon",
                                     "moisture", "temperature", "humidity", "growth_stage", "irrigation",
                                     "previous_crop") if b.get(k) not in (None, "")}
    fz = r["fertiliser"]
    summary = f"{fz['name']} ({fz['grade']})" if fz["name"] else r["category"]
    pid = save_prediction(u, "fertiliser", inputs, r, summary, b.get("crop"), fz["confidence"],
                          farm and farm["id"], "fertiliser/logreg-v1")
    return {"id": pid, **r}


# ---------------- disease ----------------
@app.post("/api/disease")
async def disease(image: UploadFile = File(...), farm_id: str = Form(""), u=Depends(user)):
    if not ml.leaf_ready():
        err(503, "The disease model is not available yet")
    if image.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        err(415, "Upload a JPG or PNG image")
    data = await image.read()
    if len(data) > 8 * 1024 * 1024:
        err(413, "Image must be under 8 MB")
    farm = own_farm(u, farm_id)
    try:
        r = ml.diagnose(data)
    except Exception:
        err(422, "Could not read this image")
    info = INFO.get(r["best"]["class"])
    r["info"] = {"cause": info[0], "symptoms": info[1], "management": info[2]} if info else None
    b = r["best"]
    summary = {"no_leaf": "No leaf detected", "uncertain": "Uncertain - not named"}.get(
        r["verdict"], f"{b['crop']}: {b['condition']}")
    pid = save_prediction(u, "disease", {"filename": image.filename}, r, summary, b["crop"], b["probability"],
                          farm and farm["id"], "disease/efficientnet-b0-v1",
                          "needs review" if r["verdict"] in ("uncertain", "no_leaf") else "completed")
    db.save_upload(u["id"], image.filename, image.content_type, data, prediction_id=pid)
    return {"id": pid, **r}


@app.get("/api/uploads/{upload_id}")
def get_upload(upload_id: int, u=Depends(user)):
    r = db.one("SELECT content_type, data FROM uploads WHERE id=? AND user_id=?", (upload_id, u["id"]))
    if not r:
        err(404, "Not found")
    return Response(r["data"], media_type=r["content_type"] or "image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/me/activity")
def my_activity(u=Depends(user)):
    """The signed-in user's own sign-in history (from auth_events)."""
    return {"events": db.rows("SELECT event, detail, ip, created_at FROM auth_events WHERE user_id=? "
                              "ORDER BY id DESC LIMIT 50", (u["id"],))}


# ---------------- automatic inputs: random real samples from the datasets ----------------
RNG = random.SystemRandom()
SAMPLES = HERE / "data"
CROP_FEATS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]


@lru_cache
def _fert_rows():
    with open(SAMPLES / "fertiliser_samples.csv", newline="", encoding="utf-8") as fh:
        return [{k.strip(): v for k, v in r.items()} for r in csv.DictReader(fh) if r.get("Nitrogen")]


@lru_cache
def _crop_rows():
    with open(SAMPLES / "crop_samples.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@app.get("/api/samples/crop")
def sample_crop(u=Depends(user)):
    """One random row of Crop_recommendation.csv (2,200 rows); a different row on every call."""
    rows = _crop_rows()
    i = RNG.randrange(len(rows))
    r = rows[i]
    return {"source": "Crop_recommendation.csv", "row": i + 1, "of": len(rows), "label": r["label"],
            "values": {k: round(float(r[k]), 2) for k in CROP_FEATS}}


@app.get("/api/samples/yield")
def sample_yield(u=Depends(user)):
    """A random district-crop-season-year record (with at least 3 earlier years) from the production dataset."""
    for _ in range(12):
        r = ml.prod_rows("SELECT * FROM production WHERE year BETWEEN 2005 AND 2020 AND Area >= 50 "
                         "ORDER BY RANDOM() LIMIT 1")[0]
        hist = ml.prod_rows("SELECT COUNT(*) n FROM production WHERE District=? AND Crop=? AND Season=? AND year<?",
                            (r["District"], r["Crop"], r["Season"], r["year"]))[0]["n"]
        if hist >= 3:
            break
    return {"source": "India Agriculture Crop Production (data.gov.in)", "state": r["State"], "district": r["District"],
            "crop": r["Crop"], "season": r["Season"], "year": int(r["year"]),
            "recorded_yield_t_ha": round(float(r["yield"]), 3), "district_area_ha": round(float(r["Area"]), 1),
            "area_ha": RNG.choice([1, 1.5, 2, 2.5, 3, 4, 5]),
            "area_note": "The dataset records district totals, not farm sizes, so an example farm area is used."}


@app.get("/api/samples/fertiliser")
def sample_fertiliser(u=Depends(user)):
    """One random row of Fertilizer Prediction.csv (99 rows) with the fertiliser it records."""
    rows = _fert_rows()
    i = RNG.randrange(len(rows))
    r = rows[i]
    return {"source": "Fertilizer Prediction.csv", "row": i + 1, "of": len(rows), "label": r["Fertilizer Name"].strip(),
            "crop_type": r["Crop Type"].strip(), "soil_type": r["Soil Type"].strip(),
            "values": {"N": float(r["Nitrogen"]), "P": float(r["Phosphorous"]), "K": float(r["Potassium"]),
                       "temperature": float(r["Temparature"]), "humidity": float(r["Humidity"]),
                       "moisture": float(r["Moisture"])}}


@app.get("/api/samples/leaf")
def sample_leaf(u=Depends(user)):
    """A random leaf photo from the plant-disease dataset (3 bundled per class), with its true label."""
    root = SAMPLES / "leaf_samples"
    cls = RNG.choice(sorted(p.name for p in root.iterdir() if p.is_dir()))
    name = RNG.choice(sorted(p.name for p in (root / cls).iterdir()))
    crop_name, _, cond = cls.partition("___")
    return {"source": "Plant leaf diseases dataset (Mendeley)", "class": cls, "crop": crop_name.replace("_", " "),
            "condition": (cond or "no leaf").replace("_", " "), "url": f"/api/samples/leaf/{cls}/{name}"}


@app.get("/api/samples/leaf/{cls}/{name}")
def sample_leaf_file(cls: str, name: str, u=Depends(user)):
    root = (SAMPLES / "leaf_samples").resolve()
    p = (root / cls / name).resolve()
    if root not in p.parents or not p.is_file():
        err(404, "Not found")
    return FileResponse(p, media_type="image/png" if p.suffix == ".png" else "image/jpeg")


@app.get("/api/disease/classes")
def disease_classes(u=Depends(user)):
    c = ml.card("leaf_disease")
    if not c:
        return {"classes": []}
    return {"classes": [ml.pretty(k) for k in c["classes"] if k != "Background_without_leaves"]}


# ---------------- weather / soil ----------------
def _loc(u, farm_id=None, lat=None, lon=None):
    if lat is not None and lon is not None:
        return float(lat), float(lon), "custom location"
    f = own_farm(u, farm_id) if farm_id else db.one(
        "SELECT * FROM farms WHERE user_id=? AND lat IS NOT NULL ORDER BY id LIMIT 1", (u["id"],))
    if f and f["lat"] is not None:
        return f["lat"], f["lon"], f["name"]
    if u.get("district"):
        g = external.geocode(u["district"])
        if g:
            return g[0]["lat"], g[0]["lon"], f"{g[0]['name']} (registered district)"
    return None


@app.get("/api/geocode")
def geocode(q: str, u=Depends(user)):
    try:
        return {"results": external.geocode(q)}
    except Exception:
        err(502, "Location search is unavailable right now")


@app.get("/api/weather")
def weather(farm_id: int | None = None, lat: float | None = None, lon: float | None = None, u=Depends(user)):
    loc = _loc(u, farm_id, lat, lon)
    if not loc:
        err(404, "Add a farm with a location (or a district in Settings) to see weather", code="no_location")
    try:
        fc = external.forecast(loc[0], loc[1])
    except Exception:
        err(502, "Open-Meteo is unreachable right now")
    return {"location": {"lat": loc[0], "lon": loc[1], "label": loc[2]}, **fc, "alerts": external.alerts(fc)}


@app.get("/api/weather/history")
def weather_history(start: str, end: str, farm_id: int | None = None, lat: float | None = None,
                    lon: float | None = None, u=Depends(user)):
    loc = _loc(u, farm_id, lat, lon)
    if not loc:
        err(404, "Add a farm with a location first", code="no_location")
    try:
        s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    except ValueError:
        err(422, "Dates must be YYYY-MM-DD")
    if e < s or (e - s).days > 366 * 3:
        err(422, "Choose a range of up to 3 years")
    if e > dt.date.today() - dt.timedelta(days=3):
        e = dt.date.today() - dt.timedelta(days=3)
    try:
        h = external.nasa_power(loc[0], loc[1], s, e)
    except Exception:
        err(502, "NASA POWER is unreachable right now")
    return {"location": {"lat": loc[0], "lon": loc[1], "label": loc[2]}, **h}


@app.get("/api/soil")
def soil(farm_id: int | None = None, lat: float | None = None, lon: float | None = None, u=Depends(user)):
    loc = _loc(u, farm_id, lat, lon)
    if not loc:
        err(404, "Add a farm with a location first", code="no_location")
    try:
        s = external.soilgrids(loc[0], loc[1])
    except Exception:
        err(502, "SoilGrids is unreachable right now (it is often slow - try again in a minute)")
    return {"location": {"lat": loc[0], "lon": loc[1], "label": loc[2]}, **s}


# ---------------- analytics ----------------
@app.get("/api/analytics/production")
def analytics(state: str | None = None, district: str | None = None, crop: str | None = None,
              season: str | None = None, u=Depends(user)):
    return ml.production_series(state, district, crop, season)


# ---------------- predictions / overview ----------------
def _pred_out(p, full=False):
    p = dict(p)
    p["inputs"] = json.loads(p["inputs"] or "{}")
    if full:
        p["result"] = json.loads(p["result"] or "{}")
    else:
        p.pop("result", None)
    return p


@app.get("/api/predictions")
def predictions(kind: str | None = None, farm_id: int | None = None, crop: str | None = None,
                status: str | None = None, start: str | None = None, end: str | None = None,
                q: str | None = None, limit: int = 200, u=Depends(user)):
    w, a = ["p.user_id=?"], [u["id"]]
    if kind:
        w.append("p.kind=?"); a.append(kind)
    if farm_id:
        w.append("p.farm_id=?"); a.append(farm_id)
    if crop:
        w.append("LOWER(p.crop)=LOWER(?)"); a.append(crop)
    if status:
        w.append("p.status=?"); a.append(status)
    if start:
        w.append("p.created_at>=?"); a.append(dt.datetime.fromisoformat(start).timestamp())
    if end:
        w.append("p.created_at<?"); a.append((dt.datetime.fromisoformat(end) + dt.timedelta(days=1)).timestamp())
    if q:
        w.append("(p.summary LIKE ? OR p.crop LIKE ? OR CAST(p.id AS TEXT)=?)"); a += [f"%{q}%", f"%{q}%", q]
    rs = db.rows(f"SELECT p.*, f.name farm FROM predictions p LEFT JOIN farms f ON f.id=p.farm_id "
                 f"WHERE {' AND '.join(w)} ORDER BY p.id DESC LIMIT ?", (*a, min(limit, 1000)))
    return {"predictions": [_pred_out(p) for p in rs]}


@app.get("/api/predictions/{pid}")
def prediction(pid: int, u=Depends(user)):
    p = db.one("SELECT p.*, f.name farm FROM predictions p LEFT JOIN farms f ON f.id=p.farm_id "
               "WHERE p.id=? AND p.user_id=?", (pid, u["id"]))
    if not p:
        err(404, "Prediction not found")
    return _pred_out(p, full=True)


@app.delete("/api/predictions/{pid}")
def del_prediction(pid: int, u=Depends(user)):
    db.run("DELETE FROM predictions WHERE id=? AND user_id=?", (pid, u["id"]))
    db.run("DELETE FROM uploads WHERE prediction_id=? AND user_id=?", (pid, u["id"]))
    return {"ok": True}


@app.get("/api/overview")
def overview(u=Depends(user)):
    uid = u["id"]
    counts = {r["kind"]: r["n"] for r in db.rows("SELECT kind, COUNT(*) n FROM predictions WHERE user_id=? GROUP BY kind", (uid,))}
    farms_ = db.rows("SELECT * FROM farms WHERE user_id=?", (uid,))
    avg_yield = db.one("SELECT AVG(json_extract(result,'$.yield_t_ha')) a FROM predictions WHERE user_id=? AND kind='yield'", (uid,))
    recent = [_pred_out(p) for p in db.rows("SELECT p.*, f.name farm FROM predictions p LEFT JOIN farms f ON f.id=p.farm_id "
                                            "WHERE p.user_id=? ORDER BY p.id DESC LIMIT 6", (uid,))]
    # Insights: only from this user's stored data - nothing generated.
    insights = []
    last_fert = db.one("SELECT result, created_at FROM predictions WHERE user_id=? AND kind='fertiliser' ORDER BY id DESC LIMIT 1", (uid,))
    if last_fert:
        res = json.loads(last_fert["result"])
        low = [k for k, v in res["status"].items() if v in ("low", "short")]
        name = (res.get("fertiliser") or {}).get("name")
        if low:
            insights.append({"type": "soil", "text": f"Your last fertiliser check found {', '.join(low)} short"
                                                    + (f" and suggested {name}" if name else "")
                                                    + ". Confirm with a soil test before buying fertiliser."})
    last_dis = db.one("SELECT summary, status FROM predictions WHERE user_id=? AND kind='disease' ORDER BY id DESC LIMIT 1", (uid,))
    if last_dis and "healthy" not in last_dis["summary"].lower():
        insights.append({"type": "disease", "text": f"Last leaf scan: {last_dis['summary']}. Re-check nearby plants and "
                                                   "confirm with your KVK if symptoms spread."})
    total_area = sum(f["area_ha"] or 0 for f in farms_)
    return {
        "user": public_user(u),
        "kpis": {"farms": len(farms_), "farm_area_ha": round(total_area, 2), "crop": counts.get("crop", 0),
                 "yield": counts.get("yield", 0),
                 "avg_yield": round(avg_yield["a"], 2) if avg_yield and avg_yield["a"] else None,
                 "fertiliser": counts.get("fertiliser", 0), "disease": counts.get("disease", 0),
                 "total": sum(counts.values())},
        "recent": recent, "insights": insights,
        "has_location": any(f["lat"] is not None for f in farms_) or bool(u.get("district")),
    }


# ---------------- assistant ----------------
def _context(u):
    ctx = {"user": {"name": u["name"], "state": u["state"], "district": u["district"]}}
    if u["share_farm_with_assistant"]:
        ctx["farms"] = [{k: f[k] for k in ("name", "district", "state", "area_ha", "soil_type", "current_crop", "irrigation")}
                        for f in db.rows("SELECT * FROM farms WHERE user_id=?", (u["id"],))]
        ctx["recent_predictions"] = [{"type": p["kind"], "summary": p["summary"], "inputs": json.loads(p["inputs"] or "{}"),
                                      "date": dt.datetime.fromtimestamp(p["created_at"]).strftime("%Y-%m-%d")}
                                     for p in db.rows("SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT 6", (u["id"],))]
    s = status()["models"]
    ctx["models"] = {"crop_recommendation": f"{s['crop']['name']}, test accuracy {s['crop']['test_accuracy']} on Crop_recommendation.csv",
                     "yield": f"LightGBM on India crop production 1997-2020, temporal test MAE {s['yield']['test_mae']} t/ha, no weather/soil inputs",
                     "disease": f"EfficientNet-B0 on PlantVillage-style leaf images, test accuracy {s['disease']['test_accuracy']}",
                     "fertiliser": "Logistic Regression on N, P, K trained on Fertilizer Prediction.csv (99 rows, 7 fertilisers: Urea, DAP, 14-35-14, 28-28, 17-17-17, 20-20, 10-26-26); names a fertiliser, never a dose"}
    return ctx


@app.get("/api/chats")
def chats(u=Depends(user)):
    return {"chats": db.rows("SELECT id,title,saved,updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC", (u["id"],))}


@app.get("/api/chats/{cid}")
def chat(cid: int, u=Depends(user)):
    c = db.one("SELECT * FROM chats WHERE id=? AND user_id=?", (cid, u["id"]))
    if not c:
        err(404, "Conversation not found")
    c["messages"] = json.loads(c["messages"])
    return c


@app.patch("/api/chats/{cid}")
async def patch_chat(cid: int, request: Request, u=Depends(user)):
    b = await request.json()
    if "saved" in b:
        db.run("UPDATE chats SET saved=? WHERE id=? AND user_id=?", (1 if b["saved"] else 0, cid, u["id"]))
    if b.get("title"):
        db.run("UPDATE chats SET title=? WHERE id=? AND user_id=?", (b["title"][:80], cid, u["id"]))
    return {"ok": True}


@app.delete("/api/chats/{cid}")
def del_chat(cid: int, u=Depends(user)):
    db.run("DELETE FROM chats WHERE id=? AND user_id=?", (cid, u["id"]))
    db.run("DELETE FROM uploads WHERE chat_id=? AND user_id=?", (cid, u["id"]))
    return {"ok": True}


@app.post("/api/chat/translate")
async def chat_translate(request: Request, u=Depends(user)):
    """Translate one earlier assistant answer into the chosen language (signed-in users; cached)."""
    b = await request.json()
    text, lang = str(b.get("text") or ""), b.get("lang") or ""
    if not text.strip():
        err(422, "Nothing to translate")
    if translate.in_language(text, lang):
        return {"text": text}
    try:
        return {"text": translate.translate_long(text, lang)}
    except translate.TranslateError as e:
        err(e.status, e.msg)


@app.post("/api/chat")
async def send_chat(message: str = Form(""), chat_id: str = Form(""), lang: str = Form("en"),
                    image: UploadFile | None = File(None), u=Depends(user)):
    message = message.strip()
    if not message and not image:
        err(422, "Type a question or attach a leaf photo")
    c = db.one("SELECT * FROM chats WHERE id=? AND user_id=?", (int(chat_id), u["id"])) if chat_id else None
    msgs = json.loads(c["messages"]) if c else []
    note = None
    if image is not None and image.filename:
        if not ml.leaf_ready():
            err(503, "The disease model is not available yet")
        img = await image.read()
        r = ml.diagnose(img)
        b = r["best"]
        note = (f"[Leaf photo analysed by the disease model: verdict={r['verdict']}, top class={b['crop']} - "
                f"{b['condition']} ({b['probability'] * 100:.1f}%), threshold {r['threshold'] * 100:.0f}%. "
                f"If verdict is uncertain or no_leaf, do not name a disease.]")
        message = (message or "Please look at my leaf photo.") + "\n" + note
    msgs.append({"role": "user", "content": message, "t": time.time()})
    try:
        text, model = assistant.reply(msgs, _context(u), lang)
    except RuntimeError as e:
        err(503, str(e))
    except Exception:
        err(502, "The assistant could not answer right now. Please try again.")
    msgs.append({"role": "assistant", "content": text, "t": time.time(), "model": model})
    title = (c and c["title"]) or message.split("\n")[0][:60]
    if c:
        db.run("UPDATE chats SET messages=?, updated_at=? WHERE id=?", (json.dumps(msgs), time.time(), c["id"]))
        cid = c["id"]
    else:
        cid = db.run("INSERT INTO chats(user_id,title,messages,updated_at) VALUES(?,?,?,?)",
                     (u["id"], title, json.dumps(msgs), time.time()))
    if note:
        db.save_upload(u["id"], image.filename, image.content_type, img, chat_id=cid)
    return {"chat_id": cid, "title": title, "reply": text, "model": model}


# ---------------- reports ----------------
def _report_rows(u, kind, farm_id, start, end):
    return predictions(kind=kind or None, farm_id=farm_id, crop=None, status=None, start=start or None,
                       end=end or None, q=None, limit=1000, u=u)["predictions"]


@app.get("/api/reports/csv")
def report_csv(kind: str = "", farm_id: int | None = None, start: str = "", end: str = "", u=Depends(user)):
    rs = _report_rows(u, kind, farm_id, start, end)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "date", "type", "farm", "crop", "result", "confidence", "model_version", "status", "inputs"])
    for p in rs:
        w.writerow([p["id"], dt.datetime.fromtimestamp(p["created_at"]).strftime("%Y-%m-%d %H:%M"), p["kind"],
                    p["farm"] or "", p["crop"] or "", p["summary"], p["confidence"] or "", p["model_version"],
                    p["status"], json.dumps(p["inputs"])])
    name = f"agrisense_{kind or 'all'}_{dt.date.today()}.csv"
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/reports/pdf")
def report_pdf(kind: str = "", farm_id: int | None = None, start: str = "", end: str = "", pid: int | None = None,
               u=Depends(user)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="AgriSense AI report", leftMargin=40, rightMargin=40)
    green = colors.HexColor("#2E8B57")
    story = [Paragraph("<font color='#2E8B57'>AgriSense AI</font> - Report", st["Title"]),
             Paragraph(f"Prepared for {u['name']} on {dt.date.today():%d %b %Y}", st["Normal"]), Spacer(1, 12)]
    if pid:
        p = prediction(pid, u)
        story += [Paragraph(f"Prediction #{p['id']} - {p['kind'].title()}", st["Heading2"]),
                  Paragraph(f"Result: <b>{p['summary']}</b>", st["Normal"]),
                  Paragraph(f"Date: {dt.datetime.fromtimestamp(p['created_at']):%d %b %Y %H:%M} | Model: {p['model_version']}", st["Normal"]),
                  Spacer(1, 8), Paragraph("Inputs", st["Heading3"])]
        t = Table([[k, str(v)] for k, v in p["inputs"].items()] or [["-", "-"]], colWidths=[150, 330])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5ECE6")), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
        story.append(t)
        res = p["result"]
        extra = res.get("explanation") or ([f"Top alternatives: " + ", ".join(f"{a['crop']} {a['probability'] * 100:.0f}%" for a in res.get("top", [])[1:])]
                                           if p["kind"] == "crop" else [])
        if p["kind"] == "yield":
            extra = [f"80% interval: {res['interval_80'][0]} - {res['interval_80'][1]} t/ha",
                     f"District average: {res.get('district_mean_t_ha')} t/ha ({res.get('years_of_history')} years)"]
        if p["kind"] == "disease" and res.get("info"):
            extra = [f"Cause: {res['info']['cause']}", f"Symptoms: {res['info']['symptoms']}",
                     f"Management: {res['info']['management']}"]
        for e in extra:
            story.append(Paragraph(e, st["Normal"]))
    else:
        rs = _report_rows(u, kind, farm_id, start, end)
        story.append(Paragraph(f"{len(rs)} {kind or 'all'} prediction(s)" + (f" from {start}" if start else "") +
                               (f" to {end}" if end else ""), st["Heading2"]))
        data = [["#", "Date", "Type", "Farm", "Result", "Conf."]] + [
            [p["id"], dt.datetime.fromtimestamp(p["created_at"]).strftime("%d-%m-%Y"), p["kind"], (p["farm"] or "-")[:18],
             Paragraph(p["summary"], st["BodyText"]), f"{p['confidence'] * 100:.0f}%" if p["confidence"] else "-"] for p in rs]
        t = Table(data, colWidths=[30, 65, 65, 90, 210, 45], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), green), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5ECE6")), ("FONTSIZE", (0, 0), (-1, -1), 8),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(t)
    story += [Spacer(1, 16), Paragraph("Model outputs are estimates. Confirm decisions with a soil test and your local "
                                       "Krishi Vigyan Kendra.", st["Italic"])]
    doc.build(story)
    name = f"agrisense_{'prediction_' + str(pid) if pid else kind or 'all'}_{dt.date.today()}.pdf"
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


# Option lists shared by the web dashboard and the Android app (one definition, on the server).
SOIL_TYPES = ["Alluvial", "Black", "Red", "Laterite", "Sandy", "Loamy", "Clayey"]
IRRIGATION = ["Rainfed", "Canal", "Tubewell", "Drip", "Sprinkler"]
GROWTH_STAGES = ["Pre-sowing", "Vegetative", "Flowering", "Fruiting"]
ROLES = [{"value": "farmer", "label": "Farmer"}, {"value": "agri_officer", "label": "Agricultural officer"},
         {"value": "researcher", "label": "Researcher"}]


@app.get("/api/meta/options")
def meta_options():
    return {"soil_types": SOIL_TYPES, "irrigation": IRRIGATION, "growth_stages": GROWTH_STAGES, "roles": ROLES,
            "fertiliser_bases": [{"value": "soil_test", "label": "Soil test report (kg/ha)"},
                                 {"value": "crop_profile", "label": "Same scale as crop recommendation"},
                                 {"value": "fertiliser_dataset", "label": "Nutrient need (fertiliser dataset scale)"}],
            "fertiliser_crop_types": fertiliser.card()["crop_types"] if fertiliser.ready() else [],
            "prediction_kinds": ["crop", "yield", "fertiliser", "disease"]}


@app.get("/api/public/states")
def public_states():
    return {"states": ml.yield_options()["State"]}


@app.get("/api/public/districts")
def public_districts(state: str):
    return {"districts": ml.districts(state)}


@app.get("/healthz")
def healthz():
    return {"ok": True}


STATIC = HERE / "static"


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/", StaticFiles(directory=STATIC), name="static")
