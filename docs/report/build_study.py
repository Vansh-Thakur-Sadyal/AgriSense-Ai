"""Study material: AgriSense AI web dashboard and Android app.
Part A covers the AI and ML side, Part B the software-engineering side. Numbers come from the model cards,
the load-test summary, the requirement list (docs/submission/spec.py) and out/aiml_facts.json.
Usage: python build_study.py <out.docx>"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "docs" / "submission"))
import content as C  # noqa: E402
from spec import FR, NFR  # noqa: E402

OUT = Path(sys.argv[1])
FIGS, AND, MY, UML, WF = (ROOT / "docs" / "figs", ROOT / "docs" / "figs" / "android", HERE / "out" / "figs",
                          ROOT / "docs" / "submission" / "figs", ROOT / "docs" / "submission" / "wf")
F = json.loads((HERE / "out" / "aiml_facts.json").read_text(encoding="utf-8"))
M = ROOT / "app" / "models"
CROP = json.loads((M / "crop_model.json").read_text())
YLD = json.loads((M / "yield_model.json").read_text())
FERT = json.loads((M / "fertiliser_model.json").read_text())
LEAF = json.loads((M / "leaf_disease.json").read_text())
LOAD = json.loads((ROOT / "tests" / "load" / "results" / "summary.json").read_text())
YR, LT, FC = YLD["results"], LEAF["test"], FERT["chosen"]
LASTYR, MEAN3 = "Baseline: last year's yield", "Baseline: mean of previous 3 years"
cr, fe, yi, lf = F["crop"], F["fert"], F["yield"], F["leaf"]
URL = "https://ai.software.microeagle.online"

INK, TEAL, GREY = RGBColor(0x14, 0x2A, 0x4C), RGBColor(0x00, 0x7A, 0x7E), RGBColor(0x60, 0x68, 0x70)
FONT = "Times New Roman"
WIDTH = 21.0 - 2 * 2.3


def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


doc = Document()
st = doc.styles["Normal"]
st.font.name = FONT; st.font.size = Pt(11.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.12
for name, size, color in (("Heading 1", 18, INK), ("Heading 2", 14, TEAL), ("Heading 3", 12, INK)):
    h = doc.styles[name]
    h.font.name = FONT; h.font.size = Pt(size); h.font.bold = True; h.font.color.rgb = color
    rf = h.element.rPr.rFonts
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), FONT)
    h.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 10)
    h.paragraph_format.space_after = Pt(6 if name == "Heading 1" else 4)
    h.paragraph_format.keep_with_next = True
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.3)
sec.top_margin = sec.bottom_margin = Cm(2.0)
FIG, TAB = [0], [0]


def runs(p, text, size=None, bold=False, italic=False, color=None):
    for i, part in enumerate(text.split("**")):
        if not part:
            continue
        r = p.add_run(part)
        r.bold = bold or i % 2 == 1
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    return p


def para(text="", size=None, bold=False, italic=False, align=None, after=None, color=None, style=None):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if text:
        runs(p, text, size, bold, italic, color)
    return p


def body(text):
    return para(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY)


def h1(t):
    return doc.add_heading(t, 1)


def h2(t):
    return doc.add_heading(t, 2)


def h3(t):
    return doc.add_heading(t, 3)


def bullets(items, style="List Bullet"):
    for t in items:
        p = para(style=style, after=2)
        runs(p, t)


def numbered(items):
    # manual numbers so each list restarts at 1
    for i, t in enumerate(items, 1):
        p = para(after=2)
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        runs(p, f"{i}.  " + t)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), fill)
    tcPr.append(sh)


def caption(kind, text):
    n = FIG if kind == "Figure" else TAB
    n[0] += 1
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    r = p.add_run(f"{kind} {n[0]}. "); r.bold = True; r.font.size = Pt(10)
    r = p.add_run(text); r.italic = True; r.font.size = Pt(10)
    if kind == "Table":
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(3)


def table(rows, fracs, title=None, size=10, keep=None):
    if title:
        caption("Table", title)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j)
            c.width = Cm(WIDTH * fracs[j])
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
            runs(p, str(v), size, bold=(i == 0), color=RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else None)
            if i == 0:
                shade(c, "142A4C")
            elif i % 2 == 0:
                shade(c, "EAF4F4")
    trPr = t.rows[0]._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)
    if keep if keep is not None else len(rows) <= 10:
        for r in t.rows[:-1]:
            for c in r.cells:
                for p in c.paragraphs:
                    p.paragraph_format.keep_with_next = True
    para(after=4)
    return t


def figure(path, text, width=WIDTH, max_h=None):
    from PIL import Image
    iw, ih = Image.open(path).size
    w = width
    if max_h and w * ih / iw > max_h:
        w = max_h * iw / ih
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(w))
    caption("Figure", text)


def figure_row(paths, text, height):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
    p.paragraph_format.keep_with_next = True
    for i, pth in enumerate(paths):
        if i:
            p.add_run("  ")
        p.add_run().add_picture(str(pth), height=Cm(height))
    caption("Figure", text)


def note(title, lines):
    """Shaded study box: key points or a definition."""
    t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0); shade(c, "EAF4F4"); c.width = Cm(WIDTH)
    p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(2)
    runs(p, title, 11, bold=True, color=TEAL)
    for ln in lines:
        q = c.add_paragraph(); q.paragraph_format.space_after = Pt(1)
        q.paragraph_format.left_indent = Cm(0.4)
        runs(q, "•  " + ln, 10.5)
    para(after=4)


def qa(pairs):
    for q, a in pairs:
        p = para(after=1); p.paragraph_format.keep_with_next = True
        runs(p, "Q. " + q, bold=True)
        p = para(align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=7)
        p.paragraph_format.left_indent = Cm(0.6)
        runs(p, a)


def page_break():
    para(after=0).add_run().add_break(WD_BREAK.PAGE)


def field(p, instr):
    r = p.add_run()
    for kind, txt in (("begin", None), ("instr", instr), ("separate", None), ("t", "1"), ("end", None)):
        if kind == "instr":
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt
        elif kind == "t":
            e = OxmlElement("w:t"); e.text = txt
        else:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), kind)
        r._r.append(e)


def part_divider(letter, title, sub):
    para(after=6).paragraph_format.page_break_before = True
    for _ in range(5):
        para(after=6)
    para(f"PART {letter}", 16, True, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL, after=4)
    p = doc.add_heading(title, 1); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(sub, 12, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
    page_break()


# ================================================================== cover
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=26)
p.add_run().add_picture(str(HERE / "niit_logo.png"), width=Cm(11))
para("STUDY MATERIAL", 15, True, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL, after=6)
para("AgriSense AI", 30, True, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=2)
para("Web Dashboard and Android App", 18, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=20)
para("Part A: Artificial Intelligence and Machine Learning", 13, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para("Part B: Software Engineering", 13, align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=26)
p.add_run().add_picture(str(AND / "home.png"), height=Cm(6.2))
p.add_run("    ")
p.add_run().add_picture(str(FIGS / "shot_02_overview.png"), height=Cm(6.2))
for n, e in C.TEAM:
    para(f"{n}  ({e})", 12, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
para(f"B.Tech CSE, Semester V, Section {C.SECTION}, Session {C.YEAR}", 11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY, after=1)
para("Artificial Intelligence (CS 322), Dr. Shweta R Malwe  |  Software Engineering (CS 301), Dr. Shreyansh Sharma",
     11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)

s2 = doc.add_section(WD_SECTION.NEW_PAGE)
s2.footer.is_linked_to_previous = False
fp = s2.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
field(fp, "PAGE")
para("Contents", 18, True, color=INK, after=8)
field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
page_break()

# ================================================================== 0 how to use + overview
h1("How to Use This Material")
body("This booklet explains everything in the AgriSense AI project in the order you would be asked about it. "
     "**Part A** covers the intelligence: the four machine-learning models, the reasoning step between them, the "
     "AI assistant and every AI and ML concept you need to explain them. **Part B** covers how the product was "
     "engineered: requirements, architecture, database, security, the web dashboard, the Android app, testing and "
     "deployment. Each chapter ends with likely viva questions and short answers.")
note("Read this first", [
    "Every number here is a measured value from the project's own model cards and test runs, not an estimate.",
    "Shaded boxes are the points to remember. Bold words are the terms an examiner expects you to use.",
    f"Live system: {URL}. The Android app talks to the same server.",
])
h2("The project in one page")
body("AgriSense AI helps an Indian farmer answer four questions: **which crop** to grow, **how much** it will "
     "yield, **which fertiliser** the soil needs, and **whether a leaf is diseased**. A farmer signs in on the web "
     "dashboard or the Android app, enters soil values (or lets the app pick a real sample), uploads a leaf photo, "
     "and gets an answer from a trained model with its confidence and the reasons behind it. An AI assistant then "
     "explains any result in the farmer's own language. Live weather, weather history and soil maps are fetched for "
     "each farm, and every result is saved to the farmer's history.")
table([
    ["Farmer's question", "AI task", "Model", "Main result"],
    ["Which crop suits my soil?", "Multi-class classification", "Random Forest", f"{pct(CROP['test_accuracy'])} accuracy"],
    ["How much will it yield?", "Regression", "LightGBM", f"MAE {YR['LightGBM (this model)']['mae_t_ha']} t/ha, R² {YR['LightGBM (this model)']['r2']}"],
    ["Which fertiliser?", "Classification + rule reasoning", "Logistic Regression", f"{pct(FC['cv_accuracy_mean'], 0)} CV accuracy"],
    ["Is this leaf sick?", "Image classification", "EfficientNet-B0 (CNN)", f"{pct(LT['accuracy'])} accuracy"],
    ["Explain it to me", "Language generation", "Mistral LLM", "15 languages, no doses"],
], [0.26, 0.24, 0.22, 0.28], "The four AI questions and the assistant")
figure(FIGS / "architecture.png", "How the parts fit: both clients call one FastAPI server that hosts the models.")

# ================================================================== PART A
part_divider("A", "Artificial Intelligence and Machine Learning",
             "Concepts, the four models, the reasoning step, the AI assistant and the ML tech stack")

h1("A1. AI and ML Concepts Used in the Project")
body("Before the individual models, these are the ideas the whole project rests on. Learn the definition and "
     "where the project uses it.")
h2("A1.1 Supervised learning")
body("In **supervised learning** a model learns a mapping from inputs (features) to an output (label) using "
     "examples where the right answer is already known. All four models here are supervised: the crop dataset "
     "gives the right crop for each soil sample, the yield data gives the real yield, and each leaf photo sits in a "
     "folder named after its disease.")
table([["Type", "Output", "Used for", "Typical metrics"],
       ["Classification", "A class from a fixed list", "Crop (22), fertiliser (7), leaf disease (39)", "Accuracy, precision, recall, F1"],
       ["Regression", "A number", "Yield in tonnes per hectare", "MAE, RMSE, R²"]],
      [0.2, 0.25, 0.3, 0.25], "Classification versus regression")
h2("A1.2 The algorithms")
h3("Logistic Regression")
body("Despite the name, it is a **classifier**. For each class it computes a weighted sum of the inputs and turns "
     "the scores into probabilities with the **softmax** function: P(class k) = e^(z_k) / Σ e^(z_j). It is fast, "
     "easy to explain and works well when classes can be separated by straight boundaries. The project uses it for "
     "fertiliser, after scaling N, P and K to zero mean and unit variance.")
h3("Decision tree, Random Forest and bagging")
body("A **decision tree** asks a series of yes/no questions (for example 'is humidity above 80?') and ends at a "
     "class. One tree overfits easily. A **Random Forest** trains many trees (400 here), each on a random bootstrap "
     "sample of rows and a random subset of features at each split, then lets them vote. This idea is called "
     "**bagging** (bootstrap aggregating); it reduces variance. The crop model is a Random Forest.")
h3("Gradient boosting and LightGBM")
body("**Boosting** builds trees one after another, each new tree correcting the errors of the trees before it "
     "(it fits the gradient of the loss). **LightGBM** is a fast boosting library that grows trees leaf-wise, "
     "handles categorical features such as district names directly and supports early stopping. The yield model "
     "is LightGBM with an L1 (absolute error) loss, which is robust to outlier yields.")
h3("K-Nearest Neighbours and SVM")
body("**KNN** classifies a point by the majority class of its K closest training points, so it depends entirely "
     "on the distance between points; useless features distort that distance. **SVM** finds the boundary with the "
     "widest margin between classes; the RBF kernel lets that boundary curve. Both were tried as candidates for the "
     "crop and fertiliser models and lost to the chosen models.")
h3("Convolutional neural network (CNN) and transfer learning")
body("A **CNN** learns image features with small filters that slide over the picture: early layers detect edges "
     "and colours, deeper layers detect spots, lesions and leaf shapes. **EfficientNet-B0** is a CNN family that "
     "scales depth, width and resolution together, giving high accuracy with only about 5.3 million parameters. "
     "With **transfer learning** we start from weights already trained on ImageNet (1.2 million everyday photos) "
     "and fine-tune them on leaves, which needs far less data and time than training from zero.")
h3("Large language model (LLM)")
body("The assistant uses a **Mistral** LLM through its API. An LLM predicts text one token at a time. It does not "
     "know the farmer's data, so the server adds a **context** block (the farmer's farms, recent predictions and the "
     "models' measured accuracy) to a **system prompt** with rules. This is called **grounding**: the answer is tied "
     "to real data instead of general knowledge.")
h2("A1.3 Evaluation ideas")
table([
    ["Concept", "Meaning", "Where used"],
    ["Train / test split", "Hold back data the model never sees, to measure honest performance", "All models"],
    ["Stratified split", "Each class keeps the same share in train and test", "Crop, fertiliser, leaf"],
    ["Temporal split", "Train on earlier years, test on later years (no peeking at the future)", "Yield"],
    ["k-fold cross-validation", "Split training data into k parts, train k times, average the score", "Model selection"],
    ["Repeated CV", "Run k-fold several times with different shuffles; steadier on small data", "Fertiliser (5x5)"],
    ["Baseline", "A trivial method the model must beat (majority class, last year's value)", "All models"],
    ["Accuracy", "Share of correct predictions", "Classifiers"],
    ["Precision / recall", "Of predicted X, how many were X / of real X, how many were found", "Per-class results"],
    ["F1 and macro F1", "Harmonic mean of precision and recall; macro = average over classes equally", "Crop, leaf"],
    ["Confusion matrix", "Table of true class against predicted class", "Crop, fertiliser, leaf"],
    ["MAE", "Average absolute error, in the target's unit (t/ha)", "Yield"],
    ["R²", "Share of the target's variance explained (1 = perfect)", "Yield"],
    ["Calibration / ECE", "Whether a stated 90% confidence is right 90% of the time; ECE measures the gap", "Leaf"],
    ["Permutation importance", "Drop in score when one feature's values are shuffled", "Crop, fertiliser"],
    ["SHAP contributions", "How much each feature pushed one prediction up or down", "Yield"],
], [0.22, 0.53, 0.25], "Evaluation concepts and where the project uses them", size=9.5)
note("Formulas to remember", [
    "Accuracy = correct / total.  Precision = TP / (TP + FP).  Recall = TP / (TP + FN).  F1 = 2PR / (P + R).",
    "MAE = average of |actual - predicted|.  R² = 1 - (sum of squared errors / total sum of squares).",
    "Softmax: p_k = e^(z_k) / sum of e^(z_j).  Temperature scaling divides the scores z by T before softmax.",
    "Overfitting: great on training data, poor on new data. Cross-validation and a held-out test detect it.",
])

# ---------------------------------------------------------------- A2 pipeline
h1("A2. The ML Pipeline")
body("Every model follows the same pipeline, written as one training script per model in the ml/ folder. The "
     "script writes the trained model and a JSON **model card** with every metric; the app, the report and the "
     "tests all read the card, so a number can never disagree between places.")
figure(MY / "ml_pipeline.png", "The pipeline every model follows.")
numbered([
    "**Raw data:** CSV files and image folders, kept in data/raw (not committed because of size).",
    "**Clean:** fix units, remove impossible values, sum duplicates, check images for copies.",
    "**Split:** stratified or temporal, with a leak guard so near-copies never cross from train to test.",
    "**Train and compare:** several candidate algorithms scored by cross-validation on the training part only.",
    "**Evaluate:** the chosen model meets the untouched test set once, against simple baselines.",
    "**Refit and serve:** refit on all data with the same settings, export (joblib, LightGBM text or ONNX), write the model card.",
])

# ---------------------------------------------------------------- A3 crop
h1("A3. Model 1: Crop Recommendation")
h2("A3.1 Data")
body(f"**Dataset:** Crop_recommendation.csv (Kaggle, A. Ingle). **{cr['rows']:,} rows**, 7 numeric features and "
     f"one label, **{cr['classes']} crops with exactly {cr['per_class']} rows each**, so a guess of the most common class "
     f"would be right only {pct(cr['majority_share'])} of the time.")
recs = cr["records"]
table([cr["columns"]] + [[r["N"], r["P"], r["K"], f"{r['temperature']:.2f}", f"{r['humidity']:.2f}", f"{r['ph']:.2f}", f"{r['rainfall']:.2f}", r["label"]] for r in recs],
      [0.1, 0.1, 0.1, 0.14, 0.13, 0.1, 0.13, 0.2], "Five real rows of the crop dataset")
h2("A3.2 How it was trained")
bullets([
    "80/20 **stratified** split with seed 42: 1,760 rows to train, 440 to test.",
    "Five candidates compared by **5-fold cross-validation** on the 1,760 training rows only.",
    "Random Forest with 400 trees won and was then tested once on the 440 held-out rows.",
    "For deployment it was refit on all 2,200 rows; the reported accuracy is from the test run.",
])
comp = sorted(CROP["comparison"], key=lambda c: -c["cv_accuracy_mean"])
table([["Model", "CV accuracy", "Test accuracy", "Macro F1", "Train time (s)"]] +
      [[c["model"], pct(c["cv_accuracy_mean"]), pct(c["test_accuracy"]), f"{c['test_macro_f1']:.4f}", c["train_seconds"]] for c in comp],
      [0.3, 0.17, 0.17, 0.16, 0.2], "Crop model comparison")
h2("A3.3 Results and what they mean")
body(f"Test accuracy **{pct(CROP['test_accuracy'])}**, macro F1 {CROP['test_macro_f1']}: only 2 of 440 test rows wrong "
     "(one blackgram predicted as maize, one rice as jute, crops that grow in similar conditions). "
     "**Permutation importance** shows which inputs the forest relies on most:")
table([["Feature", "Importance"]] + [[d["feature"], f"{d['importance']:.3f}"] for d in CROP["permutation_importance"]],
      [0.5, 0.5], "Permutation importance of the crop features")
figure(FIGS / "crop_confusion.png", "Crop confusion matrix: almost everything on the diagonal.", width=11)
h2("A3.4 In the dashboard and the app")
body("The Crop page returns the best crop with its probability, the next three alternatives, and a 0-100 "
     "**suitability score** per input showing whether each value lies inside the band where that crop grows in "
     "the data (10th to 90th percentile). Inputs outside the training range are flagged instead of silently "
     "trusted. In the Android app the same result appears on the Predict tab.")
note("Remember", [
    "Random Forest = many decision trees on bootstrap samples, majority vote (bagging).",
    "Chosen by 5-fold CV, tested once on a stratified 20% hold-out.",
    "Accuracy is high because the dataset is clean and balanced; real soil tests will score lower.",
])

# ---------------------------------------------------------------- A4 yield
h1("A4. Model 2: Yield Prediction")
h2("A4.1 Data and cleaning")
body(f"**Dataset:** India Agriculture Crop Production (Directorate of Economics and Statistics, via data.gov.in), "
     f"1997-98 to 2020-21. {yi['raw_rows']:,} raw rows; after cleaning **{yi['clean_rows']:,} rows** covering "
     f"{yi['crops']} crops, {yi['districts']} districts and {yi['states']} states. Cleaning steps:")
bullets(["Kept only crops measured in tonnes (dropped bales and nuts, which are not comparable).",
         "Dropped rows with less than 1 ha or zero production.",
         "Removed per-crop yields below the 0.5th or above the 99.5th percentile (the raw file has entry errors up to 43,958 t/ha).",
         "Summed duplicate district, crop, season and year rows."])
h2("A4.2 Features and target")
body("The model sees location, crop, season, area and the district's **own past yields** (lag features): last "
     "year's yield, the 3-year mean, the trend, how many past years exist, the district's long-run mean for that "
     "crop, the state's last-year yield and the change in area. Instead of the raw yield it learns the "
     "**log ratio** between this year's yield and a base (the 3-year mean, or the best history available). Learning "
     "a ratio lets one model handle sugarcane at 70 t/ha and pulses at 0.5 t/ha.")
h2("A4.3 Training and testing")
bullets([f"**Temporal split:** train on years before 2017-18 ({YLD['rows_train']:,} rows), test on 2017-18 onwards ({YLD['rows_test']:,} rows).",
         "Why temporal: a random split would let the model see a district's future years while being tested on its past.",
         "LightGBM, L1 loss, learning rate 0.05, 127 leaves, at least 40 rows per leaf, early stopping (best iteration 975).",
         "An 80% prediction range comes from the spread of test errors for that crop."])
meth = ["LightGBM (this model)", MEAN3, LASTYR, "Baseline: national crop mean"]
table([["Method", "R²", "MAE (t/ha)", "Median % error"]] +
      [[m.replace("Baseline: ", "Baseline - "), f"{YR[m]['r2']:.4f}", f"{YR[m]['mae_t_ha']:.4f}", f"{YR[m]['mape_median_pct']:.2f}"] for m in meth],
      [0.46, 0.16, 0.18, 0.2], "Yield model against three baselines on the unseen years")
figure(FIGS / "yield_baselines.png", "MAE and R² of the model and the baselines.", width=14)
h2("A4.4 Explaining a prediction")
body("For every prediction the server asks LightGBM for **SHAP-style contributions** (pred_contrib): how much "
     "each feature pushed this prediction above or below the base. The dashboard shows these as bars, together with "
     "the district's yield history. Gain importance over the whole model puts District first (0.37), then Crop "
     "(0.13) and the state's last-year yield (0.09).")
note("Remember", [
    "Regression with gradient boosting (LightGBM). Target = log ratio to a base yield.",
    "Temporal split because time-series data leaks with a random split.",
    f"Beats last year's yield: MAE {YR['LightGBM (this model)']['mae_t_ha']} vs {YR[LASTYR]['mae_t_ha']} t/ha.",
    "No weather or soil inputs exist in the data, so a drought year cannot be predicted.",
])

# ---------------------------------------------------------------- A5 fertiliser
h1("A5. Model 3: Fertiliser Recommendation")
h2("A5.1 Data")
body(f"**Dataset:** Fertilizer Prediction.csv (Kaggle). Only **{fe['rows']} rows**, 8 features (temperature, humidity, "
     "moisture, soil type, crop type, nitrogen, potassium, phosphorous) and 7 fertiliser classes. Class counts: " +
     ", ".join(f"{k} {v}" for k, v in fe["counts"].items()) + ".")
table([["Fertiliser", "Grade (N-P-K)", "Supplies"]] +
      [[k, v["grade"], v["supplies"]] for k, v in FERT["grades"].items()],
      [0.2, 0.2, 0.6], "The seven fertiliser classes and what each supplies")
h2("A5.2 Model selection")
body("Eight candidates were compared: four algorithms, each on N, P, K only and on all eight features, using "
     "**5-fold stratified cross-validation repeated 5 times** (25 scores each), because 99 rows give unstable "
     "single splits. Permutation importance of every non-nutrient column was exactly 0, so the final model uses "
     "N, P and K only.")
fc = sorted(FERT["comparison"], key=lambda c: -c["cv_accuracy_mean"])
table([["Algorithm", "Features", "CV accuracy", "Hold-out accuracy"]] +
      [[c["model"], c["features"], f"{pct(c['cv_accuracy_mean'], 1)} ± {c['cv_accuracy_std'] * 100:.1f}", pct(c["holdout_accuracy"], 0)] for c in fc],
      [0.32, 0.2, 0.26, 0.22], "Fertiliser candidates")
body("**Logistic Regression on N, P, K** scored 100% in all 25 folds and was chosen. KNN dropped to 23% with all "
     "features: the extra columns carry no signal but still change the distances. With 99 rows, 100% means the "
     "grades are cleanly separable in this data, not that the model is perfect.")
h2("A5.3 The reasoning step: from soil reading to fertiliser")
body("The fertiliser data describes the **nutrient to supply**, while a soil test describes **what is already in "
     "the soil**. A rule-based step (knowledge-based reasoning) converts one into the other before the model is called:")
numbered([
    "Typical level for the crop: its median N, P, K in the crop dataset, or the Soil Health Card mid-band (N 420, P 17.5, K 195 kg/ha) for a lab test.",
    "Shortfall = (typical - actual) / typical for each nutrient; under 5% counts as zero.",
    "Nothing short: answer 'No fertiliser needed' without calling the model.",
    "Scale the shortfall vector so the largest sits at the top of the fertiliser dataset's range (N 42, P 42, K 19), keeping the ratios.",
    "Required nutrients: those with at least a quarter of the largest shortfall.",
    "Run the model and pick its highest-probability grade that supplies every required nutrient (the **supply filter**).",
])
ch = F["chain"]
table([["", "N", "P", "K"], ["Field (maize)", f"{ch['input']['N']:.0f}", ch["input"]["P"], ch["input"]["K"]],
       ["Maize typical", ch["typical"]["N"], ch["typical"]["P"], ch["typical"]["K"]],
       ["Shortfall", f"{ch['shortfall']['N'] * 100:.1f}%", "0%", f"{ch['shortfall']['K'] * 100:.0f}%"],
       ["Status", "short", "adequate", "short"]], [0.34, 0.22, 0.22, 0.22], "Worked example")
body(f"N and K are both required, so the answer must supply both: **{ch['fert']}**. Urea would be rejected because it "
     "contains no potassium. The app never gives a dose: doses must come from a soil test and the local Krishi Vigyan Kendra.")
figure(MY / "ai_chain.png", "The full decision chain: learned models joined by reasoning steps.")
h2("A5.4 Full auto analysis")
body("On both the dashboard and the app, **Full auto analysis** takes a random real soil sample from the crop "
     "dataset, runs the crop model, computes the shortfall against that crop's typical levels, runs the fertiliser "
     "model and opens the Fertiliser page with both results saved. A button then hands the result to the assistant.")
note("Remember", [
    "Classification (Logistic Regression, softmax) plus a rule layer: a hybrid of learned and knowledge-based AI.",
    "5x5 repeated CV because the dataset is tiny; feature selection by permutation importance.",
    "Supply filter guarantees the answer contains every short nutrient.",
])

# ---------------------------------------------------------------- A6 leaf
h1("A6. Model 4: Leaf-Disease Detection")
h2("A6.1 Data")
body(f"**Dataset:** 'Data for: Identification of Plant Leaf Diseases Using a 9-layer Deep CNN' (Mendeley, derived "
     f"from PlantVillage). **{lf['images']:,} original images** of single leaves, 256 x 256 pixels, in **{lf['classes']} "
     f"classes** (38 crop-disease pairs plus a 'no leaf' background class). Classes are imbalanced: the largest has "
     f"{lf['largest_n']:,} images and the smallest {lf['smallest_n']}.")
figure(FIGS / "leaf_samples.png", "Sample images: each folder name is the label.", width=12)
h2("A6.2 Training")
bullets([
    f"Stratified 70/15/15 split: {LEAF['split']['train']:,} train, {LEAF['split']['val']:,} validation, {LEAF['split']['test']:,} test.",
    f"The augmented set's synthetic images were used only for training; {LEAF['split']['synthetic_dropped_leak_guard']:,} were dropped "
    "because they were near-copies of validation or test images (**leak guard**).",
    "Images resized to 224 x 224 and normalised with ImageNet mean and standard deviation.",
    "EfficientNet-B0 from ImageNet weights; class-weighted cross-entropy (rare classes count more) with label smoothing 0.05.",
    "AdamW optimiser, learning rate 0.001 with a one-cycle schedule, batch 96, 8 epochs, mixed precision on an RTX 5070 Ti (about 214 s per epoch).",
    "Exported to **ONNX** so the server runs it on CPU with ONNX Runtime, no PyTorch needed in production.",
])
figure(FIGS / "leaf_history.png", "Training loss and validation accuracy per epoch.", width=13)
h2("A6.3 Calibration and refusing to guess")
body("Neural networks are often **over-confident**. **Temperature scaling** divides the network's scores by a "
     f"temperature T (fitted on validation data: T = {LEAF['temperature']}) before softmax. This cut the expected "
     f"calibration error from {LT['ece_before_T']} to {LT['ece_after_T']}. A **confidence threshold of 0.95** is then "
     "applied: below it the app says 'needs review' instead of naming a disease. At prediction time the image and "
     "its mirror image are both scored and averaged (**test-time augmentation**).")
table([["Measure", "Value"],
       ["Test accuracy", pct(LT["accuracy"])], ["Macro recall", pct(LT["macro_recall"])], ["Macro F1", f"{LT['macro_f1']}"],
       ["Photos answered (confidence >= 0.95)", pct(LT["answered_fraction"])],
       ["Accuracy on answered photos", pct(LT["accuracy_when_answered"])],
       ["ECE before / after temperature scaling", f"{LT['ece_before_T']} / {LT['ece_after_T']}"],
       ["Majority-class baseline", pct(lf["majority_share"])]], [0.6, 0.4], "Leaf model results on 8,318 test images")
body("Hardest classes: corn Cercospora leaf spot (recall 0.961) and corn northern leaf blight (0.973), which look "
     "alike. The test images are lab photos; accuracy on field photos with soil and shadows has not been measured.")
note("Remember", [
    "CNN + transfer learning (EfficientNet-B0 pretrained on ImageNet, fine-tuned on leaves).",
    "Class weights for imbalance, leak guard for synthetic copies, macro recall as the main metric.",
    "Temperature scaling for honest confidence; threshold 0.95 to refuse unclear photos.",
])

# ---------------------------------------------------------------- A7 assistant + external AI services
h1("A7. The AI Assistant and Other AI Services")
h2("A7.1 How the assistant answers")
numbered([
    "The farmer types a question, or taps 'Ask the assistant' on a fertiliser or disease result.",
    "The server builds a **context**: the farmer's farms (if they allowed sharing), their recent predictions and each model's measured accuracy.",
    "A **system prompt** sets the rules: use the context, never invent measurements, prices, schemes, doses or spray schedules, and say what each model really used.",
    "The last 12 messages and the context go to **Mistral** (ministral-14b, temperature 0.3, up to 900 tokens). If it is busy, a smaller fallback model answers.",
    "A **dose check** scans the reply for quantities such as kg/ha. If found, the model is asked to rewrite; if amounts remain they are removed and a note says why.",
    "If the reply is not in the chosen language, **Azure Translator** translates it. The conversation is saved and can be renamed, bookmarked or deleted.",
])
h2("A7.2 Other AI and data services")
table([["Service", "What it gives", "Where shown"],
       ["Open-Meteo", "Live weather, 7-day forecast, geocoding", "Overview, Weather page, app home"],
       ["NASA POWER", "Daily weather history (satellite and model based)", "Weather history charts"],
       ["ISRIC SoilGrids (WCS)", "Modelled soil properties at six depths", "Soil page"],
       ["Azure Translator", "Interface and answers in 14 Indian languages + English", "Language switch, assistant"],
       ["Mistral API", "Assistant answers", "AI Assistant page and app tab"]],
      [0.25, 0.43, 0.32], "External services")
body("Results from these services are cached in the database with an expiry time, so repeated views are fast and "
     "the app still works briefly if a service is slow. When a service fails the page says so instead of showing numbers.")

# ---------------------------------------------------------------- A8 ML tech stack + performance
h1("A8. AI and ML Tech Stack")
table([["Layer", "Tools", "Why"],
       ["Language", "Python 3.12", "Standard for data science and ML"],
       ["Data handling", "pandas, NumPy", "Loading, cleaning and feature building"],
       ["Classical ML", "scikit-learn", "Random Forest, Logistic Regression, KNN, SVM, CV, metrics"],
       ["Boosting", "LightGBM", "Fast gradient boosting with categorical features"],
       ["Deep learning", "PyTorch, torchvision", "EfficientNet-B0 training on the GPU (CUDA 12.8)"],
       ["Inference", "ONNX Runtime, joblib", "CPU serving of the CNN; saved sklearn models"],
       ["Charts", "Matplotlib", "Evaluation figures in the reports"],
       ["LLM", "Mistral API", "Assistant answers"],
       ["Hardware", "RTX 5070 Ti (training); 2 vCPU VPS (serving)", "GPU only needed to train"]],
      [0.2, 0.38, 0.42], "ML tech stack")
b = LOAD["bench"]
table([["Model", "Mean time per prediction (1 core)", "Predictions per second"],
       ["Crop (Random Forest)", f"{b['crop_recommendation']['mean_ms']} ms", b["crop_recommendation"]["per_second_one_core"]],
       ["Yield (LightGBM)", f"{b['yield_prediction']['mean_ms']} ms", b["yield_prediction"]["per_second_one_core"]],
       ["Fertiliser (Logistic Regression)", f"{b['fertiliser']['mean_ms']} ms", b["fertiliser"]["per_second_one_core"]],
       ["Leaf (EfficientNet-B0, ONNX)", f"{b['leaf_disease']['mean_ms']} ms", b["leaf_disease"]["per_second_one_core"]]],
      [0.4, 0.33, 0.27], "Measured model speed on the server")

h1("A9. Viva Questions: AI and ML")
qa([
    ("Why Random Forest for crops and not a single decision tree?",
     "A single tree overfits. A forest averages 400 trees trained on bootstrap samples, which lowers variance. It also had the best 5-fold CV accuracy of the five candidates (99.38%)."),
    ("Why is the crop accuracy so high? Is it overfitting?",
     "No: it is measured on 440 rows the model never saw. It is high because the dataset is clean, balanced and well separated. Real soil tests will be noisier, so real accuracy will be lower."),
    ("Why a temporal split for yield?",
     "Yield is time-series data. A random split would let the model learn a district's later years and be tested on earlier ones, which inflates the score. Testing on 2017-18 onwards copies real use: predicting the future."),
    ("Why does the yield model predict a ratio instead of the yield?",
     "Yields range from about 0.5 t/ha (pulses) to 70 t/ha (sugarcane). Learning the log ratio to the district's own recent yield puts all crops on one scale and lets one model serve all of them."),
    ("What baseline did the yield model beat?",
     f"Last year's yield (MAE {YR[LASTYR]['mae_t_ha']}), the 3-year mean ({YR[MEAN3]['mae_t_ha']}) and the national crop mean ({YR['Baseline: national crop mean']['mae_t_ha']}). The model's MAE is {YR['LightGBM (this model)']['mae_t_ha']} t/ha."),
    ("The fertiliser model is 100% accurate. Do you trust that?",
     "Only partly. 99 rows is very small; 100% shows the seven grades are cleanly separated by N, P and K in this data. The real uncertainty is in the reasoning step that converts a soil reading into a need, which the app states on every result."),
    ("What is transfer learning and why use it?",
     "Starting from a network already trained on ImageNet and fine-tuning it on our images. It needs less data and time, and generic edge and texture filters transfer well to leaves."),
    ("What is temperature scaling?",
     f"Dividing the network's output scores by a constant T before softmax so that confidence matches real accuracy. T = {LEAF['temperature']} reduced ECE from {LT['ece_before_T']} to {LT['ece_after_T']}."),
    ("Why does the leaf model sometimes refuse to answer?",
     "Below a calibrated confidence of 0.95 it returns 'needs review'. Wrongly naming a disease could make a farmer spray the wrong chemical, so refusing is safer."),
    ("How do you handle class imbalance in leaves?",
     "Class-weighted loss, a stratified split, synthetic images for small classes (training only) and macro recall as the headline metric."),
    ("How is the AI assistant prevented from giving doses?",
     "The system prompt forbids it, a server-side check scans every reply for quantities, asks for one rewrite, and strips any remaining amounts with a note."),
    ("Which part of the system is not machine learning?",
     "The shortfall bridge and supply filter are rule-based reasoning; weather and soil come from external services; the assistant is a pretrained LLM we only prompt."),
])

# ================================================================== PART B
part_divider("B", "Software Engineering",
             "Process, requirements, design, database, security, web dashboard, Android app, testing and deployment")

h1("B1. Process Model and Plan")
body("The project followed an **iterative (incremental) model**: requirements and a data study first, then working "
     "increments (models, API, dashboard, security, Android app), each reviewed and tested before the next. This "
     "suited a project where model accuracy was unknown at the start and features were added in stages.")
figure(UML / "gantt.png", "Project schedule (weeks).", width=15)
table([["Phase", "Output"],
       ["Requirements", "Project proposal, SRS with 32 functional and 15 non-functional requirements"],
       ["Design", "SDD: architecture, modules, ER diagram, sequence diagrams, wireframes"],
       ["Implementation", "Training scripts, FastAPI server, web dashboard, Android app"],
       ["Testing", "88 automated tests, load test"],
       ["Deployment", "Docker container on a VPS behind Traefik with HTTPS"]], [0.25, 0.75], "Phases and deliverables")

h1("B2. Requirements")
h2("B2.1 Users")
table([["User", "Needs"], ["Farmer (main user)", "Quick answers on crop, fertiliser and leaf health in an Indian language, on a phone"],
       ["Agricultural officer", "Check many farmers' cases and explain results"],
       ["Student / researcher", "See how each model was trained and how accurate it is"]], [0.3, 0.7], "User classes")
h2("B2.2 Functional requirements")
body(f"The SRS lists **{len(FR)} functional requirements**, grouped below. Each one is traced to test cases.")
groups = {}
for f in sorted(FR, key=lambda x: x[0]):
    groups.setdefault(f[1], []).append(f[0])
table([["Group", "Requirements", "Example"]] +
      [[g, ", ".join(ids), next(x[2] for x in FR if x[0] == ids[0])[:120] + ("..." if len(next(x[2] for x in FR if x[0] == ids[0])) > 120 else "")] for g, ids in groups.items()],
      [0.17, 0.25, 0.58], "Functional requirements by group", size=9, keep=False)
h2("B2.3 Non-functional requirements")
table([["ID", "Category", "Requirement"]] + [[n[0], n[1], n[2]] for n in sorted(NFR, key=lambda x: int(x[0][4:]))],
      [0.1, 0.17, 0.73], "Non-functional requirements", size=9, keep=False)
h2("B2.4 Use cases")
figure(UML / "usecase.png", "Use-case diagram.", width=13)
table([["ID", "Use case", "Main flow"]] + [[u[0], u[1], u[5]] for u in C.USE_CASES], [0.1, 0.2, 0.7],
      "Main use cases", size=9.5, keep=False)

h1("B3. System Design")
h2("B3.1 Architecture")
body("A **three-tier, client-server** design. The **presentation tier** is two clients: a single-page web "
     "dashboard (HTML, JavaScript, Tailwind CSS) and a native Android app (Kotlin, Jetpack Compose). The "
     "**application tier** is one **FastAPI** server that exposes a REST API, loads the ML models and calls "
     "external services. The **data tier** is a **SQLite** database plus model files. Both clients use the same "
     "API, so there is no second back end to maintain.")
figure(UML / "modules.png", "Server modules.", width=14)
table([["Module (file)", "Responsibility"],
       ["main.py", "FastAPI app: all REST endpoints, sessions, validation, overview, reports"],
       ["ml.py", "Loads and runs the crop, yield and leaf models; input validation; model cards"],
       ["fertiliser.py", "Shortfall reasoning, supply filter, fertiliser model"],
       ["assistant.py", "Prompt building, Mistral calls, fallback model, dose check"],
       ["otp.py", "One-time codes: create, hash, limit, verify, send through n8n"],
       ["db.py", "SQLite schema, scrypt passwords, session tokens, uploads, cache"],
       ["external.py", "Open-Meteo, NASA POWER, SoilGrids calls with caching"],
       ["translate.py", "Azure Translator with a database cache and rate limit"],
       ["disease_info.py", "Cause, symptoms and next steps for each disease"],
       ["static/", "Web dashboard: index.html, app.js, i18n.js, styles.css, vendored libraries"]],
      [0.25, 0.75], "Server modules")
h2("B3.2 Data flow")
figure(UML / "dfd0.png", "Context diagram (DFD level 0).", width=13)
figure(UML / "dfd1.png", "DFD level 1.", width=15)
h2("B3.3 REST API")
body("The API has about 55 endpoints. All data endpoints need a valid session; a user can only read or change "
     "their own records.")
table([["Area", "Endpoints"],
       ["Authentication", "POST /api/auth/register, /login, /otp/verify, /otp/resend, /forgot, /logout"],
       ["Profile", "GET/PUT /api/me, PUT /api/me/password, POST /api/me/delete, GET /api/me/activity"],
       ["Farms", "GET/POST /api/farms, GET/PUT/DELETE /api/farms/{id}"],
       ["Predictions", "POST /api/crop/recommend, /api/yield/predict, /api/fertiliser, /api/disease"],
       ["Options and samples", "GET /api/yield/options, /api/yield/districts, /api/samples/{crop|yield|fertiliser|leaf}"],
       ["Environment", "GET /api/weather, /api/weather/history, /api/soil, /api/geocode"],
       ["History and reports", "GET /api/predictions, /api/overview, /api/reports/csv, /api/reports/pdf"],
       ["Assistant", "POST /api/chat, GET/PATCH/DELETE /api/chats/{id}, POST /api/chat/translate"],
       ["System", "GET /api/status, /api/models/{name}, /healthz, /api/i18n/*"]], [0.25, 0.75], "Main API endpoints", size=9.5)
h2("B3.4 Sequence diagrams")
figure(UML / "seq_login.png", "Sign-in with password and e-mailed code.", width=15)
figure(UML / "seq_predict.png", "A prediction request.", width=15)
figure(UML / "seq_disease.png", "Leaf-photo diagnosis.", width=15)
figure(UML / "seq_chat.png", "Assistant conversation.", width=15)

h1("B4. Database Design")
body("SQLite, one file, nine tables. JSON text columns hold flexible data such as prediction inputs and chat "
     "messages. Deleting an account deletes the user's rows from every table.")
figure(UML / "er.png", "Entity-relationship diagram.", width=15)
table([["Table", "Key columns", "Purpose"],
       ["users", "id, name, email, phone, pw_hash, state, district, role, language", "Accounts and preferences"],
       ["sessions", "token_hash, user_id, expires", "Signed-in sessions (only a hash of the token is stored)"],
       ["farms", "id, user_id, name, district, lat, lon, area_ha, soil_type", "A user's fields"],
       ["predictions", "id, user_id, kind, inputs, result, confidence, model_version", "Every model result"],
       ["chats", "id, user_id, title, saved, messages", "Assistant conversations"],
       ["uploads", "id, user_id, prediction_id, sha256, data", "Leaf photos linked to their result"],
       ["otp_challenges", "id, email, purpose, code_hash, attempts, expires", "One-time codes"],
       ["auth_events", "user_id, event, ip, user_agent, created_at", "Audit log of sign-in steps"],
       ["cache / translations", "key, value, expires / lang, src, dst", "External data and translation cache"]],
      [0.2, 0.47, 0.33], "Database tables", size=9.5)

h1("B5. Security")
table([["Threat", "Protection in AgriSense"],
       ["Stolen database", "Passwords hashed with **scrypt** and a random 16-byte salt; session tokens and OTP codes stored only as SHA-256 hashes"],
       ["Password guessing", "Sign-in needs the password **and** a 6-digit code e-mailed each time (two-step)"],
       ["Code guessing", "Codes expire in 10 minutes, are single-use, allow 5 wrong tries, 60 s between resends, 6 sends per hour"],
       ["Account enumeration", "'Forgot password' gives the same reply whether or not the e-mail exists"],
       ["Session theft (web)", "Cookie is HttpOnly (no JavaScript access), SameSite=Lax, Secure, over HTTPS only"],
       ["Session theft (app)", "Bearer token kept in Android encrypted storage (security-crypto), never in plain files"],
       ["Reading others' data", "Every query is filtered by the signed-in user's id"],
       ["Leaked keys", "API keys live in a server-side file mounted read-only; never sent to the browser or committed"],
       ["Bad input", "Every field validated against allowed ranges; file type and size checked for uploads"]],
      [0.25, 0.75], "Security measures", size=10)
figure(UML / "otp_state.png", "Life cycle of a one-time code.", width=13)

h1("B6. Web Dashboard")
h2("B6.1 Front-end technology")
body("A **single-page application**: one index.html loads app.js, which draws each page without reloading. "
     "**Tailwind CSS** handles layout, **Chart.js** draws charts and **Leaflet** with OpenStreetMap shows farm maps. "
     "All libraries and fonts are served by the app itself, so the dashboard works even if a public CDN is blocked. "
     "i18n.js swaps the interface into 15 languages, and a light and dark theme switch without reloading.")
figure(UML / "sitemap.png", "Site map of the dashboard.", width=14)
h2("B6.2 Pages")
table([["Page", "What it does"],
       ["Sign in / Sign up", "Password, then a 6-digit code from e-mail; sign-up verifies the e-mail before the account exists"],
       ["Overview", "Greeting, live weather, counts of predictions, recent results, insights, production analytics"],
       ["Crop Recommendation", "Custom input or auto-fill from the dataset; best crop, alternatives, suitability radar"],
       ["Yield Prediction", "State, district, crop, season, year, area; yield, 80% range, contributions, district history"],
       ["Fertiliser", "Three input bases, Full auto analysis, suggested fertiliser, nutrient need, model's top 3"],
       ["Plant Disease Detection", "Upload or sample photo; disease, confidence, cause, symptoms, next steps"],
       ["AI Assistant", "Chat in 15 languages using the farmer's data; saved, renamed and bookmarked chats"],
       ["Weather / Soil", "Forecast and history charts; SoilGrids properties at six depths"],
       ["Farms", "Add and edit farms with a map; coordinates outside India are refused"],
       ["History / Reports", "Every prediction with inputs and model version; PDF and CSV downloads"],
       ["Settings", "Profile, password, language, units, theme, delete account"]], [0.27, 0.73], "Dashboard pages", size=10)
figure(FIGS / "shot_03_crop.png", "Crop Recommendation page.", width=15)
figure(FIGS / "shot_05_fertiliser.png", "Fertiliser page after the full analysis.", width=15)
figure(FIGS / "shot_04_yield.png", "Yield Prediction page with contributions.", width=15)

h1("B7. Android App")
h2("B7.1 Technology")
table([["Part", "Choice"],
       ["Language and UI", "Kotlin 2.4, **Jetpack Compose** with Material 3 (declarative UI, no XML layouts)"],
       ["Android versions", "minSdk 26 (Android 8.0) to targetSdk 36"],
       ["Networking", "OkHttp with kotlinx.serialization JSON, coroutines for background calls"],
       ["Sign-in storage", "AndroidX security-crypto: the bearer token is kept in encrypted preferences"],
       ["Navigation", "Navigation Compose with a bottom bar: Home, Predict, Scan, AI Assistant, Farms"],
       ["Images and maps", "Coil for images, osmdroid (OpenStreetMap) for farm maps"],
       ["Server", "The same FastAPI server as the web; the API base URL is set in gradle.properties"]], [0.27, 0.73], "Android tech stack")
h2("B7.2 Code structure")
table([["File", "Role"],
       ["MainActivity.kt, AgriApp.kt", "Entry point, app set-up, map user agent"],
       ["data/Api.kt, data/Session.kt", "REST client and encrypted token storage"],
       ["ui/AppRoot.kt, ui/AppState.kt", "Navigation graph, shared state, 3-second welcome screen gate"],
       ["ui/Welcome.kt", "Welcome screen with progress bar"],
       ["ui/auth, home, predict, scan, assistant, farms, more", "One package per screen group"],
       ["ui/theme/Theme.kt, i18n/Tr.kt", "Light and dark colours, translated labels"]], [0.4, 0.6], "Android source layout")
body("Signing in on the app uses the same e-mail code. The server sees the app's header and returns the session "
     "token in the response instead of setting a cookie; the app then sends it as **Authorization: Bearer <token>**. "
     "Both clients therefore share one session table and one set of rules.")
figure_row([AND / "welcome.png", AND / "home.png", AND / "fertiliser.png", AND / "scan.png"],
           "Android app: welcome screen, home, fertiliser result, leaf scan.", 8.5)
figure_row([AND / "assistant.png", AND / "farm.png", AND / "hindi.png", AND / "dark.png"],
           "Android app: assistant, farm, Hindi interface, dark theme.", 8.5)

h1("B8. Testing")
h2("B8.1 Automated tests")
body("**88 automated tests** written with **pytest**, all passing. Each test case has an ID (TC-001 to TC-088) "
     "and is traced to the requirements it proves.")
table([["Test file", "Tests", "What it covers"],
       ["test_auth.py", "21", "Sign-up, sign-in, codes, limits, password reset, sessions, account deletion"],
       ["test_features.py", "36", "Farms, predictions, fertiliser reasoning, samples, history, reports, assistant rules"],
       ["test_models.py", "13", "Model cards, accuracy targets, input validation, leaf threshold"],
       ["test_ui.py", "18", "Browser tests in Microsoft Edge: pages, language switch, theme, phone width"]],
      [0.22, 0.1, 0.68], "Test suites")
table([["Technique", "Example"],
       ["Black-box (functional)", "Register with a valid code and land on the Overview page"],
       ["Boundary value", "pH 3 and 10 accepted, 2.9 refused; resend exactly at 60 s"],
       ["Negative testing", "Wrong code, expired code, sixth attempt, other user's farm id"],
       ["Integration", "Full auto analysis: crop model, then fertiliser model, both saved"],
       ["UI / end-to-end", "Edge browser driven by the tests, including 375 px phone width"],
       ["Performance / load", "Simulated users against a copy of the server"]], [0.3, 0.7], "Testing techniques used")
h2("B8.2 Load test")
st = {s["users"]: s for s in LOAD["step"]}
table([["Users at once", "Requests/s", "Median (ms)", "95th percentile (ms)", "Errors"]] +
      [[u, st[u]["rps"], st[u]["p50_ms"], st[u]["p95_ms"], st[u]["errors"]] for u in sorted(st)],
      [0.2, 0.2, 0.2, 0.24, 0.16], "Load test on a copy of the server (2 vCPU, 8 GB RAM)")
body(f"Up to **{LOAD['capacity_users_p95_under_2s']} users at once**, 95% of answers came back within 2 seconds "
     "with no errors. Beyond that the two CPU cores are full: throughput stays near 60 to 68 requests per second and "
     "waiting grows, still without errors. The test ran on a throwaway copy, never on the live database.")
figure(FIGS / "load_step.png", "Response time and throughput as users increase.", width=14)

h1("B9. Deployment")
body("The server is packaged as a **Docker** image (python:3.12-slim, runs as a non-root user, 2 Uvicorn "
     "workers, port 8150). Docker Compose restarts it automatically, limits it to 1.2 GB of memory, stores the "
     "database in a named volume and mounts the key file read-only. **Traefik** in front of it provides HTTPS "
     "with Let's Encrypt certificates. E-mail codes are sent through an **n8n** workflow on the same server.")
figure(UML / "deployment.png", "Deployment diagram.", width=15)

h1("B10. Full Tech Stack")
table([["Layer", "Technology"],
       ["Web front end", "HTML, JavaScript (single-page app), Tailwind CSS 3.4, Chart.js 4.4, Leaflet + OpenStreetMap"],
       ["Mobile front end", "Kotlin, Jetpack Compose, Material 3, OkHttp, kotlinx.serialization, Coil, osmdroid"],
       ["Back end", "Python 3.12, FastAPI, Uvicorn"],
       ["Database", "SQLite"],
       ["ML and AI", "scikit-learn, LightGBM, PyTorch, ONNX Runtime, Mistral API"],
       ["External data", "Open-Meteo, NASA POWER, ISRIC SoilGrids, Azure Translator"],
       ["Security", "scrypt, SHA-256, e-mail one-time codes, HttpOnly cookies, bearer tokens, HTTPS"],
       ["Testing", "pytest, Edge browser automation, custom load generator"],
       ["DevOps", "Docker, Docker Compose, Traefik, n8n, Linux VPS"],
       ["Tools", "VS Code, Android Studio, Microsoft Word"]], [0.22, 0.78], "Complete tech stack")

h1("B11. Viva Questions: Software Engineering")
qa([
    ("Which process model did you follow and why?",
     "An iterative, incremental model. Model accuracy and data quality were unknown at the start, so we built and tested working increments (models, API, dashboard, security, app) and refined each one."),
    ("What is the difference between a functional and a non-functional requirement? Give one of each.",
     "Functional: what the system does, for example FR-17, identify the disease from a leaf photo. Non-functional: how well it does it, for example NFR-07, a prediction returns in under 2 s."),
    ("Why one API for both the web and the app?",
     "One place for business rules, validation and security; no duplicated back end; a fix on the server reaches both clients at once."),
    ("How does the web keep a user signed in, and how does the app?",
     "The web uses an HttpOnly, SameSite cookie. The app gets the same session token in the response and sends it as a bearer token, stored in encrypted preferences. The server stores only a SHA-256 hash of the token."),
    ("Why scrypt for passwords?",
     "scrypt is slow and memory-hard on purpose, so guessing passwords from a stolen database is very expensive. Each password has its own random salt, so identical passwords give different hashes."),
    ("Why SQLite and not MySQL?",
     "One server, moderate load, no separate database service to run. The load test showed the CPU, not the database, is the limit at about 100 users. Moving to PostgreSQL is listed as future work."),
    ("What testing techniques did you use?",
     "Black-box functional tests, boundary-value tests, negative tests, integration tests of the full analysis, UI tests in Edge, and a load test. 88 tests, all passing, each traced to requirements."),
    ("What is traceability?",
     "Linking each requirement to the design element that implements it and the test cases that prove it, so nothing is built or tested without a reason."),
    ("How is the app deployed?",
     "As a Docker container on a Linux VPS, restarted automatically, behind Traefik for HTTPS, with the database in a volume and keys mounted read-only."),
    ("What happens if Mistral or a weather service is down?",
     "The assistant tries a smaller fallback model; weather and soil pages say the service is unavailable instead of showing numbers. Cached values are used while they are fresh."),
    ("What does Jetpack Compose give you over XML layouts?",
     "UI is written as Kotlin functions that redraw when state changes, so there is less code, no findViewById, and theme and language switches are simple."),
])

h1("Glossary")
table([["Term", "Meaning"],
       ["API / REST", "A set of web addresses the clients call to send and get data, using HTTP methods (GET, POST, PUT, DELETE)"],
       ["Baseline", "A simple method a model must beat to be worth using"],
       ["Bearer token", "A secret string sent in the Authorization header to prove who is calling"],
       ["Calibration", "Confidence that matches real accuracy"],
       ["CNN", "Convolutional neural network, a network for images"],
       ["Cross-validation", "Training and scoring several times on different splits and averaging"],
       ["Docker", "A tool that packages an app with everything it needs so it runs the same anywhere"],
       ["LLM", "Large language model, such as Mistral, that generates text"],
       ["Model card", "A JSON file with a model's data, settings and measured results"],
       ["ONNX", "A standard file format for trained neural networks, runnable without the training library"],
       ["OTP", "One-time password: a short code sent by e-mail that works once"],
       ["SHAP", "A method that splits a prediction into per-feature contributions"],
       ["SPA", "Single-page application: the web page changes without full reloads"],
       ["Transfer learning", "Reusing a model trained on one task as the start for another"]], [0.24, 0.76], "Glossary", size=10)

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print("wrote", OUT, FIG[0], "figures", TAB[0], "tables")
