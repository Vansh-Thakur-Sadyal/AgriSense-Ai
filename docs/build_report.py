"""Build docs/AgriSense_AI_Model_Report.pdf from the model cards, the datasets and the screenshots.

Every number in the report is read from app/models/*.json (written by the ml/ training scripts),
so re-running this after retraining keeps the report true.

Run:  .venv/Scripts/python docs/build_report.py
"""
import json
import re
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from PIL import Image as PILImage  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "app" / "models"
DOCS = ROOT / "docs"
FIGS = DOCS / "figs"
SHOTS = DOCS / "screens"
OUT = DOCS / "AgriSense_AI_Model_Report.pdf"
LEAF_DIR = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"
FIGS.mkdir(parents=True, exist_ok=True)

crop = json.loads((MODELS / "crop_model.json").read_text())
yld = json.loads((MODELS / "yield_model.json").read_text())
leaf = json.loads((MODELS / "leaf_disease.json").read_text())
fert = json.loads((MODELS / "fertiliser_model.json").read_text())
sys.path.insert(0, str(ROOT))
from app import db as appdb  # noqa: E402

OTP = (ROOT / "app" / "otp.py").exists()

# ---------------------------------------------------------------- style
GREEN, DARK, MUTED, LINE, MINT = "#2e7d4f", "#1b3a2a", "#5f6b64", "#dfe7e2", "#eef6f0"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"   # validated categorical slots 1-3
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9, "axes.edgecolor": "#c9d3cd",
                     "axes.labelcolor": "#333", "xtick.color": "#555", "ytick.color": "#555",
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#ececec", "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 200})

F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("UI", F + "segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-B", F + "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-I", F + "segoeuii.ttf"))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI-I", boldItalic="UI-B")
body = ParagraphStyle("b", fontName="UI", fontSize=9.6, leading=14, textColor=colors.HexColor("#222"),
                      spaceAfter=5)
small = ParagraphStyle("s", parent=body, fontSize=8.2, leading=11, textColor=colors.HexColor(MUTED))
h1 = ParagraphStyle("h1", parent=body, fontName="UI-B", fontSize=18, leading=23, spaceBefore=4, spaceAfter=8,
                    textColor=colors.HexColor(DARK))
h2 = ParagraphStyle("h2", parent=body, fontName="UI-B", fontSize=12.5, leading=17, spaceBefore=10, spaceAfter=4,
                    textColor=colors.HexColor(GREEN))
cell = ParagraphStyle("c", parent=body, fontSize=8.4, leading=11, spaceAfter=0)
cellb = ParagraphStyle("cb", parent=cell, fontName="UI-B")
cap = ParagraphStyle("cap", parent=small, alignment=TA_CENTER, spaceAfter=10)
W = A4[0] - 36 * mm


def P(t, st=body):
    return Paragraph(t, st)


def bullets(items):
    return [P(f"•&nbsp;&nbsp;{i}", ParagraphStyle("bl", parent=body, leftIndent=10, firstLineIndent=-8,
                                                       spaceAfter=2)) for i in items]


def table(rows, widths, head=True, zebra=True):
    data = [[c if not isinstance(c, str) else P(c, cellb if (head and i == 0) else cell) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(LINE)),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(MINT)))
    t.setStyle(TableStyle(st))
    return t


def fig(path, width=1.0, caption=None):
    im = PILImage.open(path)
    w = W * width
    h = w * im.height / im.width
    out = [Image(str(path), width=w, height=h)]
    if caption:
        out.append(P(caption, cap))
    return KeepTogether(out)


def save(f, name):
    p = FIGS / name
    f.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(f)
    return p


def pct(x):
    return f"{x * 100:.2f}%"


# ---------------------------------------------------------------- figures
def fig_architecture():
    f, ax = plt.subplots(figsize=(9, 4.4))
    ax.set_xlim(0, 100); ax.set_ylim(0, 50); ax.axis("off")

    def box(x, y, w, h, title, sub, fc="#ffffff", ec=GREEN):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.0",
                                    fc=fc, ec=ec, lw=1.1))
        ax.text(x + w / 2, y + h - 1.6, title, ha="center", va="top", fontsize=7.8, weight="bold", color=DARK)
        ax.text(x + w / 2, y + h - 4.6, sub, ha="center", va="top", fontsize=6.3, color="#444", linespacing=1.3)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color="#7a8a80", lw=1,
                                                            shrinkA=0, shrinkB=0))

    NL = chr(10)
    box(4, 36, 20, 12, "Browser / Android app", "web SPA, 15 languages" + NL + "Kotlin app on the same API", MINT)
    box(36, 36, 20, 12, "Traefik on the VPS", "HTTPS (Let's Encrypt)" + NL + "ai.software.microeagle.online")
    box(68, 36, 28, 12, "FastAPI app (Docker)", "accounts, OTP, sessions, REST API" + NL + "container 'agrisense' :8150")
    arrow(24, 42, 36, 42); arrow(56, 42, 68, 42)
    ax.text(15, 27.5, "inside the server", fontsize=7, color=GREEN, weight="bold")
    ax.text(66, 27.5, "external services", fontsize=7, color=S2, weight="bold")
    xs = [1, 15.3, 29.6, 43.9, 58.2, 72.5, 86.8]
    items = [("ML models", "RF crop|LightGBM yield|EfficientNet leaf"), ("Fertiliser model", "LogReg on N,P,K|+ shortfall step"),
             ("SQLite", "users, farms,|predictions,|chats, OTP"), ("Open-Meteo", "forecast,|geocoding"),
             ("NASA POWER", "daily weather|history"), ("ISRIC SoilGrids", "soil maps|(WCS)"),
             ("Mistral / n8n", "assistant chat,|OTP e-mail")]
    for i, (x, (t, sub)) in enumerate(zip(xs, items)):
        box(x, 4, 12.2, 20, t, sub.replace("|", NL), ec=GREEN if i < 3 else S2)
        arrow(82, 36, x + 6.1, 24.3)
    return save(f, "architecture.png")


def fig_crop_comparison():
    c = crop["comparison"]
    names = [r["model"] for r in c]
    f, ax = plt.subplots(figsize=(7.5, 2.8))
    y = np.arange(len(names))
    ax.barh(y + 0.19, [r["cv_accuracy_mean"] * 100 for r in c], 0.36, color=S1, label="5-fold CV accuracy (train part)")
    ax.barh(y - 0.19, [r["test_accuracy"] * 100 for r in c], 0.36, color=S2, label="Held-out test accuracy")
    ax.set_yticks(y, names); ax.set_xlim(94, 100.4); ax.set_xlabel("accuracy (%)")
    for i, r in enumerate(c):
        ax.text(r["cv_accuracy_mean"] * 100 + 0.05, i + 0.19, f"{r['cv_accuracy_mean'] * 100:.2f}", va="center", fontsize=7)
        ax.text(r["test_accuracy"] * 100 + 0.05, i - 0.19, f"{r['test_accuracy'] * 100:.2f}", va="center", fontsize=7)
    ax.legend(loc="lower right", fontsize=7, frameon=False)
    ax.grid(axis="y", visible=False)
    return save(f, "crop_comparison.png")


def fig_importance(items, name, xlabel, color=GREEN, top=None, labels=None):
    items = items[:top] if top else items
    f, ax = plt.subplots(figsize=(7.5, 0.32 * len(items) + 0.8))
    lab = [labels.get(i["feature"], i["feature"]) if labels else i["feature"] for i in items][::-1]
    val = [i["importance"] * 100 for i in items][::-1]
    ax.barh(lab, val, color=color, height=0.62)
    for i, v in enumerate(val):
        ax.text(v + max(val) * 0.01, i, f"{v:.1f}", va="center", fontsize=7)
    ax.set_xlabel(xlabel); ax.grid(axis="y", visible=False)
    return save(f, name)


def fig_confusion(cm, classes, name, size=7.5, short=None):
    cm = np.array(cm, dtype=float)
    norm = cm / cm.sum(1, keepdims=True).clip(min=1)
    f, ax = plt.subplots(figsize=(size, size * 0.86))
    ax.imshow(norm, cmap="Greens", vmin=0, vmax=1)
    lab = [short(c) if short else c for c in classes]
    ax.set_xticks(range(len(lab)), lab, rotation=90, fontsize=5.6 if len(lab) > 25 else 7)
    ax.set_yticks(range(len(lab)), lab, fontsize=5.6 if len(lab) > 25 else 7)
    ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.grid(False)
    for i in range(len(lab)):
        for j in range(len(lab)):
            if cm[i, j] and (i != j or len(lab) <= 25):
                ax.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=4.6 if len(lab) > 25 else 6,
                        color="white" if norm[i, j] > 0.6 else "#b03030" if i != j else "#222")
    return save(f, name)


def fig_yield_baselines():
    r = yld["results"]
    keys = ["LightGBM (this model)", "Baseline: last year's yield", "Baseline: mean of previous 3 years",
            "Baseline: national crop mean"]
    f, axs = plt.subplots(1, 2, figsize=(8, 2.4))
    lab = ["LightGBM", "Last year", "3-yr mean", "National mean"]
    for ax, m, t in zip(axs, ["mae_t_ha", "r2"], ["MAE (t/ha) - lower is better", "R² - higher is better"]):
        v = [r[k][m] for k in keys]
        ax.bar(lab, v, color=[GREEN] + ["#b7c4bc"] * 3, width=0.6)
        for i, x in enumerate(v):
            ax.text(i, x, f"{x:.3f}", ha="center", va="bottom", fontsize=7)
        ax.set_title(t, fontsize=8.5, loc="left"); ax.grid(axis="x", visible=False)
        ax.tick_params(axis="x", labelsize=7.5)
    return save(f, "yield_baselines.png")


def fig_yield_per_crop():
    pc = yld["per_crop_test"][:14]
    f, ax = plt.subplots(figsize=(7.5, 3.6))
    lab = [r["crop"] for r in pc][::-1]
    ax.barh(lab, [r["mape_median_pct"] for r in pc][::-1], color=GREEN, height=0.6)
    for i, r in enumerate(pc[::-1]):
        ax.text(r["mape_median_pct"] + 0.3, i, f"{r['mape_median_pct']:.1f}%  (n={r['rows']:,})", va="center", fontsize=6.8)
    ax.set_xlabel("median absolute % error on the test years"); ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(r["mape_median_pct"] for r in pc) * 1.35)
    return save(f, "yield_per_crop.png")


def fig_leaf_history():
    h = [x for x in leaf["history"] if "val_acc" in x]
    f, ax = plt.subplots(1, 2, figsize=(8, 2.4))
    ep = [x["epoch"] for x in h]
    ax[0].plot(ep, [x["train_loss"] for x in h], color=S1, lw=2, marker="o", ms=4)
    ax[0].set_title("Training loss", fontsize=8.5, loc="left"); ax[0].set_xlabel("epoch")
    ax[1].plot(ep, [x["val_acc"] * 100 for x in h], color=GREEN, lw=2, marker="o", ms=4, label="accuracy")
    ax[1].plot(ep, [x["val_macro_recall"] * 100 for x in h], color=S2, lw=2, marker="o", ms=4, label="macro recall")
    ax[1].set_title("Validation (%)", fontsize=8.5, loc="left"); ax[1].set_xlabel("epoch")
    ax[1].legend(fontsize=7, frameon=False)
    return save(f, "leaf_history.png")


def fig_leaf_samples():
    picks = ["Apple___Apple_scab", "Apple___healthy", "Corn___Common_rust", "Grape___Black_rot",
             "Orange___Haunglongbing_(Citrus_greening)", "Peach___Bacterial_spot", "Potato___Early_blight",
             "Potato___Late_blight", "Tomato___Early_blight", "Tomato___Leaf_Mold",
             "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Background_without_leaves"]
    f, axs = plt.subplots(3, 4, figsize=(8, 6.4))
    for ax, c in zip(axs.flat, picks):
        imgs = sorted((LEAF_DIR / c).iterdir())
        ax.imshow(PILImage.open(imgs[min(7, len(imgs) - 1)]).convert("RGB").resize((256, 256)))
        ax.set_title(c.replace("___", "\n").replace("_", " ")[:44], fontsize=7)
        ax.axis("off")
    f.tight_layout()
    return save(f, "leaf_samples.png")


def fig_leaf_class_counts():
    counts = {c: sum(1 for p in (LEAF_DIR / c).iterdir()) for c in leaf["classes"]}
    items = sorted(counts.items(), key=lambda kv: kv[1])
    f, ax = plt.subplots(figsize=(7.5, 6.2))
    ax.barh([k.replace("___", ": ").replace("_", " ")[:46] for k, _ in items], [v for _, v in items],
            color=GREEN, height=0.65)
    ax.tick_params(axis="y", labelsize=6.3); ax.set_xlabel("images (non-augmented set)")
    ax.axvline(1000, color=S2, lw=1, ls="--"); ax.text(1030, 0.5, "1,000: augmented set tops classes up to here",
                                                       fontsize=6.5, color=S2)
    ax.grid(axis="y", visible=False)
    return save(f, "leaf_counts.png")


def fig_leaf_recall():
    pr = sorted(leaf["per_class_recall"].items(), key=lambda kv: kv[1])[:15]
    f, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.barh([k.replace("___", ": ").replace("_", " ")[:46] for k, _ in pr], [v * 100 for _, v in pr],
            color=GREEN, height=0.6)
    for i, (_, v) in enumerate(pr):
        ax.text(v * 100 + 0.02, i, f"{v * 100:.2f}", va="center", fontsize=6.8)
    ax.set_xlim(min(v for _, v in pr) * 100 - 1, 100.6); ax.tick_params(axis="y", labelsize=6.8)
    ax.set_xlabel("test recall (%) - the 15 hardest classes"); ax.grid(axis="y", visible=False)
    return save(f, "leaf_recall.png")


def fig_crop_profiles():
    prof = crop["crop_profiles"]
    feats = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    cs = sorted(prof)
    mat = np.array([[prof[c][f]["median"] for f in feats] for c in cs])
    norm = (mat - mat.min(0)) / (mat.max(0) - mat.min(0))
    f, ax = plt.subplots(figsize=(6.4, 6.6))
    ax.imshow(norm, cmap="Greens", aspect="auto")
    ax.set_xticks(range(len(feats)), feats); ax.set_yticks(range(len(cs)), cs); ax.grid(False)
    for i in range(len(cs)):
        for j in range(len(feats)):
            ax.text(j, i, f"{mat[i, j]:.0f}" if feats[j] != "ph" else f"{mat[i, j]:.1f}", ha="center",
                    va="center", fontsize=6.3, color="white" if norm[i, j] > 0.6 else "#222")
    ax.set_title("Median value per crop (colour = position within the feature's range)", fontsize=8, loc="left")
    return save(f, "crop_profiles.png")


# ---------------------------------------------------------------- document
def fig_fert_comparison():
    rows = fert["comparison"]
    labels = [f"{r['model']}\n({r['features']})" for r in rows]
    vals = [r["cv_accuracy_mean"] * 100 for r in rows]
    err = [r["cv_accuracy_std"] * 100 for r in rows]
    best = fert["chosen"]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    cols = [GREEN if (r["model"], r["features"]) == (best["model"], best["features"]) else
            ("#9cc9ad" if r["features"] == "N, P, K" else "#d9c58e") for r in rows]
    ax.barh(range(len(rows)), vals, xerr=err, color=cols, capsize=3)
    ax.set_yticks(range(len(rows)), labels, fontsize=7); ax.invert_yaxis()
    ax.set_xlabel("5x5 repeated cross-validation accuracy (%)"); ax.set_xlim(0, 105)
    for i, v in enumerate(vals):
        ax.text(min(v + 1, 101), i, f"{v:.1f}", va="center", fontsize=7)
    return save(fig, "fert_comparison.png")


def fert_outcomes():
    """Run the deployed fertiliser step on every row of the crop dataset (as the full analysis does)."""
    import csv
    from collections import Counter
    from app import fertiliser
    profiles = crop["crop_profiles"]
    rows = list(csv.DictReader(open(ROOT / "app" / "data" / "crop_samples.csv", encoding="utf-8")))
    out = Counter(fertiliser.recommend({"basis": "crop_profile", "crop": r["label"], "N": r["N"], "P": r["P"], "K": r["K"]},
                                       profiles)["category"] for r in rows)
    return len(rows), out


def fig_fert_outcomes(n, out):
    order = [k for k, _ in out.most_common()]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(order, [out[k] / n * 100 for k in order], color=[S2 if k == "No fertiliser needed" else GREEN for k in order])
    ax.set_ylabel("% of the 2,200 soil samples"); ax.tick_params(axis="x", labelsize=8)
    for i, k in enumerate(order):
        ax.text(i, out[k] / n * 100 + 0.5, f"{out[k] / n * 100:.0f}%", ha="center", fontsize=7)
    return save(fig, "fert_outcomes.png")


def build():
    figs = {
        "arch": fig_architecture(), "crop_cmp": fig_crop_comparison(),
        "crop_imp": fig_importance(crop["permutation_importance"], "crop_importance.png",
                                   "permutation importance (% accuracy lost when shuffled)"),
        "crop_cm": fig_confusion(crop["confusion_matrix"], crop["classes"], "crop_confusion.png", 6.6),
        "crop_prof": fig_crop_profiles(),
        "y_base": fig_yield_baselines(), "y_crop": fig_yield_per_crop(),
        "y_imp": fig_importance(yld["importance_gain"], "yield_importance.png", "% of total split gain",
                                labels=YIELD_LABELS),
        "l_hist": fig_leaf_history(), "l_samp": fig_leaf_samples(), "l_cnt": fig_leaf_class_counts(),
        "l_rec": fig_leaf_recall(),
        "l_cm": fig_confusion(leaf["confusion_matrix"], leaf["classes"], "leaf_confusion.png", 8,
                              short=lambda c: c.replace("___", ":").replace("_", " ")[:24]),
        "f_cmp": fig_fert_comparison(),
    }
    f_n, f_out = fert_outcomes()
    figs["f_out"] = fig_fert_outcomes(f_n, f_out)
    from app import fertiliser as fert_mod
    f_ex = fert_mod.recommend({"basis": "crop_profile", "crop": "mothbeans", "N": 36, "P": 43, "K": 24, "ph": 3.51},
                              crop["crop_profiles"])
    s = []
    # ---- cover
    s += [Spacer(1, 30 * mm), P("AgriSense AI", ParagraphStyle("t", parent=h1, fontSize=34, leading=40)),
          P("Smart Farming Intelligence - model and system report",
            ParagraphStyle("st", parent=h2, fontSize=15, textColor=colors.HexColor(DARK))),
          Spacer(1, 6 * mm),
          P("NIIT University - Software Engineering (CS 301) project"),
          P("Live at <b>https://ai.software.microeagle.online</b>"),
          P(f"Report generated {time.strftime('%d %B %Y')} from the trained model cards. Every figure "
            "below is read from the files the training scripts wrote; nothing is typed in by hand."),
          Spacer(1, 10 * mm)]
    lt = leaf["test"]
    s.append(table([
        ["Component", "Method", "Headline result (held-out data)"],
        ["Crop recommendation", f"{crop['selected_model']} (best of 5 by 5-fold CV)",
         f"<b>{pct(crop['test_accuracy'])}</b> test accuracy, macro F1 {crop['test_macro_f1']:.4f}"],
        ["Yield prediction", "LightGBM on the correction to the 3-year district mean",
         f"<b>R² {yld['results']['LightGBM (this model)']['r2']}</b>, MAE "
         f"{yld['results']['LightGBM (this model)']['mae_t_ha']} t/ha on unseen years"],
        ["Leaf disease detection", "EfficientNet-B0, GPU fine-tuned, calibrated",
         f"<b>{pct(lt['accuracy'])}</b> test accuracy, {pct(lt['accuracy_when_answered'])} when it answers"],
        ["Fertiliser recommendation", f"{fert['chosen']['model']} on N, P, K (best of 8 by 5x5 repeated CV)",
         f"<b>{pct(fert['chosen']['cv_accuracy_mean'])}</b> cross-validated accuracy on {fert['rows']} rows; names a fertiliser, never a dose"],
        ["AI assistant", "Mistral chat API, grounded in the user's farm data", "Answers in 15 languages"],
    ], [0.24, 0.38, 0.38]))
    s.append(PageBreak())

    # ---- 1. overview
    s += [P("1. What the system does", h1),
          P("AgriSense AI is a web dashboard for Indian farmers. A farmer signs up, adds farms with a map "
            "location, and then uses four decision tools plus live weather and soil data. Every result is "
            "stored in the farmer's own account so it can be reviewed later, exported to PDF or CSV, and "
            "discussed with the AI assistant."),
          table([["Page", "What it gives the farmer"],
                 ["Overview", "Farm summary, live weather, latest predictions, district production trend"],
                 ["Crop Recommendation", "Best crop for the soil N-P-K, pH and climate, with top-3 alternatives and a suitability radar"],
                 ["Yield Prediction", "Expected t/ha and total tonnes with an 80% interval, history chart and a SHAP explanation"],
                 ["Fertiliser Recommendation", "Which nutrients are short and the fertiliser the model suggests (e.g. Urea, DAP, 10-26-26), with its grade and confidence"],
                 ["Plant Disease Detection", "Disease name from a leaf photo, cause, symptoms and next steps; refuses unclear photos"],
                 ["AI Farming Assistant", "Chat in English or Hindi; knows the farmer's farms and recent predictions"],
                 ["Weather Insights", "7-day forecast and alerts (Open-Meteo), plus daily history (NASA POWER)"],
                 ["Soil Health", "Modelled pH, organic carbon, nitrogen, clay, sand, bulk density at 6 depths (SoilGrids)"],
                 ["Farm Management", "Farms with map pin, area, soil type, irrigation, crop history"],
                 ["Prediction History / Reports", "Every past result, filters, charts, PDF and CSV export"],
                 ["Settings", "Profile, language, units, password, delete account"]], [0.27, 0.73]),
          Spacer(1, 4 * mm), P("1.1 Architecture", h2), fig(figs["arch"], 1.0,
                                                           "Figure 1 - Request flow from the browser to the models and data sources."),
          P("The browser talks only to our FastAPI server. The server runs the three trained models locally "
            "(no external ML service), calls the public weather and soil services, and uses the Mistral API "
            "only for the chat assistant. Results are cached in SQLite so repeated look-ups are fast."),
          PageBreak()]

    # ---- 2. datasets
    ap = leaf.get("augmented_set")
    s += [P("2. Datasets supplied and how each was used", h1),
          table([["Dataset", "Size", "Used for", "How it was used"],
                 ["Crop_recommendation.csv", "2,200 rows, 22 crops x 100", "Crop model",
                  "80/20 stratified split to measure accuracy; the deployed model is refit on all 2,200 rows"
                  if crop.get("deployed_fit") else "80/20 stratified split (1,760 train / 440 test)"],
                 ["India Agriculture Crop Production (archive.zip)", "345,407 raw rows, 1997-2020",
                  "Yield model, analytics", f"{yld['rows_clean']:,} rows after cleaning; trained on years before "
                  "2017-18 and tested on 2017-18 onward" + ("; deployed model refit on every year"
                                                          if yld.get("deployed_fit") else "")],
                 ["Plant leaf diseases - non-augmented", "55,448 images, 39 classes", "Leaf model",
                  "Stratified 70/15/15 train / validation / test split"],
                 ["Plant leaf diseases - augmented", "61,486 files", "Leaf model" if ap else "Not used",
                  (f"{ap['identical_to_an_original']:,} files are byte-identical to originals; the "
                   f"{ap['synthetic']:,} synthetic copies were linked to their source photo and used for training "
                   "only when that photo was in training") if ap else "Copies of the same photos (leak risk)"],
                 ["Six soil zips (pH, N, SOC, clay, sand, bulk density)", "metadata records", "Soil page",
                  "They hold no values (XML + index page). The same SoilGrids layers are read live instead"],
                 ["stitch_agrisense...zip", "UI export", "Design", "Visual reference for the dashboard"]],
                [0.24, 0.17, 0.13, 0.46]),
          P("2.1 Leaf dataset class balance", h2),
          fig(figs["l_cnt"], 0.92, "Figure 2 - Images per class. The largest class is 36x the smallest, so "
                                   "training uses class-weighted loss."),
          PageBreak()]

    # ---- 3. crop
    df = crop.get("deployed_fit")
    s += [P("3. Crop recommendation model", h1),
          P("<b>Question it answers:</b> given the soil's nitrogen, phosphorus and potassium values, the soil pH, "
            "temperature, humidity and rainfall, which of 22 crops suits the field best?"),
          P("3.1 Input features", h2),
          table([["Feature", "Meaning", "Unit"],
                 ["N, P, K", "Soil nutrient values as published in the dataset", "dataset ratio (often read as kg/ha)"],
                 ["temperature", "Average air temperature", "°C"], ["humidity", "Relative humidity", "%"],
                 ["ph", "Soil pH (acidity)", "0-14"], ["rainfall", "Rainfall", "mm"]], [0.18, 0.52, 0.30]),
          P("On the Crop page the farmer can fill temperature, humidity and rainfall from the live forecast "
            "with one click."),
          P("3.2 Model selection", h2),
          P("Five different algorithms were trained. The winner was chosen <b>before</b> looking at the test set, "
            "using 5-fold cross-validation accuracy on the training part only. The test set is reported, not "
            "used for selection."),
          fig(figs["crop_cmp"], 0.95, "Figure 3 - Cross-validation and test accuracy of the five candidates."),
          table([["Model", "CV accuracy", "Test accuracy", "Test macro F1", "Train time (s)"]] +
                [[r["model"], pct(r["cv_accuracy_mean"]) + f" ± {r['cv_accuracy_std'] * 100:.2f}",
                  pct(r["test_accuracy"]), f"{r['test_macro_f1']:.4f}", f"{r['train_seconds']}"]
                 for r in crop["comparison"]], [0.3, 0.2, 0.17, 0.17, 0.16]),
          P(f"<b>Selected: {crop['selected_model']}</b> - an ensemble of 400 decision trees. Each tree votes "
            "for a crop and the share of votes becomes the confidence shown to the farmer. It handles "
            "non-linear thresholds (for example rice needs very high humidity and rainfall) without scaling the inputs."),
          ]
    if df:
        s.append(P(f"<b>Deployed fit:</b> after measuring accuracy, the same model was refit on all "
                   f"{df['rows']:,} rows so no data is left unused. The accuracy above is the honest estimate for it."))
    s += [PageBreak(), P("3.3 Which inputs matter", h2),
          fig(figs["crop_imp"], 0.9, "Figure 4 - Permutation importance: how much test accuracy drops when one "
                                     "feature is shuffled."),
          P("Humidity, nitrogen and rainfall carry most of the signal. pH and temperature barely change the "
            "answer in this dataset because most crops share similar ranges for them."),
          P("3.4 Errors on the test set", h2),
          fig(figs["crop_cm"], 0.78, "Figure 5 - Confusion matrix (rows = true crop, columns = predicted)."),
          PageBreak(), P("3.5 What each crop needs (from the dataset)", h2),
          fig(figs["crop_prof"], 0.8, "Figure 6 - Median conditions per crop. The app also uses each crop's "
                                      "10th-90th percentile band for the suitability radar and fertiliser checks."),
          PageBreak()]

    # ---- 4. yield
    r = yld["results"]
    ydf = yld.get("deployed_fit")
    s += [P("4. Crop yield prediction model", h1),
          P("<b>Question it answers:</b> for a district, crop, season and year, how many tonnes per hectare "
            "should a farmer expect, and how many tonnes for their area?"),
          P("4.1 Data cleaning", h2),
          *bullets(["Kept crops measured in tonnes (cotton in bales and coconut in nuts cannot be compared).",
                    "Dropped rows without production or with less than 1 ha of area.",
                    "Removed impossible yields per crop (outside the 0.5-99.5 percentile; the raw file even "
                    "contains 43,958 t/ha).",
                    "Summed duplicate rows for the same district, crop, season and year.",
                    f"Result: <b>{yld['rows_clean']:,}</b> clean records."]),
          P("4.2 Features the model uses", h2),
          table([["Feature", "What it is"]] + [[YIELD_LABELS.get(f, f), YIELD_EXPLAIN.get(f, "")]
                                                for f in yld["features"]], [0.28, 0.72]),
          P("The dataset has <b>no weather or soil columns</b>, so the yield model does not use them and the "
            "app says this next to every prediction."),
          P("4.3 Target design", h2),
          P("Instead of predicting tonnes per hectare from scratch, the model predicts the <b>correction to the "
            "recent normal</b>: log(1 + yield) minus log(1 + base), where the base is the district's 3-year "
            "average, falling back to the long-run district average, then last year's state average, then the "
            "national crop average. This made it beat the strong \"same as last year\" baseline on average error."),
          P("4.4 Validation that mimics real use", h2),
          P(f"Training used crop years before 2017-18 ({yld['rows_train']:,} records); testing used 2017-18 to "
            f"2020-21 ({yld['rows_test']:,} records), years the model never saw. A random split would leak "
            "the future into training and overstate accuracy."),
          fig(figs["y_base"], 1.0, "Figure 7 - The model against three simple baselines on the test years."),
          table([["Method", "R²", "MAE (t/ha)", "Median % error"]] +
                [[k, f"{v['r2']}", f"{v['mae_t_ha']}", f"{v['mape_median_pct']}%"] for k, v in r.items()],
                [0.46, 0.14, 0.18, 0.22]),
          P("Honest note: on <i>median</i> percentage error, \"same as last year\" is slightly better (12.07% vs "
            "13.62%); the model wins on average error and R² because it avoids the baseline's large misses."),
          ]
    if ydf:
        s.append(P(f"<b>Deployed fit:</b> after the test above, the model was refit on every year "
                   f"({ydf['rows']:,} records, {ydf['iterations']} boosting rounds) so the latest seasons inform "
                   "predictions. The figures above remain the honest accuracy estimate."))
    s += [PageBreak(), P("4.5 Feature importance and explanations", h2),
          fig(figs["y_imp"], 0.9, "Figure 8 - Share of split gain per feature."),
          P("For every single prediction the app also shows a <b>SHAP</b> breakdown (LightGBM's exact "
            "per-feature contributions), so the farmer sees which inputs pushed the estimate up or down."),
          P("4.6 Uncertainty", h2),
          P(f"The 80% interval shown with each prediction comes from the real spread of errors on the test years "
            f"(per crop where there is enough data). Coverage on the test set: "
            f"<b>{yld['interval_80']['test_coverage'] * 100:.0f}%</b>."),
          P("4.7 Accuracy by crop", h2),
          fig(figs["y_crop"], 0.92, "Figure 9 - Median % error for the 14 most common crops in the test years."),
          PageBreak()]

    # ---- 5. leaf
    sp = leaf["split"]
    ldf = leaf.get("deployed_fit")
    s += [P("5. Plant leaf disease detection model", h1),
          P("<b>Question it answers:</b> from a photo of one leaf, which of 38 crop-disease classes (14 crops) is it, "
            "or is there no leaf at all?"),
          fig(figs["l_samp"], 0.92, "Figure 10 - Example training images from 12 of the 39 classes."),
          P("5.1 Architecture and training", h2),
          *bullets([f"{leaf['architecture']}.",
                    "Transfer learning: starts from ImageNet weights, the final layer is replaced with a 39-class layer, "
                    "and the whole network is fine-tuned.",
                    "Images resized to 224x224; training adds random crops, flips, rotations and colour changes so the "
                    "model does not memorise lighting or orientation.",
                    "Loss: class-weighted cross-entropy with label smoothing; optimiser AdamW with a one-cycle "
                    "learning-rate schedule; mixed precision on the NVIDIA GPU.",
                    f"Split: {sp['train']:,} train" + (f" + {sp['train_synthetic']:,} synthetic" if 'train_synthetic' in sp else "")
                    + f" / {sp['val']:,} validation / {sp['test']:,} test images (stratified, seed 42)."]),
          fig(figs["l_hist"], 1.0, "Figure 11 - Training loss and validation scores per epoch."),
          PageBreak(), P("5.2 Results on the held-out test images", h2),
          table([["Measure", "Value", "Meaning"],
                 ["Accuracy", pct(lt["accuracy"]), "share of test images classified correctly"],
                 ["Macro recall", pct(lt["macro_recall"]), "average of per-class recall (small classes count equally)"],
                 ["Macro F1", f"{lt['macro_f1']:.4f}", "balance of precision and recall"],
                 ["Calibration error before / after", f"{lt['ece_before_T']:.4f} / {lt['ece_after_T']:.4f}",
                  "how far the confidence is from the true hit-rate (0 = perfect)"],
                 ["Answers given", pct(lt["answered_fraction"]), f"photos confident enough (≥ {leaf['threshold'] * 100:.0f}%) to answer"],
                 ["Accuracy when it answers", pct(lt["accuracy_when_answered"]), "accuracy on those photos"]],
                [0.3, 0.2, 0.5]),
          P("5.3 Calibrated confidence and refusing to guess", h2),
          P(f"Raw neural-network confidence is usually too high. A single <b>temperature</b> (T = {leaf['temperature']}) "
            "was fitted on the validation set so that \"90% confident\" really means right about 90% of the time. "
            f"The app then only names a disease when the calibrated confidence is at least "
            f"<b>{leaf['threshold'] * 100:.0f}%</b>; otherwise it asks for a clearer photo. Rule used: {leaf['threshold_rule']}."),
          fig(figs["l_rec"], 0.92, "Figure 12 - The 15 classes with the lowest test recall."),
          ]
    if ap:
        s += [P("5.4 Using the augmented set without leaking test images", h2),
              P(f"The augmented download repeats the {ap['identical_to_an_original']:,} originals and adds "
                f"{ap['synthetic']:,} synthetic images (rotations, flips, colour and noise changes) to classes "
                "with fewer than 1,000 photos. File names do not say which photo each copy came from, so every copy "
                "was linked to its most similar original by image features (median similarity "
                f"{ap['cosine_similarity_to_source']['median']}). Copies of validation or test photos were kept out "
                f"of training ({sp.get('synthetic_dropped_leak_guard', 0):,} dropped), so the scores above are not "
                "inflated.")]
    if ldf:
        s.append(P(f"<b>Deployed fit:</b> after evaluation the network was retrained with the same recipe on "
                   f"<b>all {ldf['images']:,} images</b> ({ldf['originals']:,} originals + {ldf['synthetic']:,} "
                   "synthetic). No images remain to test that exact network, so the figures above are the honest "
                   "estimate, and it keeps the evaluated temperature and threshold."))
    s += [P("5.5 Limitation", h2), P(leaf["limitations"]), PageBreak(),
          P("5.6 Full confusion matrix", h2),
          fig(figs["l_cm"], 1.0, "Figure 13 - Test confusion matrix (off-diagonal numbers in red are mistakes)."),
          P("5.7 Serving", h2),
          P("The trained network is exported to a single ONNX file and run with ONNX Runtime on the server's CPU "
            "(no GPU needed in production). Each photo is also scored flipped and the two results are averaged. "
            "For each disease the app shows the cause, symptoms and next steps from a curated table."),
          PageBreak()]

    # ---- 6. fertiliser, live data, assistant
    fc = fert["chosen"]
    imp = fert["permutation_importance_all_features"]
    s += [P("6. Fertiliser recommendation", h1),
          P(f"The fertiliser is named by a model trained on <b>{fert['dataset']}</b>: {fert['rows']} rows, each with "
            "temperature, humidity, moisture, soil type, crop type, N, P, K and the fertiliser used. It suggests "
            "one of seven fertilisers. It never states a dose - that depends on a soil test and the local KVK."),
          table([["Fertiliser", "Grade (N-P-K %)", "Supplies", "Rows"]] +
                [[k, v["grade"], v["supplies"], str(fert["class_counts"].get(k, 0))] for k, v in fert["grades"].items()],
                [0.16, 0.18, 0.54, 0.12]),
          P("6.1 Model selection", h2),
          P("With only 99 rows a single test split is noisy, so models were compared by 5-fold cross-validation "
            "repeated 5 times (25 fits each), on two feature sets: N, P, K alone, and all eight columns."),
          fig(figs["f_cmp"], 0.95, "Figure 14 - Cross-validated accuracy (bars) and its spread (whiskers). Green: "
              "the chosen model; light green: N, P, K only; sand: all features."),
          P(f"<b>{fc['model']} on {fc['features']}</b> was chosen: {pct(fc['cv_accuracy_mean'])} cross-validated "
            f"accuracy (spread {pct(fc['cv_accuracy_std'])}), {pct(fc['holdout_accuracy'])} on a 20% hold-out. "
            "Adding the other columns made every model worse - K-nearest neighbours fell to "
            f"{pct(min(r['cv_accuracy_mean'] for r in fert['comparison']))}. The deployed model was refit on all rows."),
          table([["Column", "Permutation importance (all-features random forest)"]] +
                [[r["feature"], f"{r['importance']:.3f}"] for r in imp], [0.4, 0.6]),
          P("Shuffling temperature, humidity, moisture, soil type or crop type does not change a single prediction: in "
            "this dataset the fertiliser is decided by N, P and K alone."),
          P("6.2 From soil values to the model's input", h2),
          P("The dataset's N, P and K describe the nutrient the farmer needs to <i>supply</i> (Urea rows have high N and "
            "zero P and K) on the dataset's own scale (N and P 0-42, K 0-19). A soil sample or soil test reports what is "
            "already <i>in</i> the soil, on a different scale. The app bridges the two in a fixed, documented way:"),
          *bullets(["Each nutrient is compared with a <b>typical level</b>: the recommended crop's median in the crop "
                    "dataset, or the middle of the Soil Health Card medium band for a lab soil test (N 420, P 17.5, "
                    "K 195 kg/ha). Shortfalls under 5% count as none.",
                    "The shortfalls keep their <b>proportions</b>: the most-short nutrient is placed at the top of its "
                    "range in the fertiliser dataset and the others scale with it. This tells the model which nutrients "
                    "are needed and in what proportion, not how much.",
                    "Only fertilisers that supply every nutrient making up at least a quarter of the largest shortfall "
                    "are considered; the model's highest-ranked one among them is suggested. Its own first choice is "
                    "shown if it differs.",
                    "If nothing is short, no fertiliser is named (\"No fertiliser needed\").",
                    "Numbers already on the fertiliser dataset's scale (for example a row of the dataset) go to the model "
                    "unchanged - all 99 rows are reproduced exactly."]),
          P(f"<b>Worked example</b> (the full analysis on the phone): soil sample N 36, P 43, K 24 -> crop model "
            f"Mothbeans. Typical for mothbeans: N {f_ex['typical']['N']:g}, P {f_ex['typical']['P']:g}, "
            f"K {f_ex['typical']['K']:g}. Only P is short ({f_ex['shortfall']['P'] * 100:.0f}%), so the model input "
            f"is N {f_ex['need']['N']:g}, P {f_ex['need']['P']:g}, K {f_ex['need']['K']:g} and the suggestion is "
            f"<b>{f_ex['fertiliser']['name']} ({f_ex['fertiliser']['grade']})</b> at "
            f"{pct(f_ex['fertiliser']['confidence'])} confidence."),
          table([["Short nutrient(s)", "Typical suggestion"], ["N only", "Urea"], ["P only", "DAP"],
                 ["K only", "10-26-26"], ["N and P", "28-28"], ["P and K", "14-35-14"],
                 ["N, P and K", "a complex that supplies all three (10-26-26 / 17-17-17)"]], [0.4, 0.6]),
          fig(figs["f_out"], 0.92, f"Figure 15 - What the full analysis suggests across all {f_n:,} soil samples of the "
              f"crop dataset ({f_out['No fertiliser needed'] / f_n * 100:.0f}% need nothing)."),
          P("6.3 Limitations", h2),
          *bullets(["99 rows is very small; the perfect score reflects a dataset whose labels follow N, P and K almost "
                    "exactly, not proven field performance.",
                    "The bridge from soil values to a nutrient need is an approximation between two datasets with "
                    "different units. It is shown with every result.",
                    "When the model is less than 50% sure the result says so and points the farmer to the assistant "
                    "and a soil test."]),
          P("7. Live weather and soil data", h1),
          table([["Source", "What we read", "Notes"],
                 ["Open-Meteo", "Current weather, 7-day forecast, alerts, place search", "Free, no key; cached"],
                 ["NASA POWER", "Daily historical temperature, rain, humidity, solar radiation", "Gridded estimates, labelled as such"],
                 ["ISRIC SoilGrids 2.0 (WCS)", "pH, organic carbon, nitrogen, clay, sand, bulk density at 6 depths with 90% ranges",
                  "Modelled at 250 m; labelled \"not a lab test\""]], [0.24, 0.46, 0.30]),
          P("8. AI farming assistant - which API it uses", h1),
          P("The assistant uses the <b>Mistral AI chat API</b> (api.mistral.ai). It tries "
            "<b>ministral-14b</b> first and falls back to <b>ministral-8b</b> and <b>ministral-3b</b> if the "
            "service is busy. The API key lives only on the server (config/api_keys.env, never in the browser "
            "or the code repository)."),
          *bullets(["Every request carries a system prompt: farming topics only, reply in the user's language "
                    "(English or Hindi), never invent prices, schemes or chemical doses.",
                    "It also carries the signed-in farmer's own context: farms, recent predictions and the models' "
                    "measured accuracy, so answers refer to their district and results.",
                    "Fixed reference scales (pH bands, Soil Health Card ranges) are included so wording stays "
                    "consistent with the rest of the app.",
                    "Conversations are saved per user; they can be renamed, bookmarked or deleted.",
                    "Our own server also exposes this as an API: POST /api/chat (signed-in users only)."]),
          PageBreak()]

    # ---- 9. accounts & database
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)\(", appdb.SCHEMA)
    s += [P("9. Accounts, security and stored data", h1),
          *bullets(["Passwords are hashed with <b>scrypt</b> and a per-user random salt; they cannot be read back.",
                    "Sessions are random tokens stored as SHA-256 hashes, sent in an HttpOnly, Secure cookie.",
                    "Every farm, prediction and chat is tied to its owner; one user can never read another's data.",
                    "Users can export their data and delete their account from Settings."]
                   ),
          ]
    if OTP:
        s += [P("9.1 E-mail one-time codes (OTP)", h2),
              P("Signing up and signing in both need a 6-digit code sent to the user's e-mail, and the same code "
                "flow resets a forgotten password."),
              table([["Step", "What happens"],
                     ["Sign-up", "The form is checked and the password hashed, but <b>no account is created</b> until "
                                 "the code from the e-mail is entered."],
                     ["Sign-in", "Correct password -> a code is e-mailed -> the session starts only after the code."],
                     ["Forgot password", "E-mail + new password -> code -> new password active, all old sessions "
                                         "ended. Unknown addresses get the same answer, so accounts cannot be discovered."],
                     ["Delivery", "The server calls our own n8n workflow <b>AgriSense_OTP_Delivery</b> (a clone of the "
                                  "Saarthi OTP chain) over the private Docker network with a shared secret; n8n sends "
                                  "the e-mail from support@visioncoders.online. Success is read from the reply body."],
                     ["Limits", "Codes expire in 10 minutes, 5 wrong tries cancel the code, 60 s between resends, "
                                "at most 6 codes per address per hour. Codes are stored only as SHA-256 hashes."]],
                    [0.22, 0.78])]
    s += [P("9.2 What is stored", h2),
          table([["Table", "Contents"],
                 ["users", "Profile, role, language, scrypt password hash, e-mail verified time, last sign-in"],
                 ["sessions", "SHA-256 of each session token and its expiry"],
                 ["farms", "Name, location (lat/lon), area, soil, irrigation, crop history"],
                 ["predictions", "Every crop, yield, fertiliser and disease result with its inputs and model version"],
                 ["uploads", "Every leaf photo uploaded (disease page or chat), linked to its prediction or chat"],
                 ["chats", "Assistant conversations"],
                 ["otp_challenges", "Code requests: purpose, hashed code, attempts, expiry (no plain codes)"],
                 ["auth_events", "Audit log: sign-ups, sign-ins, failed passwords, codes sent / wrong, resets, "
                                 "sign-outs, with IP and browser"],
                 ["cache", "Cached weather and soil responses"],
                 ["production", "Cleaned crop-production history used for analytics and yield look-ups"]],
                [0.22, 0.78]),
          P("Deleting an account removes all of that user's rows from every table.", small),
          P("10. Deployment", h1),
          *bullets(["Docker container <b>agrisense</b> on the project VPS, bound to 127.0.0.1:8150.",
                    "Traefik reverse proxy serves <b>https://ai.software.microeagle.online</b> with a Let's Encrypt "
                    "certificate.",
                    "User data lives in a Docker volume, so rebuilding the app never deletes accounts.",
                    "The API key file is mounted read-only into the container.",
                    "Interactive API documentation is available at /api/docs."]),
          P("11. Limitations", h1),
          *bullets(["Leaf images are lab photos of single leaves; real field photos may score lower and this is "
                    "not measured.",
                    "Yield is district-level and has no weather or soil inputs, so a local drought or pest outbreak "
                    "is not seen by the model.",
                    "The crop dataset is small (100 rows per crop) and very clean, which is why accuracy is so high; "
                    "real soil tests are noisier.",
                    "Soil values are modelled maps, not lab tests; NASA POWER history is a gridded estimate.",
                    "The fertiliser model learned from only 99 rows; turning soil values into a nutrient need is an "
                    "approximation between two datasets with different units."]),
          PageBreak()]

    # ---- 12. screenshots
    s.append(P("12. Application screenshots", h1))
    shots = [("01_login", "Sign-in page"), ("13_signup", "Sign-up form"),
             ("14_otp", "E-mail code step after sign-up or sign-in"), ("02_overview", "Overview dashboard"),
             ("03_crop", "Crop recommendation with result"), ("04_yield", "Yield prediction with SHAP explanation"),
             ("05_fertiliser", "Fertiliser recommendation"), ("06_disease", "Leaf disease detection"),
             ("12_assistant", "AI farming assistant"), ("07_weather", "Weather insights"),
             ("08_soil", "Soil health from SoilGrids"), ("11_farms", "Farm management"),
             ("10_history", "Prediction history"), ("09_reports", "Reports and analytics")]
    n = 14
    for key, title in shots:
        p = SHOTS / f"{key}.png"
        if not p.exists():
            continue
        im = PILImage.open(p)
        if im.height > im.width * 0.78:
            im = im.crop((0, 0, im.width, int(im.width * 0.78)))
            p = FIGS / f"shot_{key}.png"
            im.save(p)
        max_h = (A4[1] - 60 * mm) / 2
        w = W
        h = w * im.height / im.width
        if h > max_h:
            h = max_h
            w = h * im.width / im.height
        s.append(KeepTogether([Image(str(p), width=w, height=h), P(f"Figure {n} - {title}.", cap)]))
        n += 1

    # ---- appendix: API
    s += [PageBreak(), P("Appendix - server API endpoints", h1),
          P("All endpoints except sign-up, sign-in and public look-ups require a signed-in session.", small)]
    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    eps = re.findall(r'@app\.(get|post|put|delete|patch)\("([^"]+)"\)', main_src)
    s.append(table([["Method", "Path", "What it does"]] + [[m.upper(), p, EP_DOC.get(p + " " + m.upper(),
                    EP_DOC.get(p, ""))] for m, p in eps if p != "/"], [0.1, 0.34, 0.56]))

    def page(c, d):
        c.saveState()
        c.setFont("UI", 7.5)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(18 * mm, 10 * mm, "AgriSense AI - model and system report")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")
        c.restoreState()

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="AgriSense AI - model and system report",
                            author="AgriSense AI team")
    doc.build(s, onFirstPage=page, onLaterPages=page)
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


EP_DOC = {
    "/api/auth/register": "Create an account", "/api/auth/login": "Sign in with e-mail or phone and password",
    "/api/auth/logout": "Sign out (ends the session)", "/api/auth/otp/resend": "Send a new code (60 s gap)", "/api/auth/forgot": "Start a password reset by e-mail code", "/api/uploads/{upload_id}": "Download one of my uploaded leaf photos", "/api/me/activity": "My sign-in history", "/api/samples/crop": "Random real row of the crop dataset", "/api/samples/yield": "Random real district production record", "/api/samples/leaf": "Random dataset leaf photo + label", "/api/samples/leaf/{cls}/{name}": "Download a dataset leaf photo", "/api/auth/otp/start": "E-mail a one-time code",
    "/api/auth/otp/verify": "Check the code and finish sign-up / sign-in",
    "/api/me GET": "Current user's profile", "/api/me PUT": "Update profile and preferences",
    "/api/me/password": "Change password", "/api/me/delete": "Delete account and all its data",
    "/api/status": "Which models and services are available", "/api/models/{name}": "A model's card (metrics)",
    "/api/farms GET": "List my farms", "/api/farms POST": "Add a farm", "/api/farms/{fid} GET": "One farm",
    "/api/farms/{fid} PUT": "Edit a farm", "/api/farms/{fid} DELETE": "Delete a farm",
    "/api/crop/recommend": "Run the crop model", "/api/crop/info": "Crop profiles from the dataset",
    "/api/yield/options": "States, crops and seasons the yield model knows",
    "/api/yield/districts": "Districts of a state", "/api/yield/predict": "Run the yield model (with SHAP)",
    "/api/fertiliser": "Find nutrient shortfalls and run the fertiliser model", "/api/disease": "Run the leaf model on an uploaded photo",
    "/api/disease/classes": "Crops and diseases the leaf model knows", "/api/geocode": "Search a place name",
    "/api/weather": "Live forecast for a farm", "/api/weather/history": "NASA POWER daily history",
    "/api/soil": "SoilGrids profile for a farm", "/api/analytics/production": "District / state production series",
    "/api/predictions GET": "My prediction history", "/api/predictions/{pid} GET": "One prediction",
    "/api/predictions/{pid} DELETE": "Delete a prediction", "/api/overview": "Data for the Overview page",
    "/api/chats GET": "My assistant conversations", "/api/chats/{cid} GET": "One conversation",
    "/api/chats/{cid} PATCH": "Rename or bookmark", "/api/chats/{cid} DELETE": "Delete a conversation",
    "/api/chat": "Ask the assistant (Mistral API)", "/api/reports/csv": "Export my predictions as CSV",
    "/api/reports/pdf": "Export my predictions as PDF", "/api/public/states": "States list (no sign-in)",
    "/api/public/districts": "Districts list (no sign-in)", "/healthz": "Health check for Docker"}
YIELD_LABELS = {"State": "State", "District": "District", "Crop": "Crop", "Season": "Season",
                "log_area": "Area (log)", "lag1": "Last year's yield", "lag2": "Yield two years ago",
                "lag_trend": "Yield trend", "lag_mean3": "3-year average yield", "lag_count": "Years of history",
                "dist_crop_mean": "District long-run average", "state_crop_lag1": "State yield last year",
                "area_change": "Change in area"}
YIELD_EXPLAIN = {
    "State": "State name (categorical)", "District": "District name (categorical; 700+ districts)",
    "Crop": "Crop name (categorical)", "Season": "Kharif, Rabi, Whole Year, Summer, Autumn or Winter",
    "log_area": "log of the district's area under the crop (district scale, not the farm's)",
    "lag1": "District yield for this crop and season last year", "lag2": "Same, two years ago",
    "lag_trend": "Last year minus two years ago: is yield rising or falling?",
    "lag_mean3": "Average of the previous three years", "lag_count": "How many earlier years exist for this combination",
    "dist_crop_mean": "Average of all earlier years in the district (only past years, no leakage)",
    "state_crop_lag1": "Area-weighted state yield last year: captures region-wide good or bad seasons",
    "area_change": "Change in cultivated area since last year (log ratio)"}

if __name__ == "__main__":
    build()
