"""UML-style diagrams for the submission documents, drawn with matplotlib (saved as PNG)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "figs"
OUT.mkdir(exist_ok=True)
GREEN, DARK, MINT, GREY, ORANGE, BLUE = "#2e7d4f", "#1b3a2a", "#eef6f0", "#7a8a80", "#eb6834", "#2a78d6"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 8, "figure.dpi": 200})
NL = chr(10)


def _save(f, name):
    p = OUT / name
    f.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(f)
    return p


def _canvas(w, h, xl=100, yl=60):
    f, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xl); ax.set_ylim(0, yl); ax.axis("off")
    return f, ax


def box(ax, x, y, w, h, title, sub="", fc="white", ec=GREEN, fs=7.6, lw=1.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8", fc=fc, ec=ec, lw=lw))
    if sub:
        ax.text(x + w / 2, y + h - 1.2, title, ha="center", va="top", fontsize=fs, weight="bold", color=DARK)
        ax.text(x + w / 2, y + h - 3.6, sub, ha="center", va="top", fontsize=fs - 1.4, color="#444", linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs, weight="bold", color=DARK)


def arrow(ax, x1, y1, x2, y2, label="", color=GREY, style="-|>", ls="-", fs=6.2, off=(0, 0.8)):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle=style, color=color, lw=0.9, ls=ls,
                                                        shrinkA=0, shrinkB=0))
    if label:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], label, ha="center", va="bottom", fontsize=fs,
                color="#333", bbox=dict(fc="white", ec="none", pad=0.4))


def actor(ax, x, y, name):
    ax.add_patch(plt.Circle((x, y + 4.2), 1.1, fc="white", ec=DARK, lw=1))
    ax.plot([x, x], [y + 3.1, y + 0.9], color=DARK, lw=1)
    ax.plot([x - 1.6, x + 1.6], [y + 2.4, y + 2.4], color=DARK, lw=1)
    ax.plot([x, x - 1.3], [y + 0.9, y - 1], color=DARK, lw=1)
    ax.plot([x, x + 1.3], [y + 0.9, y - 1], color=DARK, lw=1)
    ax.text(x, y - 1.8, name, ha="center", va="top", fontsize=7, weight="bold", color=DARK)


def usecase():
    f, ax = _canvas(9, 6.8, 100, 76)
    ax.add_patch(FancyBboxPatch((18, 1), 64, 74, boxstyle="round,pad=0.3,rounding_size=1.5", fc="#fbfdfb", ec=GREEN, lw=1.2))
    ax.text(50, 73.5, "AgriSense AI", ha="center", fontsize=9, weight="bold", color=GREEN)
    cases = ["Register with e-mail code", "Sign in (password + code)", "Reset password", "Manage profile / delete account",
             "Manage farms", "Get crop recommendation", "Predict yield", "Get fertiliser suggestion", "Detect leaf disease",
             "Chat with AI assistant", "View weather & forecast", "View soil profile", "View history / delete",
             "Export PDF / CSV reports", "View production analytics", "Run auto analysis (dataset)"]
    ys = []
    for i, c in enumerate(cases):
        col, row = i % 2, i // 2
        x, y = 23 + col * 30, 66 - row * 8.6
        ax.add_patch(Ellipse((x + 12, y), 25, 6, fc="white", ec=GREEN, lw=1))
        ax.text(x + 12, y, c, ha="center", va="center", fontsize=6.6)
        ys.append((x, y, col))
    actor(ax, 7, 40, "Farmer /" + NL + "Agri officer /" + NL + "Researcher")
    for x, y, col in ys:
        if col == 0:
            ax.plot([9, x - 0.5], [42, y], color="#b9c5bd", lw=0.6)
    for x, y, col in ys[1::2]:
        ax.plot([9, x - 0.5], [42, y], color="#b9c5bd", lw=0.6)
    actor(ax, 92, 58, "E-mail service" + NL + "(n8n + SMTP)")
    actor(ax, 92, 36, "Mistral API")
    actor(ax, 92, 14, "Open-Meteo /" + NL + "NASA POWER /" + NL + "SoilGrids")
    for (x, y, _), tgt in zip([ys[0], ys[1], ys[2]], [58, 58, 58]):
        ax.plot([x + 24.5, 90], [y, tgt + 2], color="#f3b394", lw=0.6, ls="--")
    ax.plot([ys[9][0] + 24.5, 90], [ys[9][1], 38], color="#f3b394", lw=0.6, ls="--")
    for k in (10, 11):
        ax.plot([ys[k][0] + 24.5, 90], [ys[k][1], 16], color="#f3b394", lw=0.6, ls="--")
    return _save(f, "usecase.png")


def context_dfd():
    f, ax = _canvas(9, 4.2, 100, 46)
    ax.add_patch(plt.Circle((50, 23), 10, fc=MINT, ec=GREEN, lw=1.3))
    ax.text(50, 23, "0" + NL + "AgriSense AI" + NL + "system", ha="center", va="center", fontsize=8, weight="bold", color=DARK)
    ents = [(2, 33, "Farmer"), (2, 8, "Administrator" + NL + "(deploys)"), (78, 38, "E-mail (n8n)"),
            (78, 25, "Mistral API"), (78, 12, "Open-Meteo /" + NL + "NASA POWER"), (78, 0.5, "ISRIC SoilGrids")]
    for x, y, t in ents:
        box(ax, x, y, 18, 7, t, fc="white", ec=DARK)
    arrow(ax, 20, 37, 41, 27, "registration, sign-in, soil values," + NL + "photos, questions", off=(-2, 1.5))
    arrow(ax, 41, 21, 20, 34, "recommendations, predictions," + NL + "diagnoses, answers, reports", off=(-3, -6.5))
    arrow(ax, 20, 11, 41, 18, "models, config, keys", off=(-1, -3))
    arrow(ax, 59, 27, 78, 41, "e-mail + code", off=(0, 0.6))
    arrow(ax, 60, 24, 78, 28.5, "prompt + context", off=(0, 0.4))
    arrow(ax, 60, 21, 78, 16, "lat / lon, dates", off=(1, -0.2))
    arrow(ax, 59, 18, 78, 4.5, "lat / lon", off=(1, -1))
    return _save(f, "dfd0.png")


def dfd_level1():
    f, ax = _canvas(9.4, 6.4, 100, 70)
    ys = [60, 49, 38, 27, 16, 5]
    names = ["1.0 Authenticate (+ e-mail OTP)", "2.0 Manage farms", "3.0 Run models (crop / yield / leaf / fert.)",
             "4.0 Assistant chat", "5.0 Fetch weather & soil", "6.0 History & reports"]
    for y, t in zip(ys, names):
        ax.add_patch(FancyBboxPatch((30, y), 28, 7, boxstyle="round,pad=0.3,rounding_size=3", fc=MINT, ec=GREEN))
        ax.text(44, y + 3.5, t, ha="center", va="center", fontsize=6.8, weight="bold", color=DARK)
        arrow(ax, 17, 36, 30, y + 3.5)
    box(ax, 1, 32, 16, 8, "Farmer", fc="white", ec=DARK)
    stores = {"D1": (66, "D1  users, sessions, otp_challenges, auth_events"), "D2": (48, "D2  farms, predictions, uploads, chats"),
              "D3": (34, "D3  trained models + model cards"), "D4": (21, "D4  production history (1997-2020)")}
    for k, (y, t) in stores.items():
        ax.plot([70, 99], [y, y], color=DARK, lw=1); ax.plot([70, 99], [y - 5, y - 5], color=DARK, lw=1)
        ax.plot([70, 70], [y - 5, y], color=DARK, lw=1)
        ax.text(71, y - 2.5, t, va="center", fontsize=6.2, color=DARK)
    box(ax, 70, 1, 29, 9, "External: Mistral API, Open-Meteo," + NL + "NASA POWER, SoilGrids, n8n e-mail", fc="white", ec=ORANGE, fs=6.4)
    links = [(60, 63.5, "D1"), (49, 45.5, "D2"), (38, 31.5, "D3"), (38, 45.5, "D2"), (38, 18.5, "D4"), (27, 45.5, "D2"),
             (5, 45.5, "D2"), (16, 18.5, "D4")]
    for y, ty, _ in links:
        arrow(ax, 58.5, y + 3.5, 70, ty, color="#9fb3a6")
    for y in (60, 27, 16):
        arrow(ax, 58.5, y + 2, 70, 5.5, color="#f3b394", ls="--")
    return _save(f, "dfd1.png")


ER_TABLES = {
    "users": ["id PK", "name", "email UNIQUE", "phone UNIQUE", "pw_hash (scrypt)", "state, district", "role, language",
              "email_verified_at", "last_login_at", "created_at"],
    "sessions": ["token_hash PK (SHA-256)", "user_id FK", "expires"],
    "farms": ["id PK", "user_id FK", "name, village", "state, district", "lat, lon, area_ha", "soil_type, irrigation",
              "crop_history (JSON)", "updated_at"],
    "predictions": ["id PK", "user_id FK", "farm_id FK (null)", "kind", "inputs, result (JSON)", "summary, crop",
                    "confidence, status", "model_version", "created_at"],
    "uploads": ["id PK", "user_id FK", "prediction_id FK", "chat_id FK", "filename, content_type", "size, sha256",
                "data BLOB", "created_at"],
    "chats": ["id PK", "user_id FK", "title, saved", "messages (JSON)", "updated_at"],
    "otp_challenges": ["id PK (random)", "email", "purpose", "user_id FK (null)", "payload (JSON)", "code_hash (SHA-256)",
                       "attempts, sends", "expires, last_sent", "consumed_at, ip"],
    "auth_events": ["id PK", "user_id FK (null)", "email", "event, detail", "ip, user_agent", "created_at"],
    "production": ["State, District", "Crop, Season", "year", "Area, Production", "yield"],
    "cache": ["key PK", "value (JSON)", "expires"],
}


def er_diagram():
    f, ax = _canvas(9.6, 9.6, 100, 100)
    pos = {"users": (38, 46), "sessions": (4, 86), "farms": (4, 42), "predictions": (38, 8), "uploads": (72, 8),
           "chats": (72, 50), "otp_challenges": (72, 74), "auth_events": (38, 78), "production": (4, 8), "cache": (4, 68)}
    rects = {}
    for t, (x, y) in pos.items():
        rows = ER_TABLES[t]
        h = 2.6 + 2.05 * len(rows)
        ax.add_patch(FancyBboxPatch((x, y), 24, h, boxstyle="square,pad=0", fc="white", ec=GREEN, lw=1))
        ax.add_patch(FancyBboxPatch((x, y + h - 2.6), 24, 2.6, boxstyle="square,pad=0", fc=GREEN, ec=GREEN))
        ax.text(x + 12, y + h - 1.3, t, ha="center", va="center", color="white", fontsize=7.2, weight="bold")
        for i, r in enumerate(rows):
            ax.text(x + 0.8, y + h - 3.7 - 2.05 * i, r, va="center", fontsize=5.9,
                    color=DARK if ("PK" in r or "FK" in r) else "#444", weight="bold" if "PK" in r else "normal")
        rects[t] = (x, y, 24, h)

    def link(a, b, la="1", lb="N"):
        xa, ya, wa, ha = rects[a]; xb, yb, wb, hb = rects[b]
        ca, cb = (xa + wa / 2, ya + ha / 2), (xb + wb / 2, yb + hb / 2)
        def edge(r, c, o):
            x, y, w, h = r
            dx, dy = o[0] - c[0], o[1] - c[1]
            if abs(dx) * h > abs(dy) * w:
                return (x + w if dx > 0 else x, c[1])
            return (c[0], y + h if dy > 0 else y)
        pa, pb = edge(rects[a], ca, cb), edge(rects[b], cb, ca)
        ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=GREY, lw=0.9)
        ax.text(pa[0] + (pb[0] - pa[0]) * 0.08, pa[1] + (pb[1] - pa[1]) * 0.08 + 0.6, la, fontsize=6.5, color=ORANGE, weight="bold")
        ax.text(pb[0] - (pb[0] - pa[0]) * 0.1, pb[1] - (pb[1] - pa[1]) * 0.1 + 0.6, lb, fontsize=6.5, color=ORANGE, weight="bold")
    for t in ("sessions", "farms", "predictions", "chats", "otp_challenges", "auth_events"):
        link("users", t)
    link("predictions", "uploads", "1", "0..1")
    link("farms", "predictions", "0..1", "N")
    link("chats", "uploads", "1", "N")
    return _save(f, "er.png")


def sequence(name, parts, msgs, height=None, width=9.4):
    """parts: list of names; msgs: (from_idx, to_idx, text, kind) kind in {'call','ret','self','note'}."""
    n = len(msgs)
    H = height or (6 + n * 3.4)
    f, ax = _canvas(width, H / 9, 100, H)
    xs = [6 + i * (88 / (len(parts) - 1)) for i in range(len(parts))]
    for x, p in zip(xs, parts):
        box(ax, x - 7, H - 5, 14, 4.2, p, fc=MINT, fs=6.8)
        ax.plot([x, x], [1, H - 5], color="#b9c5bd", lw=0.8, ls="--")
    y = H - 8
    for a, b, text, kind in msgs:
        if kind == "self":
            ax.annotate("", (xs[a] + 0.4, y - 1.6), (xs[a] + 0.4, y),
                        arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=0.9, connectionstyle="arc3,rad=-1.4"))
            ax.text(xs[a] + 4, y - 0.8, text, fontsize=6.1, va="center", color="#333")
        elif kind == "note":
            ax.text(xs[a], y - 0.6, text, fontsize=6.1, ha="center", va="center", color=DARK,
                    bbox=dict(fc="#fff8e1", ec="#e8c66a", pad=2))
        else:
            arrow(ax, xs[a], y, xs[b], y, text, color=GREEN if kind == "call" else GREY,
                  ls="-" if kind == "call" else "--", off=(0, 0.25))
        y -= 3.4
    return _save(f, name)


def seq_signup():
    return sequence("seq_signup.png", ["Browser", "FastAPI", "SQLite", "n8n workflow", "SMTP"], [
        (0, 1, "POST /api/auth/register {name, email, password}", "call"),
        (1, 1, "validate fields, check duplicates, scrypt(password)", "self"),
        (1, 2, "INSERT otp_challenges (SHA-256 code, payload, expires +10 min)", "call"),
        (1, 3, "POST /webhook/agrisense-otp  x-otp-secret", "call"),
        (3, 3, "shared secret matches?", "self"),
        (3, 4, "send e-mail with 6-digit code", "call"),
        (3, 1, '{"ok": true}', "ret"),
        (1, 0, "{otp_required, challenge_id, masked e-mail}", "ret"),
        (0, 0, "user types the code from the e-mail", "note"),
        (0, 1, "POST /api/auth/otp/verify {challenge_id, code}", "call"),
        (1, 2, "compare SHA-256, attempts < 5, not expired, mark consumed", "call"),
        (1, 2, "INSERT users (email_verified_at), sessions, auth_events", "call"),
        (1, 0, "Set-Cookie agrisense_session (HttpOnly) + user", "ret")])


def seq_login():
    return sequence("seq_login.png", ["Browser", "FastAPI", "SQLite", "n8n + SMTP"], [
        (0, 1, "POST /api/auth/login {identifier, password, remember}", "call"),
        (1, 2, "SELECT user; scrypt check", "call"),
        (1, 2, "wrong -> INSERT auth_events(login_failed); 401", "call"),
        (1, 2, "right -> INSERT otp_challenges(purpose=login)", "call"),
        (1, 3, "deliver code", "call"),
        (1, 0, "{otp_required, challenge_id}", "ret"),
        (0, 1, "POST /api/auth/otp/verify", "call"),
        (1, 2, "verify + INSERT sessions, auth_events(login)", "call"),
        (1, 0, "session cookie (1 day or 30 days with 'remember me')", "ret")])


def seq_predict():
    return sequence("seq_predict.png", ["Browser", "FastAPI", "ml.py", "Model file", "SQLite"], [
        (0, 1, "POST /api/yield/predict {state, district, crop, season, year, area}", "call"),
        (1, 1, "require session, validate fields", "self"),
        (1, 2, "predict_yield(...)", "call"),
        (2, 4, "SELECT district history (lags, 3-yr mean, state last year)", "call"),
        (2, 3, "LightGBM.predict(features) + pred_contrib (SHAP)", "call"),
        (2, 1, "yield = base x exp(correction); 80% interval; contributions", "ret"),
        (1, 4, "INSERT predictions (inputs, result, model_version)", "call"),
        (1, 0, "JSON result -> charts and explanation", "ret")])


def seq_disease():
    return sequence("seq_disease.png", ["Browser", "FastAPI", "ml.py", "ONNX Runtime", "SQLite"], [
        (0, 1, "POST /api/disease (multipart image)", "call"),
        (1, 1, "type JPG/PNG, size <= 8 MB", "self"),
        (1, 2, "diagnose(bytes)", "call"),
        (2, 2, "resize 224x224, normalise, + flipped copy", "self"),
        (2, 3, "EfficientNet-B0 logits", "call"),
        (2, 2, "softmax(logits / T), average, threshold", "self"),
        (2, 1, "verdict: diseased / healthy / uncertain / no_leaf", "ret"),
        (1, 4, "INSERT predictions + uploads (photo bytes)", "call"),
        (1, 0, "class, confidence, top-5, cause / symptoms / steps", "ret")])


def seq_chat():
    return sequence("seq_chat.png", ["Browser", "FastAPI", "SQLite", "Mistral API"], [
        (0, 1, "POST /api/chat {message, lang, optional photo}", "call"),
        (1, 2, "load farms, recent predictions, model metrics (context)", "call"),
        (1, 1, "photo? run leaf model, add result note", "self"),
        (1, 3, "chat/completions (system prompt + context + last 12 messages)", "call"),
        (3, 1, "reply (ministral-14b; falls back to 8b / 3b on 429)", "ret"),
        (1, 2, "UPDATE chats; INSERT uploads (photo)", "call"),
        (1, 0, "{chat_id, reply, model}", "ret")])


def otp_state():
    f, ax = _canvas(9, 3.4, 100, 36)
    st = [(2, 14, "Issued" + NL + "(code e-mailed)"), (28, 26, "Waiting"), (28, 2, "Resent" + NL + "(new code)"),
          (56, 26, "Consumed" + NL + "(success)"), (56, 2, "Expired" + NL + "(10 min)"), (82, 14, "Locked" + NL + "(5 wrong)")]
    for x, y, t in st:
        ax.add_patch(FancyBboxPatch((x, y), 16, 7.5, boxstyle="round,pad=0.3,rounding_size=3", fc=MINT, ec=GREEN))
        ax.text(x + 8, y + 3.75, t, ha="center", va="center", fontsize=7, weight="bold", color=DARK)
    arrow(ax, 18, 19, 28, 28, "")
    arrow(ax, 44, 30, 56, 30, "correct code")
    arrow(ax, 36, 26, 36, 9.5, "resend" + NL + "(>= 60 s)", off=(5, -3))
    arrow(ax, 40, 9.5, 40, 26, "")
    arrow(ax, 44, 27, 82, 19, "5th wrong code", off=(8, -1))
    arrow(ax, 44, 26.5, 56, 9, "time passes", off=(-2, -3))
    return _save(f, "otp_state.png")


def deployment():
    f, ax = _canvas(9.4, 4.8, 100, 52)
    ax.add_patch(FancyBboxPatch((22, 1), 76, 49, boxstyle="round,pad=0.3,rounding_size=1.5", fc="#fbfdfb", ec=DARK, lw=1.2))
    ax.text(24, 48, "Hostinger VPS 187.127.191.13 (Ubuntu, Docker)", fontsize=7.5, weight="bold", color=DARK, va="top")
    box(ax, 1, 22, 16, 10, "Browser", "HTTPS 443", fc=MINT)
    box(ax, 25, 22, 18, 14, "Traefik", "host network" + NL + "file provider" + NL + "Let's Encrypt TLS")
    ax.add_patch(FancyBboxPatch((48, 18, ), 24, 27, boxstyle="round,pad=0.3,rounding_size=1", fc="white", ec=GREEN, lw=1, ls="--"))
    ax.text(49, 43.5, "container agrisense", fontsize=6.8, weight="bold", color=GREEN, va="top")
    box(ax, 50, 29, 20, 11, "uvicorn x2 workers", "FastAPI app" + NL + "models (ONNX, RF, LGBM)")
    box(ax, 50, 19.5, 20, 7.5, "volume agrisense_data", "agrisense.db (SQLite)", fs=6.6)
    ax.add_patch(FancyBboxPatch((76, 18), 20, 27, boxstyle="round,pad=0.3,rounding_size=1", fc="white", ec=ORANGE, lw=1, ls="--"))
    ax.text(77, 43.5, "network n8n-kmar_default", fontsize=6.2, weight="bold", color=ORANGE, va="top")
    box(ax, 78, 27, 16, 11, "n8n", "AgriSense_OTP" + NL + "_Delivery", ec=ORANGE)
    box(ax, 50, 3, 20, 9, "config/api_keys.env", "read-only mount" + NL + "Mistral key, OTP secret", fs=6.6)
    box(ax, 78, 3, 16, 9, "SMTP", "support@" + NL + "visioncoders.online", ec=ORANGE, fs=6.6)
    arrow(ax, 17, 27, 25, 29, "TLS")
    arrow(ax, 43, 32, 50, 34, ""); ax.text(46.5, 37.5, "127.0.0.1:8150", fontsize=5.8, ha="center", color="#333")
    arrow(ax, 70, 34, 78, 33, "webhook")
    arrow(ax, 86, 27, 86, 12, "")
    arrow(ax, 60, 12, 60, 19.5, "")
    return _save(f, "deployment.png")


def ml_pipeline():
    f, ax = _canvas(9.4, 3.8, 100, 40)
    cols = [(1, "Raw data", "CSV, zipped images"), (19, "Clean & split", "temporal / stratified" + NL + "leak guard"),
            (37, "Train (GPU)", "5 crop models (CV)" + NL + "LightGBM, EfficientNet"),
            (55, "Evaluate", "held-out test," + NL + "baselines, calibration"),
            (73, "Refit on all data", "same recipe" + NL + "+ export ONNX"), (88, "Serve", "FastAPI on CPU")]
    for x, t, s in cols:
        box(ax, x, 18, 15 if x < 88 else 11, 14, t, s, fc=MINT if x in (37, 73) else "white")
    for (x1, *_), (x2, *_) in zip(cols, cols[1:]):
        arrow(ax, x1 + (15 if x1 < 88 else 11), 25, x2, 25)
    box(ax, 55, 2, 30, 9, "Model cards (*.json)", "metrics, splits, thresholds, history" + NL + "-> app, report, tests", ec=ORANGE)
    arrow(ax, 62, 18, 66, 11)
    arrow(ax, 80, 18, 76, 11)
    return _save(f, "ml_pipeline.png")


def modules():
    f, ax = _canvas(9.4, 5, 100, 54)
    box(ax, 38, 40, 24, 12, "main.py", "routes, auth, validation," + NL + "sessions, reports, chat", fc=MINT)
    mods = [(2, 22, "db.py", "SQLite schema, scrypt," + NL + "sessions, events, uploads"),
            (22, 22, "otp.py", "codes, limits," + NL + "n8n delivery"),
            (42, 22, "ml.py", "crop / yield / leaf" + NL + "inference, SHAP"),
            (62, 22, "external.py", "Open-Meteo, NASA," + NL + "SoilGrids + cache"),
            (82, 22, "assistant.py", "Mistral chat," + NL + "grounding, fallback"),
            (32, 4, "fertiliser.py", "shortfall step +" + NL + "fertiliser model"),
            (52, 4, "disease_info.py", "cause / symptoms /" + NL + "next steps")]
    for x, y, t, s in mods:
        box(ax, x, y, 16, 11, t, s)
        arrow(ax, 50, 40, x + 8, y + 11)
    box(ax, 2, 4, 22, 11, "static/", "index.html, app.js (SPA)," + NL + "i18n.js, styles.css", ec=BLUE)
    box(ax, 76, 4, 22, 11, "models/", "crop .joblib, yield .txt," + NL + "leaf .onnx + cards", ec=ORANGE)
    arrow(ax, 58, 22, 76, 12, "")
    return _save(f, "modules.png")


def gantt():
    tasks = [("Requirement study & proposal", 0, 1), ("Dataset collection & cleaning", 0.5, 1.5), ("SRS & UI design (Stitch)", 1, 1.2),
             ("Crop & yield models", 1.5, 1.5), ("Leaf disease CNN (GPU)", 2, 2), ("Backend API & database", 2, 2),
             ("Dashboard UI (EN/HI)", 2.5, 2), ("Weather, soil, assistant", 3.5, 1), ("Security & e-mail OTP", 4, 1),
             ("Testing (67 cases)", 4.5, 1.2), ("Deployment & documentation", 5, 1)]
    f, ax = plt.subplots(figsize=(8.6, 3.4))
    for i, (t, s, d) in enumerate(tasks[::-1]):
        ax.barh(i, d, left=s, color=GREEN if "model" in t.lower() or "CNN" in t else "#8cc2a0", height=0.56)
    ax.set_yticks(range(len(tasks)), [t for t, *_ in tasks[::-1]], fontsize=7)
    ax.set_xticks(range(7), [f"Week {i * 2 + 1}-{i * 2 + 2}" for i in range(7)], fontsize=7)
    ax.grid(axis="x", color="#e5e5e5"); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return _save(f, "gantt.png")


def sitemap():
    f, ax = _canvas(9.4, 4.4, 100, 48)
    box(ax, 2, 34, 15, 8, "Sign in", fc=MINT); box(ax, 2, 22, 15, 8, "Create account", fc=MINT)
    box(ax, 2, 10, 15, 8, "Forgot password", fc=MINT); box(ax, 22, 22, 15, 8, "E-mail code", fc="#fff8e1", ec=ORANGE)
    arrow(ax, 17, 38, 22, 28); arrow(ax, 17, 26, 22, 26); arrow(ax, 17, 14, 22, 24)
    box(ax, 42, 22, 13, 8, "Overview", fc=MINT)
    arrow(ax, 37, 26, 42, 26)
    pages = ["Crop Recommendation", "Yield Prediction", "Fertiliser", "Disease Detection", "AI Assistant", "Weather",
             "Soil Health", "Farm Management", "Prediction History", "Reports & Analytics", "Settings", "Help"]
    for i, p in enumerate(pages):
        col, row = i // 6, i % 6
        x, y = 62 + col * 19, 42 - row * 7.6
        box(ax, x, y, 17, 5.6, p, fs=6.6)
        ax.plot([55, x], [26, y + 2.8], color="#c9d3cd", lw=0.6)
    return _save(f, "sitemap.png")


def all_figs():
    return {k: fn() for k, fn in dict(usecase=usecase, dfd0=context_dfd, dfd1=dfd_level1, er=er_diagram, seq_signup=seq_signup,
                                     seq_login=seq_login, seq_predict=seq_predict, seq_disease=seq_disease, seq_chat=seq_chat,
                                     otp_state=otp_state, deployment=deployment, ml_pipeline=ml_pipeline, modules=modules,
                                     gantt=gantt, sitemap=sitemap).items()}


if __name__ == "__main__":
    print(all_figs())
