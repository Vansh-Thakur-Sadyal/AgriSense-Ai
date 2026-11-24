"""AI and ML project report (Artificial Intelligence, CS 322), built on the department's template.

The template's own styles, headings and tables are kept: its six tables are copied and filled, extra
tables copy the template's table look, and the NIIT cover goes first. Numbers come from the model cards,
the load-test summary and out/aiml_facts.json (written by aiml_facts.py)."""
import copy
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import content as C  # noqa: E402

TEMPLATE = Path(sys.argv[1])
OUTFILE = Path(sys.argv[2])
FIGS = ROOT / "docs" / "figs"
MYFIGS = HERE / "out" / "figs"
F = json.loads((HERE / "out" / "aiml_facts.json").read_text(encoding="utf-8"))
M = ROOT / "app" / "models"
CROP = json.loads((M / "crop_model.json").read_text())
YLD = json.loads((M / "yield_model.json").read_text())
FERT = json.loads((M / "fertiliser_model.json").read_text())
LEAF = json.loads((M / "leaf_disease.json").read_text())
LOAD = json.loads((ROOT / "tests" / "load" / "results" / "summary.json").read_text())

COURSE, CODE, FACULTY = "ARTIFICIAL INTELLIGENCE", "CS 322", "Dr. Shweta R Malwe"
URL = "https://ai.software.microeagle.online"
FONT = "Times New Roman"
FULL_W = 10080  # template table width in dxa (7 in)
YR = YLD["results"]


def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


# ------------------------------------------------------------------ open template, keep its tables, clear body
doc = Document(TEMPLATE)
body = doc.element.body
TPL = [copy.deepcopy(t._tbl) for t in doc.tables]
TITLE_P = copy.deepcopy(doc.paragraphs[0]._p)
for el in list(body):
    if el.tag != qn("w:sectPr"):
        body.remove(el)
HAS_H2 = "Heading 2" in [s.name for s in doc.styles]
FIG = [0]
TAB = [0]


def _font(run, size=10.5, bold=False, italic=False, color=None):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color


def runs(p, text, size=10.5, bold=False, italic=False):
    """**bold** spans inside text."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if part:
            _font(p.add_run(part), size, bold or i % 2 == 1, italic)
    return p


def para(text="", size=10.5, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=6, style=None):
    p = doc.add_paragraph(style=style)
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    if text:
        runs(p, text, size, bold, italic)
    return p


def h1(text):
    p = doc.add_paragraph(style="Heading 1")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.keep_with_next = True
    _font(p.add_run(text), 16)
    return p


def h2(text):
    p = doc.add_paragraph(style="Heading 2" if HAS_H2 else None)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    _font(p.add_run(text), 12.5, bold=True)
    return p


def bullets(items, style="List Bullet"):
    for t in items:
        p = para(style=style, after=2)
        runs(p, t)


def numbered(items):
    """Each call starts a new list at 1 (a new w:num on the style's abstract list)."""
    numbering = doc.part.numbering_part.element
    style_num = doc.styles["List Number"].element.pPr.find(qn("w:numPr")).find(qn("w:numId")).get(qn("w:val"))
    abs_id = next(n.find(qn("w:abstractNumId")).get(qn("w:val")) for n in numbering.findall(qn("w:num"))
                  if n.get(qn("w:numId")) == style_num)
    new_id = str(max(int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))) + 1)
    num = OxmlElement("w:num"); num.set(qn("w:numId"), new_id)
    a = OxmlElement("w:abstractNumId"); a.set(qn("w:val"), abs_id); num.append(a)
    o = OxmlElement("w:lvlOverride"); o.set(qn("w:ilvl"), "0")
    so = OxmlElement("w:startOverride"); so.set(qn("w:val"), "1"); o.append(so); num.append(o)
    numbering.append(num)
    for t in items:
        p = para(style="List Number", after=2)
        pr = p._p.get_or_add_pPr()
        numPr = OxmlElement("w:numPr")
        il = OxmlElement("w:ilvl"); il.set(qn("w:val"), "0"); numPr.append(il)
        ni = OxmlElement("w:numId"); ni.set(qn("w:val"), new_id); numPr.append(ni)
        pr.insert(1, numPr)
        runs(p, t)


def _cell_text(cell, text, size=10, bold=False, shade=None, align=None):
    lines = text.split("\n") if isinstance(text, str) else text
    p = cell.paragraphs[0]
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    p.paragraph_format.space_after = Pt(0)
    if align is not None:
        p.alignment = align
    runs(p, lines[0], size, bold)
    for ln in lines[1:]:
        q = cell.add_paragraph()
        q.paragraph_format.space_after = Pt(0)
        if align is not None:
            q.alignment = align
        runs(q, ln, size, bold)
    if shade:
        tcPr = cell._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd")
        sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), shade)
        tcPr.append(sh)


def _place(tbl_el):
    """Append a table element at the end of the body (before sectPr)."""
    body.insert(len(body) - 1, tbl_el)
    from docx.table import Table
    return Table(tbl_el, doc._body)


def template_table(i, values, drop_rows=0):
    """Copy template table i and write values into its second column (row 0 is the header unless i == 0)."""
    t = _place(copy.deepcopy(TPL[i]))
    start = 0 if i == 0 else 1
    for k in range(drop_rows):
        t._tbl.remove(t.rows[-1]._tr)
    for row, v in zip(t.rows[start:], values):
        if isinstance(v, tuple):
            _cell_text(row.cells[0], v[0])
            _cell_text(row.cells[1], v[1])
        else:
            _cell_text(row.cells[1], v)
    _widths(t, [0.3, 0.7] if i else [0.28, 0.72])
    if i == 2:
        _cell_text(t.rows[0].cells[1], "Details", bold=True)
    keep(t, whole=(i in (0, 5)))
    para(after=4)
    return t


def keep(t, whole=False):
    rows = t.rows[:-1] if whole else t.rows[:1]
    for r in rows:
        for c in r.cells:
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next = True
    for r in t.rows:
        trPr = r._tr.get_or_add_trPr()
        if trPr.find(qn("w:cantSplit")) is None:
            cs = OxmlElement("w:cantSplit"); trPr.insert(0, cs)


def _widths(t, fracs):
    ws = [int(FULL_W * f) for f in fracs]
    grid = t._tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), ws):
        gc.set(qn("w:w"), str(w))
    for row in t.rows:
        for c, w in zip(row.cells, ws):
            tcW = c._tc.get_or_add_tcPr().find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW"); c._tc.get_or_add_tcPr().insert(0, tcW)
            tcW.set(qn("w:w"), str(w)); tcW.set(qn("w:type"), "dxa")


def caption(kind, text):
    n = (FIG if kind == "Figure" else TAB)
    n[0] += 1
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    _font(p.add_run(f"{kind} {n[0]}. "), 10, bold=True)
    _font(p.add_run(text), 10, italic=True)
    if kind == "Table":
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(3)
    return p


def table(rows, fracs, title=None, size=9.5, align_num=True):
    if title:
        caption("Table", title)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            num = align_num and i > 0 and j > 0 and str(v).replace(".", "").replace("%", "").replace("-", "").replace(",", "").strip().isdigit()
            _cell_text(t.cell(i, j), str(v), size, bold=(i == 0), shade="D9EAF7" if i == 0 else None,
                       align=WD_ALIGN_PARAGRAPH.CENTER if (i == 0 or num) else None)
    for r in t.rows[:1]:
        trPr = r._tr.get_or_add_trPr()
        h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)
    _widths(t, fracs)
    keep(t, whole=len(rows) <= 8)
    para(after=4)
    return t


def figure(path, text, width=6.6):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    caption("Figure", text)


def page_break():
    para(after=0).add_run().add_break(WD_BREAK.PAGE)


def field(p, instr):
    r = p.add_run()
    for kind, txt in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        if kind:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), kind); r._r.append(e)
        elif txt == instr:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = instr; r._r.append(e)
        else:
            e = OxmlElement("w:t"); e.text = txt; r._r.append(e)


# ================================================================== cover (NIIT layout)
def cover():
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
    p.add_run().add_picture(str(HERE / "niit_logo.png"), width=Cm(13.5))
    for t, sz, after in (("B. Tech. CSE Semester V", 16, 2), (f"L-T-P-C: {C.LTPC}", 16, 2), (f"Session: {C.YEAR}", 16, 30),
                         (f"{COURSE} ({CODE})", 17, 2), ("AI AND ML PROJECT REPORT", 17, 14), (C.TITLE, 15, 26)):
        para(t, size=sz, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=after)
    for name, enr in C.TEAM:
        p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
        r = p.add_run(f"Name: {name}    Enrollment No.: {enr}"); _font(r, 14, bold=True)
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=40)
    r = p.add_run(f"Section: {C.SECTION}"); _font(r, 14, bold=True); r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    grey = RGBColor(0x80, 0x80, 0x80)
    t = doc.add_table(rows=1, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    l, rc = t.rows[0].cells
    _font(l.paragraphs[0].add_run(f"Submitted To: {FACULTY}"), 13, color=grey)
    _font(rc.paragraphs[0].add_run("Submitted By:"), 13, color=grey)
    for name, enr in C.TEAM:
        q = rc.add_paragraph(); q.paragraph_format.space_after = Pt(0)
        _font(q.add_run(f"{name} ({enr})"), 13, color=grey)
    # new section for the report body, page numbers from 1
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    doc.sections[0].footer.is_linked_to_previous = False
    for fp in doc.sections[0].footer.paragraphs:
        for r in list(fp.runs):
            r._element.getparent().remove(r._element)
    sec.footer.is_linked_to_previous = False
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field(fp, "PAGE")
    pg = sec._sectPr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sec._sectPr.append(pg)
    pg.set(qn("w:start"), "1")


cover()

# ================================================================== title + project table
body.insert(len(body) - 1, copy.deepcopy(TITLE_P))
template_table(0, [
    C.TITLE,
    "",
    [f"{n} - {e} - {C.SECTION}" for n, e in C.TEAM],
    f"B.Tech CSE / {C.SECTION}",
    C.YEAR,
    FACULTY,
])

cr = F["crop"]; fe = F["fert"]; yi = F["yield"]; lf = F["leaf"]
LT = LEAF["test"]
FC = FERT["chosen"]

# ================================================================== 1 abstract
h1("1. Abstract")
para("Most small farmers in India choose a crop, buy fertiliser and react to leaf disease based on habit or on what "
     "the local shop suggests. This project builds AgriSense AI, a web dashboard and Android app that turns soil, "
     "climate and crop data into those three decisions. It uses supervised learning for four tasks: crop "
     f"recommendation (Random Forest, {cr['rows']:,} records, {cr['classes']} crops), district yield prediction "
     f"(LightGBM, {yi['clean_rows']:,} cleaned government records), fertiliser recommendation (Logistic Regression, "
     f"{fe['rows']} records) and leaf-disease detection (EfficientNet-B0, {lf['images']:,} leaf images, {lf['classes']} classes). "
     "A small reasoning layer joins the crop and fertiliser models: it measures how far the soil falls short of the "
     "chosen crop's typical N, P and K and only accepts a fertiliser that supplies every nutrient that is short.")
para("Each algorithm was chosen by comparing several candidates with cross-validation, then tested on data it had not "
     f"seen against a simple baseline. The crop model reached {pct(CROP['test_accuracy'])} accuracy (majority baseline "
     f"{pct(cr['majority_share'])}). The yield model reached R² {YR['LightGBM (this model)']['r2']} on later years "
     f"it was not trained on, against {YR['Baseline: last year' + chr(39) + 's yield']['r2']} for last year's yield. The leaf model "
     f"reached {pct(LT['accuracy'])} accuracy with calibrated confidence. The fertiliser model scored "
     f"{pct(FC['cv_accuracy_mean'], 1)} in repeated cross-validation, a figure with wide uncertainty because the "
     f"dataset has only {fe['rows']} rows. The system is deployed and handles about "
     f"{LOAD['capacity_users_p95_under_2s']} users at the same time on a 2-core server.")

# ================================================================== 2 problem
h1("2. Problem Statement and Objectives")
para("**Real-world problem:** A Soil Health Card gives a farmer N, P and K values, but it does not say which crop suits "
     "the field or which of the many fertiliser grades in the shop to buy. Leaf diseases are often recognised only after "
     "they have spread. Weather, soil and yield records exist on different government and research websites, mostly in "
     "English. The people affected are small and marginal farmers, the extension officers who advise them, and "
     "agriculture students. Wrong choices cost money through lost yield and through fertiliser that the soil did not need.")
para("**Objectives:**", after=2)
bullets([
    "Frame crop choice and fertiliser choice as classification, yield as regression and leaf diagnosis as image "
    "classification, and join crop and fertiliser in one decision chain.",
    "Select each algorithm by comparing several candidates with cross-validation instead of picking one by habit.",
    "Train four ML models on public Indian and PlantVillage-derived data and serve them through one API used by the "
    "web dashboard and the Android app.",
    "Evaluate every model on held-out data against a simple baseline, using metrics that suit the task.",
    "Analyse the errors and the limits of each dataset, and list what would improve each model.",
])

# ================================================================== 3 formulation
h1("3. AI Problem Formulation")
para("The system answers four questions for a farmer. Three are learned from labelled data; the fourth step, "
     "turning a soil reading into a fertiliser need, is a rule-based reasoning step placed between two models.")
template_table(1, [
    "Classification (crop, fertiliser, leaf disease), regression (yield) and rule-based reasoning that links the "
    "crop and fertiliser models.",
    "Soil N, P, K, temperature, humidity, pH and rainfall; state, district, crop, season, year and area; "
    "a photo of one leaf.",
    "A crop with its probability and three alternatives; yield in t/ha with an 80% range; a fertiliser name and "
    "grade, or 'no fertiliser needed'; a disease name with calibrated confidence, or 'needs review'.",
    ["Random Forest for crops (best of 5 models in 5-fold CV).",
     "LightGBM for yield (handles 700+ districts as categories and trains in minutes on 3 lakh rows).",
     "Logistic Regression for fertiliser (best of 8 in 5x5 repeated CV; the simplest model that separates the classes).",
     "EfficientNet-B0 transfer learning for leaves (high accuracy with 5.3 M parameters, runs on a CPU through ONNX)."],
    "Learns patterns from labelled records; reasons about nutrient shortfall; refuses to name a disease when its "
    "calibrated confidence is below 0.95; an LLM assistant (Mistral) explains a result in 15 languages using the "
    "farmer's own data, without giving doses.",
    "Small and marginal farmers, agricultural extension officers, agriculture students.",
    "Each model beats its baseline on held-out data; the leaf model is at least 99.9% accurate on the photos it "
    "answers (validation); the server answers 95% of requests within 2 s with 100 users at once.",
])
h2("3.1 Reasoning step between the crop and fertiliser models")
para("The fertiliser dataset describes the nutrient that has to be supplied, while a soil test describes what is "
     "already in the soil. The two cannot be fed into one model directly, so a rule step converts one into the other:")
numbered([
    "Take the typical level for the chosen crop: the median N, P and K of that crop in the crop dataset, or the "
    "middle of the Soil Health Card band (N 420, P 17.5, K 195 kg/ha) for a lab soil test.",
    "Compute the shortfall of each nutrient as a fraction of the typical level. Shortfalls under 5% count as zero.",
    "If nothing is short, stop: the answer is 'no fertiliser needed' and the model is not called.",
    "Scale the shortfall vector so the most-short nutrient sits at the top of the fertiliser dataset's range "
    "(N 42, P 42, K 19), keeping the ratio between nutrients.",
    "Mark as required every nutrient whose shortfall is at least a quarter of the largest one.",
    "Run the fertiliser model and take its highest-probability class whose grade supplies all required nutrients.",
])
ch = F["chain"]
para(f"Example: a maize field with N {ch['input']['N']:.0f}, P {ch['input']['P']} and K {ch['input']['K']}. Maize's typical "
     f"levels are N {ch['typical']['N']}, P {ch['typical']['P']} and K {ch['typical']['K']}, so N is "
     f"{ch['shortfall']['N'] * 100:.1f}% short, K is {ch['shortfall']['K'] * 100:.0f}% short and P is adequate. Both N and K "
     f"pass the one-quarter rule, so the answer must supply both; the system returns **{ch['fert']}**, a balanced "
     "NPK grade. Urea would have been rejected because it supplies no potassium.")
figure(MYFIGS / "ai_chain.png", "AI decision chain: two learned models joined by a reasoning step, plus the separate leaf-disease model.")

# ================================================================== 4 ML
h1("4. Machine Learning Component")
para("The project has four ML models. Each is described below with the template's items, followed by five real "
     "records from its dataset with the original field names. All counts were measured on the files used for training.")


def records_table(recs, cols, title, fmt=None, fracs=None):
    rows = [cols] + [[(fmt or {}).get(c, lambda v: v)(r[c]) for c in cols] for r in recs]
    table(rows, fracs or [1 / len(cols)] * len(cols), title, size=8.5)


r2 = lambda v: f"{v:.2f}"  # noqa: E731
h2("4.1 Crop recommendation")
template_table(2, [
    f"Multi-class classification ({cr['classes']} crops)",
    "One soil sample with the climate of its field",
    "Crop Recommendation Dataset (Crop_recommendation.csv), A. Ingle, Kaggle; compiled from Indian agricultural data",
    "Public dataset, used for academic work as permitted on its Kaggle page",
    "Held in full",
    f"{cr['rows']:,} samples, {cr['features']} features (N, P, K, temperature, humidity, ph, rainfall)",
    "label: the crop suited to the given soil and climate",
    f"{cr['classes']} classes with exactly {cr['per_class']} samples each ({pct(cr['majority_share'])} per class)",
    "Permutation importance on the test set: " + ", ".join(f"{d['feature']} {d['importance']:.3f}" for d in CROP["permutation_importance"]),
    "Given by the dataset author for each soil and climate combination; not measured yield outcomes",
    f"Majority class: {pct(cr['majority_share'])} accuracy. Simple model: Logistic Regression, "
    f"{pct(CROP['comparison'][0]['test_accuracy'])}",
    "Accuracy (classes are balanced), with macro F1 and per-class precision and recall",
    "80/20 stratified split, seed 42; model chosen by 5-fold CV on the 80% part only, so the 20% stays unseen",
])
records_table(cr["records"], cr["columns"], "Five records from Crop_recommendation.csv (decimals rounded to 2 places)",
              {c: r2 for c in ("temperature", "humidity", "ph", "rainfall")})

h2("4.2 Yield prediction")
template_table(2, [
    "Regression (yield in tonnes per hectare)",
    "One district, crop, season and year",
    "India Agriculture Crop Production, Directorate of Economics and Statistics, published on data.gov.in (1997-98 to 2020-21)",
    "Public government data under the Government Open Data License - India",
    "Held in full",
    f"{yi['raw_rows']:,} raw rows and {len(yi['columns'])} columns; {yi['clean_rows']:,} rows after cleaning; "
    f"{len(YLD['features'])} model features ({yi['crops']} crops, {yi['districts']} districts, {yi['states']} states)",
    "Yield = Production / Area (t/ha). The model learns log(1+yield) minus log(1+base), where base is the 3-year mean "
    "or the nearest available history",
    f"Mean {yi['yield_mean']} t/ha, SD {yi['yield_sd']}, median {yi['yield_median']}, range {yi['yield_min']} to "
    f"{yi['yield_max']} (skewed by sugarcane, banana and tapioca)",
    "Gain importance: " + ", ".join(f"{d['feature']} {d['importance']:.3f}" for d in YLD["importance_gain"][:6]) +
    ". Lag features are the same district's earlier yields",
    "Official area and production returns reported by state agriculture departments",
    f"Last year's yield: R² {YR['Baseline: last year' + chr(39) + 's yield']['r2']}, MAE {YR['Baseline: last year' + chr(39) + 's yield']['mae_t_ha']} t/ha. "
    f"Mean of previous 3 years: R² {YR['Baseline: mean of previous 3 years']['r2']}, MAE {YR['Baseline: mean of previous 3 years']['mae_t_ha']}",
    "MAE in t/ha (easy to read for a farmer), with R² and median percentage error",
    f"Temporal split: train on crop years before 2017-18 ({YLD['rows_train']:,} rows), test on 2017-18 onwards "
    f"({YLD['rows_test']:,} rows). A random split would let the model see the future of the same district",
])
recs = [dict(r, Yield=round(r["Yield"], 3)) for r in yi["records"]]
records_table(recs, yi["columns"], "Five records from India Agriculture Crop Production.csv",
              fracs=[0.13, 0.12, 0.08, 0.08, 0.1, 0.09, 0.09, 0.11, 0.11, 0.09])

h2("4.3 Fertiliser recommendation")
template_table(2, [
    f"Multi-class classification ({len(FERT['classes'])} fertiliser grades)",
    "One field record: weather, moisture, soil type, crop and the nutrient values, with the fertiliser used",
    "Fertilizer Prediction dataset (Fertilizer Prediction.csv), Kaggle",
    "Public dataset, used for academic work as permitted on its Kaggle page",
    "Held in full",
    f"{fe['rows']} samples, {fe['features']} features",
    "Fertilizer Name: one of Urea, DAP, 28-28, 14-35-14, 20-20, 17-17-17, 10-26-26",
    ", ".join(f"{k} {v}" for k, v in fe["counts"].items()) + f" (largest class {pct(fe['majority_share'], 1)})",
    "Permutation importance: " + ", ".join(f"{d['feature']} {d['importance']:.3f}" for d in FERT["permutation_importance_all_features"][:3]) +
    "; temperature, humidity, moisture, soil type and crop type all 0.000, so the final model uses N, P and K only",
    "Given by the dataset author; how the records were collected is not documented",
    f"Majority class (Urea): {pct(fe['majority_share'], 1)} accuracy",
    "Accuracy, with macro F1 on a hold-out set",
    f"5-fold stratified CV repeated 5 times on all {fe['rows']} rows to choose the model; a 20-row stratified hold-out as a second check",
])
records_table(fe["records"], fe["columns"], "Five records from Fertilizer Prediction.csv (field names as in the file, including its spelling)")

h2("4.4 Leaf-disease detection")
template_table(2, [
    f"Image classification ({lf['classes']} classes: 38 crop-condition pairs and one 'no leaf' background class)",
    "One photo of a single leaf on a plain background",
    "Data for: Identification of Plant Leaf Diseases Using a 9-layer Deep CNN, Mendeley Data (Arun Pandian and "
    "Geetharamani, 2019), derived from PlantVillage",
    "Public dataset under CC BY 4.0",
    "Held in full (original and augmented sets)",
    f"{lf['images']:,} original images (256 x 256 RGB), {lf['classes']} classes; the augmented set adds "
    f"{LEAF['deployed_fit']['synthetic']:,} synthetic images. Input resized to 224 x 224",
    "Folder name of the image, for example Tomato___Late_blight (crop and condition)",
    f"Imbalanced: largest {lf['largest'].replace('___', ' / ').replace('_', ' ')} {lf['largest_n']:,} images, smallest "
    f"{lf['smallest'].replace('___', ' / ').replace('_', ' ')} {lf['smallest_n']}",
    "Learned from pixels by the network; no hand-made features",
    "Labelled by plant pathologists in the PlantVillage project",
    f"Majority class on the test split: {pct(lf['majority_share'])} accuracy",
    "Macro recall (because of the imbalance), with accuracy, macro F1 and expected calibration error (ECE)",
    f"Stratified 70/15/15 split, seed 42: {LEAF['split']['train']:,} train, {LEAF['split']['val']:,} validation, "
    f"{LEAF['split']['test']:,} test. Synthetic images only in training; {LEAF['split']['synthetic_dropped_leak_guard']:,} "
    "were dropped because they were copies of validation or test images",
])
records_table(lf["records"], ["file", "folder (label)", "width x height", "mode", "size_kb"],
              "Five records from the leaf image set (an image record is a file and its class folder)",
              fracs=[0.17, 0.38, 0.17, 0.1, 0.18])

# ================================================================== 5 methodology
h1("5. AI/ML Methodology")
para("All four models follow the same pipeline (Figure 2). Every metric quoted in this report is written by the "
     "training script into a JSON model card, which the app and this report read.")
numbered([
    "**Problem definition and formulation:** each farmer question was mapped to one task type (Table in Section 3) "
    "and a success criterion was fixed before training.",
    "**Dataset selection:** public datasets that match Indian crops and conditions, with a known source and "
    "enough rows; the yield data comes from the Government of India.",
    "**Data understanding and preprocessing:** units checked (the yield file mixes tonnes, bales and nuts, so only "
    "tonnes were kept), impossible yields above the 99.5th percentile per crop removed, duplicate district rows summed, "
    "images checked for copies across splits.",
    "**Model selection:** 5 classifiers for crops, 8 candidates (4 algorithms x 2 feature sets) for fertiliser, "
    "gradient boosting against three baselines for yield, a pretrained CNN for leaves.",
    "**Training:** scikit-learn and LightGBM on CPU; EfficientNet-B0 for 8 epochs on an RTX 5070 Ti GPU with mixed "
    "precision (about 214 s per epoch).",
    "**Parameter tuning:** LightGBM early stopping (best iteration 975); leaf learning-rate schedule and class "
    "weights; leaf confidence threshold and temperature fitted on the validation set only.",
    "**Evaluation and comparison with baseline:** held-out test data for every model; majority class, last-year "
    "and 3-year-mean baselines; calibration error for the leaf model.",
    "**Interpretation of results:** permutation and gain importance, SHAP contributions per yield prediction, "
    "confusion matrices, and a per-crop breakdown of yield error.",
])
figure(MYFIGS / "ml_pipeline.png", "ML pipeline used for every model.")
figure(FIGS / "architecture.png", "System architecture: the web dashboard and Android app call one FastAPI server that hosts the models.", width=6.2)

# ================================================================== 6 implementation
h1("6. Implementation Details")
template_table(3, [
    ["Every request is checked against allowed ranges (for example pH 3 to 10) and rejected with a clear message.",
     "Yield inputs must be a state, district, crop and season combination present in the data.",
     "Leaf photos are rotated by their EXIF tag, resized to 224 x 224 and normalised with ImageNet mean and SD."],
    "Shortfall reasoning of Section 3.1; a fertiliser is accepted only if its grade supplies every required nutrient. "
    "The crop result also reports which inputs fall outside the chosen crop's usual band.",
    ["Crop: Random Forest, 400 trees, refit on all 2,200 rows after testing.",
     "Yield: LightGBM, L1 loss, learning rate 0.05, 127 leaves, at least 40 rows per leaf, early stopping.",
     "Fertiliser: standardised N, P, K into multinomial Logistic Regression.",
     "Leaf: EfficientNet-B0 from ImageNet weights, class-weighted cross-entropy with label smoothing 0.05, AdamW "
     "(lr 0.001), one-cycle schedule, batch 96, 8 epochs; exported to ONNX."],
    ["Crop: class probabilities, top 4 shown with a 0-100 suitability score per input.",
     "Yield: base x exp(predicted log ratio), with an 80% range from test residual quantiles.",
     "Leaf: average of the photo and its mirror image, divided by temperature 0.570, softmax; below 0.95 the result is "
     "'needs review'."],
    "Python 3.12, pandas, NumPy, scikit-learn, LightGBM, PyTorch and torchvision, ONNX Runtime, SHAP-style "
    "contributions from LightGBM, FastAPI, SQLite, Mistral API for the assistant, Kotlin with Jetpack Compose for the app",
    ["Training: Windows 11 PC, NVIDIA RTX 5070 Ti (CUDA 12.8), fixed seed 42.",
     f"Serving: Docker on a VPS with 2 vCPU ({LOAD['host']['cpu'].split(' Processor')[0]}) and 8 GB RAM, 2 server workers."],
])

# ================================================================== 7 results
h1("7. Results and Evaluation")
para("All results below are from data the model did not train on. The summary table gives the main figures; the "
     "sub-sections show the comparisons, the class-level results and the charts.")
B = LOAD["bench"]
template_table(4, [
    [f"Crop: accuracy {pct(CROP['test_accuracy'])}",
     f"Yield: MAE {YR['LightGBM (this model)']['mae_t_ha']} t/ha",
     f"Fertiliser: CV accuracy {pct(FC['cv_accuracy_mean'], 1)} (SD {FC['cv_accuracy_std']})",
     f"Leaf: macro recall {pct(LT['macro_recall'])}"],
    [f"Crop: macro F1 {CROP['test_macro_f1']}",
     f"Yield: R² {YR['LightGBM (this model)']['r2']}, median error {YR['LightGBM (this model)']['mape_median_pct']}%",
     f"Fertiliser: hold-out accuracy {pct(FC['holdout_accuracy'], 0)}, macro F1 {FC['holdout_macro_f1']}",
     f"Leaf: accuracy {pct(LT['accuracy'])}, macro F1 {LT['macro_f1']}, ECE {LT['ece_after_T']}"],
    [f"Crop: majority {pct(cr['majority_share'])}; Logistic Regression {pct(CROP['comparison'][0]['test_accuracy'])}",
     f"Yield: last year MAE {YR['Baseline: last year' + chr(39) + 's yield']['mae_t_ha']}, 3-year mean MAE {YR['Baseline: mean of previous 3 years']['mae_t_ha']}",
     f"Fertiliser: majority {pct(fe['majority_share'], 1)}",
     f"Leaf: majority {pct(lf['majority_share'])}"],
    [f"Crop: {pct(CROP['test_accuracy'])}", f"Yield: MAE {YR['LightGBM (this model)']['mae_t_ha']} t/ha",
     f"Fertiliser: {pct(FC['cv_accuracy_mean'], 1)}", f"Leaf: {pct(LT['accuracy'])}; {pct(LT['accuracy_when_answered'])} on the {pct(LT['answered_fraction'], 1)} of photos it answers"],
    [f"Crop: +{(CROP['test_accuracy'] - cr['majority_share']) * 100:.1f} points over majority, "
     f"+{(CROP['test_accuracy'] - CROP['comparison'][0]['test_accuracy']) * 100:.1f} over Logistic Regression",
     f"Yield: MAE {(1 - YR['LightGBM (this model)']['mae_t_ha'] / YR['Baseline: mean of previous 3 years']['mae_t_ha']) * 100:.1f}% lower than the 3-year mean",
     f"Fertiliser: +{(FC['cv_accuracy_mean'] - fe['majority_share']) * 100:.1f} points over majority",
     f"Leaf: +{(LT['accuracy'] - lf['majority_share']) * 100:.1f} points over majority"],
    [f"Mean time per prediction on one server core: crop {B['crop_recommendation']['mean_ms']} ms, yield "
     f"{B['yield_prediction']['mean_ms']} ms, fertiliser {B['fertiliser']['mean_ms']} ms, leaf {B['leaf_disease']['mean_ms']} ms",
     f"Leaf training: {sum(h['seconds'] for h in LEAF['history'] if h['run'] == 'evaluation') / 60:.0f} min for 8 epochs on the GPU",
     f"Server: {LOAD['capacity_users_p95_under_2s']} users at once with 95% of answers under 2 s ({LOAD['capacity_rps_at_that_point']} requests/s)"],
    "Real outputs for records of every dataset are listed in Table " + "{SAMPLES}" + " in Section 7.5.",
])

h2("7.1 Crop recommendation")
rows = [["Model", "CV accuracy (mean ± SD)", "Test accuracy", "Test macro F1", "Training time (s)"]]
for c in sorted(CROP["comparison"], key=lambda c: -c["cv_accuracy_mean"]):
    rows.append([c["model"], f"{pct(c['cv_accuracy_mean'])} ± {c['cv_accuracy_std'] * 100:.2f}", pct(c["test_accuracy"]),
                 f"{c['test_macro_f1']:.4f}", c["train_seconds"]])
table(rows, [0.28, 0.22, 0.16, 0.16, 0.18], "Five classifiers compared on the crop data (model chosen on CV accuracy)")
pc = CROP["per_class"]
imperfect = [(k, v) for k, v in pc.items() if v["f1-score"] < 1]
para(f"Random Forest had the best cross-validated accuracy and was chosen. On the 440 test samples it made "
     f"{round(440 * (1 - CROP['test_accuracy']))} mistakes. Only {len(imperfect)} of the 22 crops are below a perfect F1 score:")
table([["Crop", "Precision", "Recall", "F1", "Test samples"]] +
      [[k, f"{v['precision']:.3f}", f"{v['recall']:.3f}", f"{v['f1-score']:.3f}", int(v["support"])] for k, v in imperfect],
      [0.3, 0.17, 0.17, 0.17, 0.19], "Crops with any test error (all other crops: precision, recall and F1 = 1.000)")
para("The confusions are between crops that need similar soil and rain, such as rice and jute, and blackgram and "
     "maize. Accuracy this high is a sign of how clean the dataset is: it has exactly 100 well-separated rows per crop, "
     "so real soil tests will give lower accuracy.")
figure(FIGS / "crop_confusion.png", "Crop model confusion matrix on the 20% test split.", width=4.3)

h2("7.2 Yield prediction")
rows = [["Method", "R²", "MAE (t/ha)", "Median % error"]]
for k in ("LightGBM (this model)", "Baseline: mean of previous 3 years", "Baseline: last year's yield", "Baseline: national crop mean"):
    v = YR[k]
    rows.append([k.replace("Baseline: ", "Baseline - "), f"{v['r2']:.4f}", f"{v['mae_t_ha']:.4f}", f"{v['mape_median_pct']:.2f}"])
table(rows, [0.46, 0.16, 0.18, 0.2], f"Yield on the test years 2017-18 onwards ({YLD['rows_test']:,} rows)")
para("The model has the lowest MAE and the highest R². Last year's yield is a strong baseline because district "
     "yields change slowly; it even has a lower median percentage error, which shows that the model's gain is mainly "
     "on large errors, where a bad or good season moves the yield far from the previous year. The model has no "
     "rainfall or soil input (they are not in the dataset), so it cannot foresee a drought.")
pcrop = YLD["per_crop_test"][:6]
table([["Crop", "Test rows", "R²", "MAE (t/ha)", "Median % error"]] +
      [[p["crop"], f"{p['rows']:,}", f"{p['r2']:.3f}", f"{p['mae_t_ha']:.3f}", f"{p['mape_median_pct']:.1f}"] for p in pcrop],
      [0.32, 0.16, 0.16, 0.16, 0.2], "Per-crop test results for the six crops with the most test rows")
para("Within a single crop, R² is lower (0.34 to 0.74) because the overall figure also benefits from the large "
     "differences between crops. Pulses such as moong and urad are the hardest to predict.")
figure(FIGS / "yield_baselines.png", "Yield model against the baselines on the test years.", width=5.6)

h2("7.3 Fertiliser recommendation")
rows = [["Algorithm", "Features", "CV accuracy (mean ± SD)", "Hold-out accuracy", "Hold-out macro F1"]]
for c in sorted(FERT["comparison"], key=lambda c: -c["cv_accuracy_mean"]):
    rows.append([c["model"], c["features"], f"{pct(c['cv_accuracy_mean'], 1)} ± {c['cv_accuracy_std'] * 100:.1f}",
                 pct(c["holdout_accuracy"], 0), f"{c['holdout_macro_f1']:.3f}"])
table(rows, [0.26, 0.16, 0.24, 0.17, 0.17], "Eight candidates compared with 5x5 repeated cross-validation")
para("Every algorithm does better on N, P and K alone than on all eight features; K-Nearest Neighbours falls to "
     "23% when soil type, crop type and weather are added, because those columns carry no signal here and swamp the "
     "distance. Logistic Regression made no error in 25 folds. With 99 rows this does not mean the model is perfect: "
     "it means the seven grades are cleanly separated by N, P and K in this dataset. The reasoning step in Section 3.1, "
     "not the model, is where real-world uncertainty enters.")
figure(FIGS / "fert_comparison.png", "Cross-validated accuracy of the eight fertiliser candidates.", width=5.6)

h2("7.4 Leaf-disease detection")
para(f"On the {LEAF['split']['test']:,} test images the model reached {pct(LT['accuracy'])} accuracy and "
     f"{pct(LT['macro_recall'])} macro recall. Dividing the outputs by a temperature of {LEAF['temperature']} lowered the "
     f"expected calibration error from {LT['ece_before_T']} to {LT['ece_after_T']}, so a reported confidence of 0.97 "
     f"really means about 97%. With the 0.95 threshold the model answers {pct(LT['answered_fraction'], 2)} of photos and is "
     f"right on {pct(LT['accuracy_when_answered'])} of them; the rest are sent for review instead of being guessed.")
table([["Class", "Recall"]] + [[k.replace("___", " / ").replace("_", " "), f"{v:.4f}"] for k, v in lf["lowest_recall"]],
      [0.7, 0.3], "The six classes with the lowest test recall (the other "
      f"{len(LEAF['per_class_recall']) - 6} classes are at "
      f"{sorted(LEAF['per_class_recall'].values())[6]:.3f} or higher; "
      f"{sum(v == 1 for v in LEAF['per_class_recall'].values())} are at 1.000)")
para("The weakest classes are corn leaf spot and northern leaf blight, which look alike, and tomato target spot "
     "against early blight. All test photos are lab images of single leaves; accuracy on field photos with soil, "
     "shadows or several leaves has not been measured and will be lower.")
figure(FIGS / "leaf_history.png", "Leaf model validation accuracy and training loss per epoch.", width=5.4)
figure(FIGS / "leaf_confusion.png", "Leaf model confusion matrix on the test split (39 classes).", width=5.8)

h2("7.5 Sample outputs and server capacity")
S_TABLE = TAB[0] + 1
rows = [["Model", "Input", "Actual / reference", "System output"]]
for s in F["samples"]:
    rows.append([s["model"], s["input"].replace("___", " / "), s["truth"].replace("___", " / "), s["output"].replace("___", " / ")])
table(rows, [0.13, 0.43, 0.2, 0.24], "Real outputs from the deployed models", size=8.5, align_num=False)
para("The crop, fertiliser and leaf rows are taken from the datasets. The deployed models were refit on all "
     "data after testing, so these rows show the pipeline working, not new accuracy figures. The yield rows predict "
     "2021-22, a year after the last year in the data, so there is no actual value yet; the district's average is given "
     "for comparison.")
st = {s["users"]: s for s in LOAD["step"]}
table([["Users at once", "Requests/s", "Median (ms)", "95th percentile (ms)", "Errors"]] +
      [[u, st[u]["rps"], st[u]["p50_ms"], st[u]["p95_ms"], st[u]["errors"]] for u in sorted(st)],
      [0.2, 0.2, 0.2, 0.22, 0.18], "Load test on a copy of the server (2 vCPU, 8 GB RAM, mixed API traffic)")
para(f"Up to {LOAD['capacity_users_p95_under_2s']} users, 95% of answers came back within 2 seconds and no request "
     "failed. Beyond that the two CPU cores are saturated: throughput stays near 60 to 68 requests per second and "
     "waiting time grows, but still without errors.")
figure(FIGS / "load_step.png", "Response time and throughput as the number of simultaneous users grows.", width=5.8)

# ================================================================== 8 conclusion
h1("8. Conclusion and Future Scope")
para("The project built an AI system for farm decisions using supervised learning for crop recommendation, yield "
     "prediction, fertiliser choice and leaf-disease detection, joined by a rule-based reasoning step that turns a soil "
     "reading into a fertiliser need. Each model was chosen by cross-validation and tested on unseen data against a "
     f"baseline: {pct(CROP['test_accuracy'])} accuracy for crops (baseline {pct(cr['majority_share'])}), MAE "
     f"{YR['LightGBM (this model)']['mae_t_ha']} t/ha for yield (best baseline {YR['Baseline: last year' + chr(39) + 's yield']['mae_t_ha']}), "
     f"{pct(LT['accuracy'])} for leaf disease with calibrated confidence, and {pct(FC['cv_accuracy_mean'], 1)} cross-validated "
     "accuracy for fertiliser. The system is live on the web and on Android and serves about 100 users at once.")
para("Major limitations: the crop dataset is clean and balanced, so its accuracy overstates real-world performance; "
     "the yield model works per district and has no weather or soil input; the fertiliser model learned from 99 "
     "rows and the link between soil tests and its scale is an approximation; the leaf model has only been measured on "
     "lab photos.")
para("Future work:", after=2)
bullets(C.FUTURE)

# ================================================================== 9 team
h1("9. Team Contribution")
team_rows = [
    (f"{C.TEAM[0][0]} / {C.TEAM[0][1]}", "AI problem formulation, system design, leaf-disease CNN (GPU training, "
     "calibration, ONNX), shortfall reasoning step, deployment"),
    (f"{C.TEAM[1][0]} / {C.TEAM[1][1]}", "Datasets and cleaning, crop and fertiliser models, model comparison "
     "experiments, permutation importance"),
    (f"{C.TEAM[2][0]} / {C.TEAM[2][1]}", "Yield model and baselines, testing of AI/ML results, load test, "
     "documentation and presentation"),
]
template_table(5, team_rows, drop_rows=1)

# ================================================================== 10 references
h1("10. References and Appendices")
para("**Datasets**", after=2)
bullets([
    "A. Ingle, Crop Recommendation Dataset, Kaggle (Crop_recommendation.csv).",
    "Directorate of Economics and Statistics, Ministry of Agriculture and Farmers Welfare, Crop Production Statistics, "
    "data.gov.in, Government Open Data License - India.",
    "Fertilizer Prediction dataset, Kaggle (Fertilizer Prediction.csv).",
    "J. Arun Pandian and G. Geetharamani, Data for: Identification of Plant Leaf Diseases Using a 9-layer Deep "
    "Convolutional Neural Network, Mendeley Data, 2019, CC BY 4.0.",
])
para("**Papers and documentation**", after=2)
bullets([
    "L. Breiman, Random Forests, Machine Learning 45, 5-32, 2001.",
    "G. Ke et al., LightGBM: A Highly Efficient Gradient Boosting Decision Tree, NeurIPS 2017.",
    "M. Tan and Q. V. Le, EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks, ICML 2019.",
    "C. Guo, G. Pleiss, Y. Sun and K. Q. Weinberger, On Calibration of Modern Neural Networks, ICML 2017.",
    "G. Geetharamani and J. Arun Pandian, Identification of plant leaf diseases using a nine-layer deep convolutional "
    "neural network, Computers and Electrical Engineering 76, 323-338, 2019.",
    "D. P. Hughes and M. Salathe, An open access repository of images on plant health to enable the development of "
    "mobile disease diagnostics, arXiv:1511.08060, 2015.",
    "Soil Health Card Scheme, Ministry of Agriculture and Farmers Welfare, soil nutrient rating bands.",
])
para("**Libraries and tools:** scikit-learn, LightGBM, PyTorch, torchvision, ONNX Runtime, pandas, NumPy, "
     "Matplotlib, FastAPI, SQLite, Docker, Mistral API, Kotlin and Jetpack Compose.", after=4)
para(f"**Source code:** submitted with this report (05_Source_Code); live system at {URL}.", after=4)
para("**Dataset records and additional graphs:** five records of each dataset are in Tables "
     f"{{REC}} of Section 4; further figures are in the model report (AgriSense_AI_Model_Report.pdf).", after=14)

para("**Students' Signatures:**", after=22).paragraph_format.keep_with_next = True
t = doc.add_table(rows=2, cols=3)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
for j, (n, e) in enumerate(C.TEAM):
    _cell_text(t.cell(0, j), "______________________", 10.5, align=WD_ALIGN_PARAGRAPH.CENTER)
    _cell_text(t.cell(1, j), f"{n}\n{e}", 10.5, align=WD_ALIGN_PARAGRAPH.CENTER)
keep(t, whole=True)
for c in t.rows[1].cells:
    for q in c.paragraphs:
        q.paragraph_format.keep_with_next = True
for txt, af in (("", 14), ("**Faculty Signature:**", 22), ("______________________", 0)):
    para(txt, align=WD_ALIGN_PARAGRAPH.LEFT, after=af).paragraph_format.keep_with_next = True
para(FACULTY, align=WD_ALIGN_PARAGRAPH.LEFT)

# ------------------------------------------------------------------ fill cross-references written as placeholders
REC_TABLES = "1 to 4"
for p in doc.paragraphs:
    for r in p.runs:
        if "{REC}" in r.text:
            r.text = r.text.replace("{REC}", REC_TABLES)
for tb in doc.tables:
    for row in tb.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    if "{SAMPLES}" in r.text:
                        r.text = r.text.replace("{SAMPLES}", str(S_TABLE))

OUTFILE.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUTFILE)
print("wrote", OUTFILE, FIG[0], "figures", TAB[0], "tables")
