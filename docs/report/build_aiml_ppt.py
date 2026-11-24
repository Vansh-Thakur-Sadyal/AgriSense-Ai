"""AI and ML final-evaluation deck, built on the department's sample deck (its title style, teal mark,
page numbers and Times New Roman text are kept; the sample's guidance slides are replaced).
Usage: python build_aiml_ppt.py <sample.pptx> <out.pptx>"""
import copy
import json
import sys
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import content as C  # noqa: E402

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
FIGS = ROOT / "docs" / "figs"
AND = FIGS / "android"
MY = HERE / "out" / "figs"
F = json.loads((HERE / "out" / "aiml_facts.json").read_text(encoding="utf-8"))
M = ROOT / "app" / "models"
CROP = json.loads((M / "crop_model.json").read_text())
YLD = json.loads((M / "yield_model.json").read_text())
FERT = json.loads((M / "fertiliser_model.json").read_text())
LEAF = json.loads((M / "leaf_disease.json").read_text())
LOAD = json.loads((ROOT / "tests" / "load" / "results" / "summary.json").read_text())
YR = YLD["results"]
LT = LEAF["test"]
FC = FERT["chosen"]
LASTYR = "Baseline: last year's yield"
MEAN3 = "Baseline: mean of previous 3 years"

NAVY, TEAL, GREY = RGBColor(0x14, 0x2A, 0x4C), RGBColor(0x00, 0x91, 0x96), RGBColor(0x69, 0x73, 0x7D)
TINT, INK, WHITE = RGBColor(0xE8, 0xF4, 0xF4), RGBColor(0x22, 0x22, 0x22), RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xB9, 0xC4, 0xCF)
FONT = "Times New Roman"
COURSE = "Artificial Intelligence (CS 322)"
FACULTY = "Dr. Shweta R Malwe"


DATA_LINKS = {
    "Crop": ("Crop Recommendation Dataset (A. Ingle), Kaggle", "https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset"),
    "Yield": ("India Agriculture Crop Production, Kaggle (from data.gov.in)", "https://www.kaggle.com/datasets/pyatakov/india-agriculture-crop-production"),
    "Fertiliser": ("Fertilizer Prediction, Kaggle", "https://www.kaggle.com/datasets/gdabhishek/fertilizer-prediction"),
    "Leaf": ("Plant leaf diseases (39 classes), Mendeley Data, DOI 10.17632/tywbtsjrjv.1", "https://data.mendeley.com/datasets/tywbtsjrjv/1"),
}
PAPER_LINKS = [
    ("L. Breiman, Random Forests, Machine Learning 45, 2001", "https://doi.org/10.1023/A:1010933404324"),
    ("G. Ke et al., LightGBM: A Highly Efficient Gradient Boosting Decision Tree, NeurIPS 2017",
     "https://proceedings.neurips.cc/paper/2017/file/6449f44a102fde848669bdd9eb6b76fa-Paper.pdf"),
    ("M. Tan, Q. V. Le, EfficientNet: Rethinking Model Scaling for CNNs, ICML 2019", "https://arxiv.org/abs/1905.11946"),
    ("C. Guo et al., On Calibration of Modern Neural Networks, ICML 2017", "https://arxiv.org/abs/1706.04599"),
    ("G. Geetharamani, J. Arun Pandian, Plant leaf disease identification with a nine-layer deep CNN, Computers and Electrical Engineering 76, 2019",
     "https://doi.org/10.1016/j.compeleceng.2019.04.011"),
    ("D. P. Hughes, M. Salathe, An open access repository of images on plant health (PlantVillage), 2015", "https://arxiv.org/abs/1511.08060"),
]


def link_list(s, x, y, w, h, items, size=13):
    """Bulleted 'label' lines, each followed by its clickable URL."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for i, (label, url) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(5)
        pPr = p._p.get_or_add_pPr(); pPr.set("marL", "228600"); pPr.set("indent", "-228600")
        pPr.append(pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"}))
        pPr.append(pPr.makeelement(qn("a:buChar"), {"char": "•"}))
        r = p.add_run(); r.text = label + ": "; _run_font(r, size)
        r = p.add_run(); r.text = url; _run_font(r, size - 1, color=TEAL)
        r.hyperlink.address = url; r.font.underline = True
    return tb


def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


# ------------------------------------------------------------------ open sample, drop its slides
prs = Presentation(SRC)
BLANK = prs.slides[1].slide_layout
sld = prs.slides._sldIdLst
for s in list(sld):
    prs.part.drop_rel(s.get(qn("r:id")))
    sld.remove(s)
N = [0]


def _run_font(r, size, bold=False, color=INK, italic=False):
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    rPr = r._r.get_or_add_rPr()
    for tag in ("a:cs", "a:ea"):
        if rPr.find(qn(tag)) is None:
            e = rPr.makeelement(qn(tag), {"typeface": FONT}); rPr.append(e)


def write(tf, paras, size=16, color=INK, bullet=False, after=6, align=None):
    """paras: strings with **bold** spans. A paragraph starting with '- ' gets a bullet when bullet is True."""
    tf.word_wrap = True
    first = True
    for text in paras:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(after)
        if align is not None:
            p.alignment = align
        b = bullet and not text.startswith("##")
        text = text.lstrip("#")
        if b and text.startswith("- "):
            text = text[2:]
        if b:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", "285750"); pPr.set("indent", "-285750")
            bf = pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"}); pPr.append(bf)
            bc = pPr.makeelement(qn("a:buChar"), {"char": "•"}); pPr.append(bc)
        for i, part in enumerate(text.split("**")):
            if part:
                r = p.add_run(); r.text = part
                _run_font(r, size, i % 2 == 1, color)
        if b is False and bullet:
            pass
    return tf


def textbox(s, x, y, w, h, paras, size=16, color=INK, bullet=False, after=6, align=None, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    write(tf, paras, size, color, bullet, after, align)
    return tb


def slide(title):
    s = prs.slides.add_slide(BLANK)
    N[0] += 1
    textbox(s, 0.55, 0.28, 12.1, 0.55, [f"**{title}**"], 27, NAVY)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.58), Inches(0.96), Inches(1.05), Inches(0.06))
    bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background()
    textbox(s, 12.2, 7.08, 0.6, 0.3, [str(N[0])], 9, GREY, align=PP_ALIGN.RIGHT)
    return s


def box(s, x, y, w, h, fill=TINT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    b = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = fill
    if line:
        b.line.color.rgb = line; b.line.width = Pt(1)
    else:
        b.line.fill.background()
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        b.adjustments[0] = 0.08
    b.shadow.inherit = False
    return b


def card(s, x, y, w, h, head, body, size=14, fill=TINT, head_color=NAVY):
    box(s, x, y, w, h, fill)
    textbox(s, x + 0.15, y + 0.1, w - 0.3, 0.45, [f"**{head}**"], size + 2, head_color)
    textbox(s, x + 0.15, y + 0.55, w - 0.3, h - 0.65, body if isinstance(body, list) else [body], size)


def circle_num(s, x, y, n, d=0.5, fill=TEAL):
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid(); c.fill.fore_color.rgb = fill; c.line.fill.background(); c.shadow.inherit = False
    tf = c.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    write(tf, [f"**{n}**"], 16 if d >= 0.5 else 13, WHITE, align=PP_ALIGN.CENTER)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE


def image(s, path, x, y, w, h, caption=None, border=False):
    """Fit inside the box, centred."""
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    px, py = x + (w - pw) / 2, y + (h - ph) / 2
    pic = s.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(pw), Inches(ph))
    if border:
        pic.line.color.rgb = SOFT; pic.line.width = Pt(0.75)
    if caption:
        textbox(s, x, py + ph + 0.04, w, 0.32, [caption], 11, GREY, align=PP_ALIGN.CENTER)
    return pic


def table(s, rows, x, y, w, widths, size=13, row_h=0.36, bold_first_col=False):
    t = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows))).table
    tot = sum(widths)
    for j, wd in enumerate(widths):
        t.columns[j].width = Emu(int(Inches(w) * wd / tot))
    for i, r in enumerate(rows):
        t.rows[i].height = Inches(row_h)
        for j, v in enumerate(r):
            c = t.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.07)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (TINT if i % 2 == 0 else WHITE)
            tf = c.text_frame
            tf.paragraphs[0].text = ""
            bold = i == 0 or (bold_first_col and j == 0)
            write(tf, [f"**{v}**" if bold else str(v)], size, WHITE if i == 0 else INK, after=0)
    tblPr = t._tbl.tblPr
    tblPr.set("firstRow", "1"); tblPr.set("bandRow", "0")
    return t


def arrow(s, x1, y1, x2, y2):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = GREY; c.line.width = Pt(1.5)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}); ln.append(tail)
    return c


def chart_style(ch, size=12, legend=False, fmt=None, maxv=None, minv=None):
    ch.font.name = FONT; ch.font.size = Pt(size)
    ch.has_legend = legend
    if legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(size); ch.legend.font.name = FONT
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor(0xDD, 0xE3, 0xE8)
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(size - 1); va.tick_labels.font.color.rgb = GREY
    if fmt:
        va.tick_labels.number_format = fmt; va.tick_labels.number_format_is_linked = False
    if maxv is not None:
        va.maximum_scale = maxv
    if minv is not None:
        va.minimum_scale = minv
    ca = ch.category_axis
    ca.tick_labels.font.size = Pt(size - 1); ca.tick_labels.font.color.rgb = INK
    ca.format.line.color.rgb = SOFT


def bar_chart(s, x, y, w, h, cats, series, colors, title=None, fmt="0", label_fmt=None, horizontal=False,
              maxv=None, minv=None, size=12, point_colors=None, gap=60):
    cd = CategoryChartData(); cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    ch = s.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    chart_style(ch, size, legend=len(series) > 1, fmt=fmt, maxv=maxv, minv=minv)
    ch.plots[0].gap_width = gap
    for i, ser in enumerate(ch.series):
        ser.format.fill.solid(); ser.format.fill.fore_color.rgb = colors[i]
        ser.invert_if_negative = False
        dl = ser.data_labels
        dl.show_value = True; dl.number_format = label_fmt or fmt; dl.number_format_is_linked = False
        dl.font.size = Pt(size - 1); dl.font.name = FONT; dl.position = XL_LABEL_POSITION.OUTSIDE_END
        if point_colors and i == 0:
            for k, c in point_colors.items():
                pt = ser.points[k]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = c
    if title:
        ch.has_title = True
        ch.chart_title.text_frame.text = title
        r = ch.chart_title.text_frame.paragraphs[0].runs[0]
        r.font.size = Pt(size + 1); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = NAVY
    else:
        ch.has_title = False
    return ch


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


cr, fe, yi, lf = F["crop"], F["fert"], F["yield"], F["leaf"]

# ================================================================== 1 title (sample's layout, filled)
s = prs.slides.add_slide(BLANK); N[0] += 1
textbox(s, 1.27, 0.56, 7.45, 0.57, ["**FINAL PROJECT EVALUATION**"], 28)
textbox(s, 1.27, 1.44, 7.6, 1.2, ["**AgriSense AI: A Smart Farming Assistant**",
                                  "Crop, yield, fertiliser and leaf-disease decisions with machine learning"], 24, NAVY, after=4)
s.shapes[-1].text_frame.paragraphs[1].runs[0].font.size = Pt(18)
s.shapes[-1].text_frame.paragraphs[1].runs[0].font.color.rgb = GREY
textbox(s, 1.52, 3.3, 7.3, 1.3, ["**Presented By**"] + [f"{n}  |  {e}" for n, e in C.TEAM], 16, after=3)
textbox(s, 1.52, 4.85, 7.3, 0.45, [f"**Programme:** B.Tech CSE, Semester V, Section {C.SECTION}"], 16)
textbox(s, 1.52, 5.35, 7.3, 0.45, [f"**Course:** {COURSE}, Session {C.YEAR}"], 16)
textbox(s, 1.52, 5.85, 7.3, 0.45, [f"**Faculty:** {FACULTY}"], 16)
image(s, HERE / "niit_logo.png", 8.9, 0.5, 3.9, 1.3)
image(s, AND / "welcome.png", 9.75, 2.1, 2.3, 4.9, border=True)
notes(s, "Introduce the team and the project: an AI system that helps a farmer choose a crop and a fertiliser, "
         "estimate yield and recognise leaf disease.")

# ================================================================== 2 problem statement
s = slide("1. Problem Statement")
textbox(s, 0.75, 1.35, 6.6, 4.6, [
    "- A Soil Health Card gives N, P and K values, but it does not say **which crop suits the field** or **which "
    "fertiliser grade** to buy.",
    "- Leaf diseases are usually noticed **after they have spread**.",
    "- Yield, weather and soil records sit on separate government and research websites, mostly in English.",
    "- Wrong choices cost money: lost yield, and fertiliser the soil did not need.",
], 18, bullet=True, after=12)
card(s, 0.75, 5.35, 6.6, 1.45, "AI question",
     "Given soil, climate, location and a leaf photo, what should the farmer grow, how much will it yield, "
     "which fertiliser does the soil need, and is the leaf diseased?", 14)
image(s, FIGS / "shot_02_overview.png", 7.75, 1.4, 5.1, 4.6, "AgriSense AI web dashboard (overview page)", border=True)

# ================================================================== 3 objectives
s = slide("2. Project Objectives")
objs = [
    ("Problem as AI tasks", "Crop and fertiliser choice as classification, yield as regression, leaf diagnosis as image classification, joined in one decision chain."),
    ("Data and features", f"Four public datasets: soil and climate (N, P, K, temperature, humidity, pH, rainfall), {yi['clean_rows']:,} district yield records, fertiliser records and {lf['images']:,} leaf images."),
    ("Algorithms", "Random Forest, LightGBM, Logistic Regression and EfficientNet-B0, each chosen by comparing several candidates with cross-validation."),
    ("Evaluation and comparison", "Every model tested on unseen data against a simple baseline, with accuracy, F1, MAE, R² and calibration error."),
    ("Usable system", "Serve all models through one API to a web dashboard and an Android app, with an AI assistant that explains results in 15 languages."),
]
for i, (h, t) in enumerate(objs):
    y = 1.35 + i * 1.12
    circle_num(s, 0.8, y + 0.1, i + 1, 0.55)
    textbox(s, 1.55, y, 11.2, 1.05, [f"**{h}**", t], 16, after=2)

# ================================================================== 4 workflow (native diagram)
s = slide("3. Workflow Diagram")
steps = [("Problem definition", "4 farmer questions as AI tasks"),
         ("Data collection", "Kaggle, data.gov.in, Mendeley"),
         ("Preprocessing", "units, outliers, duplicates, image copies"),
         ("EDA", "class balance, yield spread, ranges"),
         ("Feature selection", "permutation and gain importance"),
         ("Train-test split", "stratified, temporal, leak guard"),
         ("Model training", "compare candidates with CV"),
         ("Model evaluation", "held-out test vs baselines"),
         ("Deployment", "FastAPI, ONNX, Docker, Android"),
         ("Prediction", "result + AI assistant explanation")]
bw, bh, gx = 2.2, 1.25, 0.32
for i, (h, t) in enumerate(steps):
    row, col = divmod(i, 5)
    if row == 1:
        col = 4 - col  # snake: second row runs right to left
    x = 0.75 + col * (bw + gx)
    y = 1.55 + row * 2.35
    b = box(s, x, y, bw, bh, NAVY if i in (6, 7) else TINT)
    textbox(s, x + 0.08, y + 0.1, bw - 0.16, 0.4, [f"**{i + 1}. {h}**"], 14, WHITE if i in (6, 7) else NAVY, align=PP_ALIGN.CENTER)
    textbox(s, x + 0.08, y + 0.52, bw - 0.16, 0.7, [t], 12, WHITE if i in (6, 7) else INK, align=PP_ALIGN.CENTER)
for i in range(4):
    x = 0.75 + i * (bw + gx) + bw
    arrow(s, x + 0.03, 1.55 + bh / 2, x + gx - 0.03, 1.55 + bh / 2)
    x2 = 0.75 + (4 - i) * (bw + gx)
    arrow(s, x2 - 0.03, 3.9 + bh / 2, x2 - gx + 0.03, 3.9 + bh / 2)
xr = 0.75 + 4 * (bw + gx) + bw / 2
arrow(s, xr, 1.55 + bh + 0.03, xr, 3.9 - 0.03)
textbox(s, 0.75, 5.75, 11.9, 1.0, [
    "Steps 6 to 8 run once per model: 5 classifiers for crops, LightGBM against 3 baselines for yield, 8 candidates "
    "for fertiliser, and a pretrained CNN for leaves. Every metric is saved to a JSON model card that the app and "
    "the report read."], 14, GREY)

# ================================================================== 5 AI decision chain
s = slide("3. Workflow: AI Decision Chain")
image(s, MY / "ai_chain.png", 0.7, 1.3, 11.9, 4.1)
card(s, 0.75, 5.55, 5.8, 1.35, "Learned", "Crop model and fertiliser model learn from labelled records; the leaf CNN learns from images.", 14)
card(s, 6.85, 5.55, 5.8, 1.35, "Reasoned", "A rule step turns a soil reading into a nutrient need and rejects any fertiliser that does not supply what is short.", 14)

# ================================================================== 6 methodology: datasets
s = slide("4. Methodology: Datasets")
table(s, [
    ["Model", "Dataset and source", "Samples", "Features", "Target", "Split"],
    ["Crop", "Crop_recommendation.csv, Kaggle", f"{cr['rows']:,}", "7", f"label ({cr['classes']} crops, 100 each)", "80/20 stratified"],
    ["Yield", "Crop Production, Kaggle (data.gov.in)", f"{yi['clean_rows']:,}", str(len(YLD["features"])), "Yield, t/ha", "Train < 2017-18, test after"],
    ["Fertiliser", "Fertilizer Prediction.csv, Kaggle", str(fe["rows"]), "8 (3 used)", "Fertilizer Name (7)", "5x5 repeated CV"],
    ["Leaf", "PlantVillage-derived, Mendeley (CC BY 4.0)", f"{lf['images']:,}", "224x224 RGB", f"{lf['classes']} classes", "70/15/15 stratified"],
], 0.6, 1.35, 12.1, [1.1, 3.2, 1.1, 1.3, 2.3, 2.1], 14, 0.5, bold_first_col=True)
for i, key in enumerate(("Crop", "Yield", "Fertiliser", "Leaf"), start=1):
    for r in s.shapes[-1].table.cell(i, 1).text_frame.paragraphs[0].runs:
        r.hyperlink.address = DATA_LINKS[key][1]; r.font.color.rgb = TEAL; r.font.underline = True
textbox(s, 0.6, 3.82, 12.1, 0.3, ["Click a dataset name to open its source page; all links are on the References slide."], 11, GREY)
textbox(s, 0.6, 4.15, 6.0, 0.4, ["**Preprocessing**"], 18, NAVY)
textbox(s, 0.6, 4.55, 6.0, 2.4, [
    "- Yield: kept tonnes only, removed per-crop yields above the 99.5th percentile, summed duplicate district rows "
    f"({yi['raw_rows']:,} to {yi['clean_rows']:,} rows).",
    "- Leaf: resize to 224x224, ImageNet normalisation; 1,811 synthetic images dropped because they copied test or validation images.",
    "- All inputs checked against allowed ranges before prediction.",
], 14, bullet=True, after=6)
image(s, FIGS / "leaf_samples.png", 7.0, 4.1, 5.8, 2.85, "Sample leaf images from the dataset")

# ================================================================== 7 methodology: algorithms
s = slide("4. Methodology: Algorithms and Why")
algs = [
    ("Crop: Random Forest", ["Compared: LogReg, KNN, SVM, RF, LightGBM", "Best 5-fold CV accuracy (99.38%)", "400 trees, gives class probabilities"]),
    ("Yield: LightGBM", ["Handles 700+ districts as categories", "Trains on 3 lakh rows in minutes", "L1 loss, 127 leaves, early stopping"]),
    ("Fertiliser: Logistic Regression", ["8 candidates (4 algorithms x 2 feature sets)", "Simplest model with 100% CV", "Uses N, P, K only (others add nothing)"]),
    ("Leaf: EfficientNet-B0", ["Transfer learning from ImageNet", "5.3 M parameters, runs on CPU via ONNX", "Calibrated: refuses below 0.95"]),
]
for i, (h, pts) in enumerate(algs):
    x = 0.6 + i * 3.1
    box(s, x, 1.4, 2.9, 3.55)
    circle_num(s, x + 0.15, 1.55, i + 1, 0.5)
    textbox(s, x + 0.75, 1.5, 2.1, 0.75, [f"**{h}**"], 15, NAVY)
    textbox(s, x + 0.15, 2.4, 2.65, 2.5, ["- " + p for p in pts], 14, bullet=True, after=8)
textbox(s, 0.6, 5.2, 12.1, 0.4, ["**Training and testing strategy**"], 18, NAVY)
textbox(s, 0.6, 5.6, 12.1, 1.4, [
    "- Model chosen on cross-validation of the training part only; the test part stays unseen until the end.",
    "- Yield uses a **temporal** split (later years as test), because a random split would let the model see a district's future.",
    "- After testing, each model is refit on all data for deployment; reported figures are from the test run.",
], 14, bullet=True, after=4)

# ================================================================== 8 methodology: reasoning step
s = slide("4. Methodology: From Soil Reading to Fertiliser")
st = ["Take the crop's typical N, P, K (crop median, or Soil Health Card mid-band for a lab test)",
      "Shortfall of each nutrient as a fraction of typical; under 5% counts as zero",
      "Nothing short: answer 'no fertiliser needed' and stop",
      "Scale the shortfall so the largest sits at the top of the fertiliser data's range",
      "Required = every nutrient with at least 1/4 of the largest shortfall",
      "Fertiliser model ranks the grades; take the best one that supplies all required nutrients"]
for i, t in enumerate(st):
    y = 1.4 + i * 0.88
    circle_num(s, 0.75, y + 0.05, i + 1, 0.45)
    textbox(s, 1.35, y, 6.0, 0.85, [t], 15)
ch = F["chain"]
box(s, 7.75, 1.4, 5.0, 5.3)
textbox(s, 7.95, 1.5, 4.6, 0.45, ["**Worked example: maize**"], 18, NAVY)
table(s, [["", "N", "P", "K"],
          ["Soil", f"{ch['input']['N']:.0f}", str(ch["input"]["P"]), str(ch["input"]["K"])],
          ["Maize typical", str(ch["typical"]["N"]), str(ch["typical"]["P"]), str(ch["typical"]["K"])],
          ["Shortfall", f"{ch['shortfall']['N'] * 100:.1f}%", "0%", f"{ch['shortfall']['K'] * 100:.0f}%"],
          ["Status", "short", "adequate", "short"]], 7.95, 2.05, 4.6, [1.6, 1, 1, 1], 14, 0.4, bold_first_col=True)
textbox(s, 7.95, 4.25, 4.6, 2.4, [
    "Both N and K pass the 1/4 rule, so the answer must supply both.",
    f"Result: **{ch['fert']}** (balanced NPK).",
    "Urea is rejected: it has no potassium."], 15, after=8)

# ================================================================== 9 architecture + tech stack
s = slide("System Architecture and Tech Stack")
image(s, FIGS / "architecture.png", 0.55, 1.3, 7.0, 3.6)
textbox(s, 0.6, 5.05, 6.9, 1.9, [
    "- The web dashboard and Android app call **one FastAPI server**.",
    "- Models load once per worker; the leaf CNN runs through **ONNX Runtime** on CPU.",
    "- Weather (Open-Meteo, NASA POWER) and soil maps (SoilGrids) are fetched live; results are stored per user.",
], 14, bullet=True, after=5)
stack = [("Machine learning", "scikit-learn, LightGBM"), ("Deep learning", "PyTorch, torchvision, ONNX Runtime"),
         ("Data", "pandas, NumPy, Matplotlib"), ("Backend", "Python 3.12, FastAPI, SQLite"),
         ("LLM assistant", "Mistral API, 15 languages"), ("Web client", "HTML, CSS, JavaScript"),
         ("Mobile", "Kotlin, Jetpack Compose"), ("Deployment", "Docker, Traefik, Linux VPS")]
for i, (h, t) in enumerate(stack):
    r, c = divmod(i, 2)
    x, y = 7.85 + c * 2.5, 1.3 + r * 1.42
    box(s, x, y, 2.35, 1.27)
    textbox(s, x + 0.1, y + 0.08, 2.15, 0.4, [f"**{h}**"], 14, TEAL)
    textbox(s, x + 0.1, y + 0.5, 2.15, 0.75, [t], 13)

# ================================================================== 10 experimental setup
s = slide("5. Experimental Setup")
host = LOAD["host"]["cpu"].split(" Processor")[0]
table(s, [
    ["Item", "Configuration"],
    ["Hardware", "Training: Windows 11 PC with NVIDIA RTX 5070 Ti (CUDA 12.8). Serving: VPS with 2 vCPU (" + host + "), 8 GB RAM"],
    ["Software", "Windows 11, VS Code, Python virtual environment; Docker on Linux for deployment"],
    ["Language", "Python 3.12 (models, API); Kotlin (Android); JavaScript (web)"],
    ["Libraries", "NumPy, pandas, Matplotlib, scikit-learn, LightGBM, PyTorch, torchvision, ONNX Runtime, FastAPI"],
    ["Dataset configuration", f"Crop {cr['rows']:,} x 7, 80/20. Yield {yi['clean_rows']:,} x {len(YLD['features'])}, temporal. Fertiliser {fe['rows']} x 3, 5x5 CV. Leaf {lf['images']:,} images, 70/15/15"],
    ["Algorithm configuration", "RF 400 trees; LightGBM lr 0.05, 127 leaves, L1 loss; LogReg multinomial, scaled; EfficientNet-B0, AdamW lr 0.001, batch 96, 8 epochs, label smoothing 0.05, seed 42"],
    ["Evaluation metrics", "Accuracy, macro F1, precision, recall (classification); MAE, R², median % error (yield); calibration error (leaf); latency and throughput (server)"],
], 0.6, 1.35, 12.1, [2.4, 9.7], 14, 0.62, bold_first_col=True)

# ================================================================== 11 results summary
s = slide("6. Results & Discussions")
table(s, [
    ["Model", "Primary metric", "Baseline", "Result"],
    ["Crop", "Accuracy", f"{pct(cr['majority_share'])} (majority)", pct(CROP["test_accuracy"])],
    ["Yield", "MAE (t/ha)", f"{YR[LASTYR]['mae_t_ha']} (last year)", f"{YR['LightGBM (this model)']['mae_t_ha']}"],
    ["Fertiliser", "CV accuracy", f"{pct(fe['majority_share'], 1)} (majority)", pct(FC["cv_accuracy_mean"], 1)],
    ["Leaf disease", "Accuracy", f"{pct(lf['majority_share'])} (majority)", pct(LT["accuracy"])],
], 0.6, 1.4, 6.3, [1.6, 1.6, 2.0, 1.1], 15, 0.55, bold_first_col=True)
textbox(s, 0.6, 4.4, 6.3, 2.5, [
    "- All three classifiers are far above their majority baselines.",
    f"- Yield beats last year's yield on MAE and on R² ({YR['LightGBM (this model)']['r2']} vs {YR[LASTYR]['r2']}).",
    f"- The leaf model answers {pct(LT['answered_fraction'], 1)} of photos and is right on {pct(LT['accuracy_when_answered'])} of those.",
], 15, bullet=True, after=8)
bar_chart(s, 7.2, 1.3, 5.6, 5.5, ["Crop", "Fertiliser", "Leaf"],
          [("Majority baseline", [cr["majority_share"] * 100, fe["majority_share"] * 100, lf["majority_share"] * 100]),
           ("Our model", [CROP["test_accuracy"] * 100, FC["cv_accuracy_mean"] * 100, LT["accuracy"] * 100])],
          [SOFT, TEAL], "Accuracy vs baseline (%)", fmt="0", label_fmt="0.0", maxv=110, minv=0)

# ================================================================== 12 crop results
s = slide("6. Results: Crop Recommendation")
comp = sorted(CROP["comparison"], key=lambda c: -c["cv_accuracy_mean"])
bar_chart(s, 0.55, 1.3, 6.7, 3.6, [c["model"].replace("K-Nearest Neighbours", "KNN") for c in comp],
          [("CV accuracy", [c["cv_accuracy_mean"] * 100 for c in comp]), ("Test accuracy", [c["test_accuracy"] * 100 for c in comp])],
          [SOFT, TEAL], "Five classifiers compared (%)", fmt="0", label_fmt="0.0", minv=90, maxv=101)
textbox(s, 0.6, 5.05, 6.6, 1.9, [
    f"- Random Forest: best CV accuracy, **{pct(CROP['test_accuracy'])}** test accuracy, macro F1 {CROP['test_macro_f1']}.",
    "- Only 2 of 440 test samples wrong (blackgram as maize, rice as jute): crops needing similar soil and rain.",
    "- The dataset is clean and balanced, so real soil tests will score lower.",
], 14, bullet=True, after=6)
image(s, FIGS / "crop_confusion.png", 7.5, 1.25, 5.3, 5.6, "Confusion matrix, 20% test split")

# ================================================================== 13 yield results
s = slide("6. Results: Yield Prediction")
meth = ["LightGBM (this model)", MEAN3, LASTYR, "Baseline: national crop mean"]
lab = ["LightGBM", "3-year mean", "Last year", "National mean"]
bar_chart(s, 0.55, 1.3, 6.2, 3.3, lab, [("MAE", [YR[m]["mae_t_ha"] for m in meth])], [SOFT],
          "MAE on test years, t/ha (lower is better)", fmt="0.0", label_fmt="0.000", point_colors={0: TEAL})
bar_chart(s, 6.85, 1.3, 6.0, 3.3, lab, [("R²", [YR[m]["r2"] for m in meth])], [SOFT],
          "R² on test years (higher is better)", fmt="0.0", label_fmt="0.000", point_colors={0: TEAL}, minv=0, maxv=1.05)
pc = YLD["per_crop_test"][:5]
table(s, [["Crop", "Test rows", "R²", "MAE"]] + [[p["crop"], f"{p['rows']:,}", f"{p['r2']:.2f}", f"{p['mae_t_ha']:.2f}"] for p in pc],
      0.6, 4.8, 5.6, [2.2, 1.2, 1, 1], 12, 0.34)
textbox(s, 6.5, 4.8, 6.3, 2.1, [
    f"- Test: {YLD['rows_test']:,} rows from 2017-18 onwards, never seen in training.",
    "- Last year's yield is a strong baseline; the model gains most on large swings.",
    "- No rainfall or soil input in the data, so a drought year cannot be foreseen.",
], 14, bullet=True, after=6)

# ================================================================== 14 fertiliser results
s = slide("6. Results: Fertiliser Recommendation")
fc = sorted(FERT["comparison"], key=lambda c: -c["cv_accuracy_mean"])
labels = [f"{c['model'].replace('K-Nearest Neighbours', 'KNN').replace('Logistic Regression', 'LogReg')} ({'NPK' if c['features'] == 'N, P, K' else 'all'})" for c in fc]
bar_chart(s, 0.55, 1.25, 7.3, 5.7, labels, [("CV accuracy", [c["cv_accuracy_mean"] * 100 for c in fc])], [SOFT],
          "5x5 repeated CV accuracy (%)", fmt="0", label_fmt="0.0", horizontal=True, minv=0, maxv=110,
          point_colors={i: TEAL for i, c in enumerate(fc) if c["features"] == "N, P, K"}, gap=40)
card(s, 8.15, 1.35, 4.65, 1.65, "Chosen: Logistic Regression", f"{pct(FC['cv_accuracy_mean'], 1)} in 25 folds, 100% on the 20-row hold-out, on N, P, K only.", 14)
textbox(s, 8.15, 3.2, 4.65, 3.7, [
    "- Every algorithm does better on N, P, K alone (teal) than on all 8 features.",
    "- KNN falls to 23% with all features: soil, crop and weather add noise to the distance.",
    f"- Only {fe['rows']} rows, so 100% means the grades separate cleanly here, not that the model is perfect.",
], 14, bullet=True, after=8)

# ================================================================== 15 leaf results
s = slide("6. Results: Leaf-Disease Detection")
stats = [(pct(LT["accuracy"]), "test accuracy"), (pct(LT["macro_recall"]), "macro recall"),
         (f"{LT['ece_before_T']} → {LT['ece_after_T']}", "calibration error"), (pct(LT["accuracy_when_answered"]), "accuracy when it answers")]
for i, (v, l) in enumerate(stats):
    x = 0.6 + i * 3.1
    box(s, x, 1.35, 2.9, 1.35)
    textbox(s, x + 0.1, 1.42, 2.7, 0.7, [f"**{v}**"], 26, TEAL, align=PP_ALIGN.CENTER)
    textbox(s, x + 0.1, 2.1, 2.7, 0.45, [l], 14, GREY, align=PP_ALIGN.CENTER)
image(s, FIGS / "leaf_history.png", 0.55, 2.95, 6.4, 2.7, "Validation accuracy and training loss, 8 epochs on RTX 5070 Ti")
table(s, [["Hardest classes", "Recall"]] + [[k.replace("___", " / ").replace("_", " ").replace(" Gray leaf spot", ""), f"{v:.3f}"] for k, v in lf["lowest_recall"][:4]],
      7.3, 3.0, 5.5, [4.2, 1.3], 13, 0.36)
textbox(s, 7.3, 4.95, 5.5, 2.0, [
    "- Look-alike diseases are the main confusion (corn leaf spot vs northern leaf blight).",
    f"- Temperature scaling ({LEAF['temperature']}) makes confidence honest; below 0.95 the photo goes for review.",
    "- Tested on lab photos only; field photos will score lower.",
], 13, bullet=True, after=5)

# ================================================================== 16 sample outputs
s = slide("6. Results: Sample Outputs")
rows = [["Model", "Input", "Actual / reference", "System output"]]
for smp in F["samples"]:
    if smp["model"] == "Crop" and rows[-1][0] == "Crop":
        continue
    if smp["model"] == "Leaf disease" and sum(r[0] == "Leaf disease" for r in rows) >= 2:
        continue
    if smp["model"] == "Fertiliser" and sum(r[0] == "Fertiliser" for r in rows) >= 2:
        continue
    rows.append([smp["model"], smp["input"].replace("___", " / "), smp["truth"].replace("___", " / "), smp["output"].replace("___", " / ").replace(", diseased", "")])
table(s, rows, 0.6, 1.35, 12.1, [1.4, 5.3, 2.4, 3.0], 13, 0.52, bold_first_col=True)
textbox(s, 0.6, 1.5 + 0.52 * len(rows), 12.1, 1.2, [
    "Outputs from the deployed models. Yield rows predict 2021-22, one year past the data, so the district average is shown "
    "for reference. Crop, fertiliser and leaf rows come from the datasets and show the pipeline working."], 13, GREY)

# ================================================================== 17 load test
s = slide("6. Results: Load and Capacity Test")
step = LOAD["step"]
cd = CategoryChartData(); cd.categories = [str(x["users"]) for x in step]
cd.add_series("95th percentile (ms)", [x["p95_ms"] for x in step]); cd.add_series("Median (ms)", [x["p50_ms"] for x in step])
chl = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.55), Inches(1.3), Inches(6.3), Inches(4.2), cd).chart
chart_style(chl, 12, legend=True, fmt="#,##0")
for ser, col in zip(chl.series, (TEAL, NAVY)):
    ser.format.line.color.rgb = col; ser.format.line.width = Pt(2.25); ser.smooth = False
    ser.marker.format.fill.solid(); ser.marker.format.fill.fore_color.rgb = col
chl.has_title = True; chl.chart_title.text_frame.text = "Response time vs users at once"
r = chl.chart_title.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(13); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = NAVY
bar_chart(s, 6.95, 1.3, 5.9, 4.2, [str(x["users"]) for x in step], [("Requests/s", [x["rps"] for x in step])], [SOFT],
          "Throughput, requests per second", fmt="0", label_fmt="0", point_colors={3: TEAL})
for i, (v, l) in enumerate([(str(LOAD["capacity_users_p95_under_2s"]), "users with 95% under 2 s"),
                            (f"{LOAD['capacity_rps_at_that_point']:.0f}", "requests per second"),
                            ("0", "errors in 32,061 requests"),
                            (f"{LOAD['bench']['leaf_disease']['mean_ms']:.0f} ms", "leaf prediction on 1 core")]):
    x = 0.6 + i * 3.1
    box(s, x, 5.7, 2.9, 1.2)
    textbox(s, x + 0.1, 5.75, 2.7, 0.6, [f"**{v}**"], 24, TEAL, align=PP_ALIGN.CENTER)
    textbox(s, x + 0.1, 6.35, 2.7, 0.45, [l], 13, GREY, align=PP_ALIGN.CENTER)

# ================================================================== 18 discussion (sample's "contd" slide)
s = slide("Result & Discussions Contd’")
disc = [("Result interpretation",
         ["Crop and leaf accuracies are near 100% because both datasets are clean lab-style data.",
          "Yield error of 0.87 t/ha is small for rice and wheat but large for low-yield pulses."]),
        ("Model comparison",
         ["Tree ensembles win on tabular data (RF for crops, LightGBM for yield).",
          "A simple linear model is enough for fertiliser once only N, P, K are used.",
          "The pretrained CNN beats training from scratch on 55k images."]),
        ("Discussion of findings",
         ["Features with no signal hurt distance-based models most (KNN 99% to 23%).",
          "District identity and past yields explain most of the yield.",
          "Calibration matters more than raw accuracy for a farmer-facing tool."])]
for i, (h, pts) in enumerate(disc):
    x = 0.6 + i * 4.1
    box(s, x, 1.4, 3.9, 3.75)
    circle_num(s, x + 0.2, 1.6, i + 4, 0.55)
    textbox(s, x + 0.9, 1.62, 2.9, 0.6, [f"**{h}**"], 17, NAVY)
    textbox(s, x + 0.2, 2.45, 3.5, 2.6, ["- " + p for p in pts], 15, bullet=True, after=10)
textbox(s, 0.6, 5.35, 12.1, 0.4, ["**Best-performing model per task**"], 17, NAVY)
for i, (task, m) in enumerate([("Crop", "Random Forest"), ("Yield", "LightGBM"), ("Fertiliser", "Logistic Regression"), ("Leaf disease", "EfficientNet-B0")]):
    x = 0.6 + i * 3.1
    box(s, x, 5.85, 2.9, 1.0, NAVY)
    textbox(s, x + 0.1, 5.9, 2.7, 0.4, [task], 13, SOFT, align=PP_ALIGN.CENTER)
    textbox(s, x + 0.1, 6.27, 2.7, 0.5, [f"**{m}**"], 16, WHITE, align=PP_ALIGN.CENTER)

# ================================================================== 19 web screenshots
for part, shots in ((1, [("shot_03_crop.png", "Crop recommendation with top alternatives"), ("shot_05_fertiliser.png", "Fertiliser suggested after the full chain")]),
                    (2, [("shot_04_yield.png", "Yield prediction with feature contributions"), ("shot_07_weather.png", "Live weather and history for the farm")])):
    s = slide(f"Application: Web Dashboard ({part}/2)")
    for k, (f, c) in enumerate(shots):
        image(s, FIGS / f, 0.6 + k * 6.15, 1.3, 5.95, 5.3, c, border=True)

# ================================================================== 20 android screenshots
s = slide("Application: Android App")
phones = [("home.png", "Home"), ("chain.png", "Full auto analysis"), ("fertiliser.png", "Fertiliser result"),
          ("scan.png", "Leaf scan"), ("assistant.png", "AI assistant")]
for i, (f, c) in enumerate(phones):
    image(s, AND / f, 0.6 + i * 2.48, 1.3, 2.25, 5.25, c, border=True)

# ================================================================== 21 conclusion
s = slide("7. Conclusion")
cl = [(pct(CROP["test_accuracy"]), "crop accuracy", f"baseline {pct(cr['majority_share'])}"),
      (f"{YR['LightGBM (this model)']['r2']}", "yield R² on unseen years", f"last year {YR[LASTYR]['r2']}"),
      (pct(FC["cv_accuracy_mean"], 0), "fertiliser CV accuracy", f"baseline {pct(fe['majority_share'], 1)}"),
      (pct(LT["accuracy"]), "leaf accuracy", f"ECE {LT['ece_after_T']}")]
for i, (v, l, b) in enumerate(cl):
    x = 0.6 + i * 3.1
    box(s, x, 1.4, 2.9, 1.75)
    textbox(s, x + 0.1, 1.48, 2.7, 0.7, [f"**{v}**"], 28, TEAL, align=PP_ALIGN.CENTER)
    textbox(s, x + 0.1, 2.2, 2.7, 0.85, [l, b], 13, GREY, align=PP_ALIGN.CENTER, after=0)
textbox(s, 0.6, 3.5, 12.1, 3.4, [
    "- We framed four farm decisions as AI tasks and joined the crop and fertiliser models with a reasoning step that turns a soil reading into a nutrient need.",
    "- Each algorithm was chosen by cross-validation and beat a simple baseline on data it had not seen.",
    "- The system is live on the web and Android, explains results through an AI assistant, and serves about 100 users at once on a 2-core server.",
    "- Main limits: clean lab-style datasets, no weather input for yield, only 99 fertiliser rows, leaf model untested on field photos.",
], 16, bullet=True, after=10)

# ================================================================== 22 future scope
s = slide("8. Future Scope")
for i, t in enumerate(C.FUTURE):
    y = 1.4 + i * 1.08
    circle_num(s, 0.8, y + 0.08, i + 1, 0.55)
    box(s, 1.55, y, 11.2, 0.82)
    textbox(s, 1.7, y + 0.1, 10.9, 0.65, [t], 17, anchor=MSO_ANCHOR.MIDDLE)

# ================================================================== references with links
s = slide("References and Dataset Links")
textbox(s, 0.6, 1.25, 12.1, 0.4, ["**Datasets**"], 18, NAVY)
link_list(s, 0.6, 1.65, 12.1, 2.0, list(DATA_LINKS.values()), 13)
textbox(s, 0.6, 3.1, 12.1, 0.4, ["**Research papers**"], 18, NAVY)
link_list(s, 0.6, 3.5, 12.1, 3.0, PAPER_LINKS, 13)

# ================================================================== thank you
s = prs.slides.add_slide(BLANK); N[0] += 1
textbox(s, 0.6, 2.2, 12.1, 1.1, ["**THANK YOU**"], 54, NAVY, align=PP_ALIGN.CENTER)
tb = textbox(s, 0.6, 3.45, 12.1, 0.5, ["Live system: "], 18, INK, align=PP_ALIGN.CENTER)
r = tb.text_frame.paragraphs[0].add_run(); r.text = "https://ai.software.microeagle.online"
_run_font(r, 18, color=TEAL); r.hyperlink.address = "https://ai.software.microeagle.online"; r.font.underline = True
textbox(s, 0.6, 4.3, 12.1, 0.5, ["   |   ".join(n for n, _ in C.TEAM)], 16, GREY, align=PP_ALIGN.CENTER)
textbox(s, 0.6, 4.75, 12.1, 0.5, [f"{COURSE}  |  {FACULTY}"], 16, GREY, align=PP_ALIGN.CENTER)
textbox(s, 12.2, 7.08, 0.6, 0.3, [str(N[0])], 9, GREY, align=PP_ALIGN.RIGHT)

prs.core_properties.title = "AgriSense AI - AI and ML Final Evaluation"
prs.core_properties.author = ", ".join(n for n, _ in C.TEAM)
OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
# hyperlinks take the theme's hlink colour; make it the deck's teal (theme XML lives only inside the zip)
import re, shutil, tempfile, zipfile
_fd, _tp = tempfile.mkstemp(suffix=".pptx"); import os; os.close(_fd); tmp = Path(_tp)
with zipfile.ZipFile(OUT) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename.startswith("ppt/theme/theme"):
            t = data.decode("utf-8")
            for tag in ("hlink", "folHlink"):
                t = re.sub(rf"<a:{tag}>.*?</a:{tag}>", f'<a:{tag}><a:srgbClr val="009196"/></a:{tag}>', t, flags=re.S)
            data = t.encode("utf-8")
        zout.writestr(item, data)
shutil.move(str(tmp), OUT)
print("wrote", OUT, N[0], "slides")
