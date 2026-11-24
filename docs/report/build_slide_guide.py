"""Slide-by-slide guide to the AI and ML final-evaluation deck: for every slide, what is on it, what to say,
the ideas behind it and likely questions. Slide pictures come from out/slides/sNN.png (rendered from the deck).
Usage: python build_slide_guide.py <out.docx>"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import content as C  # noqa: E402

OUT = Path(sys.argv[1])
SL = HERE / "out" / "slides"
F = json.loads((HERE / "out" / "aiml_facts.json").read_text(encoding="utf-8"))
M = ROOT / "app" / "models"
CROP = json.loads((M / "crop_model.json").read_text())
YLD = json.loads((M / "yield_model.json").read_text())
FERT = json.loads((M / "fertiliser_model.json").read_text())
LEAF = json.loads((M / "leaf_disease.json").read_text())
LOAD = json.loads((ROOT / "tests" / "load" / "results" / "summary.json").read_text())
YR, LT, FC = YLD["results"], LEAF["test"], FERT["chosen"]
LG = YR["LightGBM (this model)"]
LY = YR["Baseline: last year's yield"]
M3 = YR["Baseline: mean of previous 3 years"]
cr, fe, yi, lf, ch = F["crop"], F["fert"], F["yield"], F["leaf"], F["chain"]
B = LOAD["bench"]

INK, TEAL, GREY = RGBColor(0x14, 0x2A, 0x4C), RGBColor(0x00, 0x7A, 0x7E), RGBColor(0x60, 0x68, 0x70)
FONT = "Times New Roman"


def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


doc = Document()
st = doc.styles["Normal"]
st.font.name = FONT; st.font.size = Pt(11.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.line_spacing = 1.1
for name, size, color in (("Heading 1", 17, INK), ("Heading 2", 12.5, TEAL)):
    h = doc.styles[name]
    h.font.name = FONT; h.font.size = Pt(size); h.font.bold = True; h.font.color.rgb = color
    rf = h.element.rPr.rFonts
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), FONT)
    h.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = sec.bottom_margin = Cm(1.9)
WIDTH = 21.0 - 4.4


def runs(p, text, size=None, bold=False, italic=False, color=None):
    for i, part in enumerate(text.split("**")):
        if part:
            r = p.add_run(part); r.bold = bold or i % 2 == 1; r.italic = italic
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


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), fill)
    tcPr.append(sh)


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


def say_box(text):
    t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0); shade(c, "EAF4F4"); c.width = Cm(WIDTH)
    p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(2)
    runs(p, "What to say", 10.5, bold=True, color=TEAL)
    for chunk in text.split("\n"):
        q = c.add_paragraph(); q.paragraph_format.space_after = Pt(3); q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        runs(q, chunk, 11, italic=True)
    para(after=2)


def slide(n, title, shows, say, explain, asks=(), img_w=13.0):
    h = doc.add_heading(f"Slide {n}: {title}", 1)
    h.paragraph_format.page_break_before = True
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
    p.add_run().add_picture(str(SL / f"s{n:02d}.png"), width=Cm(img_w))
    doc.add_heading("What is on the slide", 2)
    para(shows, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    say_box(say)
    doc.add_heading("Explained", 2)
    for e in explain:
        q = para(style="List Bullet", after=2, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        runs(q, e)
    if asks:
        doc.add_heading("If the examiner asks", 2)
        for qq, aa in asks:
            q = para(after=0); q.paragraph_format.keep_with_next = True
            runs(q, "Q. " + qq, bold=True)
            q = para(after=5, align=WD_ALIGN_PARAGRAPH.JUSTIFY); q.paragraph_format.left_indent = Cm(0.6)
            runs(q, aa)


# ================================================================== cover + intro
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
p.add_run().add_picture(str(HERE / "niit_logo.png"), width=Cm(10.5))
para("PRESENTATION GUIDE", 14, True, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL, after=6)
para("AgriSense AI", 28, True, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=2)
para("AI and ML Final Evaluation: every slide explained", 16, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=22)
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=22)
p.add_run().add_picture(str(SL / "s01.png"), width=Cm(14))
for n, e in C.TEAM:
    para(f"{n}  ({e})", 12, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
para(f"Artificial Intelligence (CS 322), Dr. Shweta R Malwe  |  B.Tech CSE Semester V, Section {C.SECTION}, Session {C.YEAR}",
     11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)

s2 = doc.add_section(WD_SECTION.NEW_PAGE)
s2.footer.is_linked_to_previous = False
fp = s2.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
field(fp, "PAGE")
doc.add_heading("How to use this guide", 1)
para("Each of the 25 slides of AgriSense_AI_ML_Final_Evaluation_v2.pptx has its own page here, in the same order. "
     "Every page gives a picture of the slide, a plain description of what is on it, a short script to say "
     "(the shaded box), the ideas behind the slide explained simply, and the questions an examiner is likely to "
     "ask with short answers. Read the script aloud a few times; do not read it off the page during the talk.",
     align=WD_ALIGN_PARAGRAPH.JUSTIFY)
doc.add_heading("Timing and sharing the talk", 2)
para("At about 40 to 50 seconds per slide the talk takes 18 to 20 minutes. One possible split between the three of "
     "you (change it to match who built what):", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
t = doc.add_table(rows=4, cols=3); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
rows = [["Speaker", "Slides", "Topic"],
        [C.TEAM[0][0], "1 to 9", "Problem, objectives, workflow, datasets, algorithms, reasoning step, architecture"],
        [C.TEAM[1][0], "10 to 16", "Experimental setup and the results of all four models"],
        [C.TEAM[2][0], "17 to 25", "Load test, discussion, the web and Android apps, conclusion, future scope"]]
for i, r in enumerate(rows):
    for j, v in enumerate(r):
        c = t.cell(i, j); c.width = Cm([3.6, 2.4, 10.6][j])
        runs(c.paragraphs[0], v, 10.5, bold=(i == 0), color=RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else None)
        c.paragraphs[0].paragraph_format.space_after = Pt(0)
        if i == 0:
            shade(c, "142A4C")
para(after=4)
doc.add_heading("Five numbers to know by heart", 2)
for x in [f"Crop model: **{pct(CROP['test_accuracy'])}** accuracy on 440 unseen rows (majority baseline {pct(cr['majority_share'])}).",
          f"Yield model: **R² {LG['r2']}**, MAE **{LG['mae_t_ha']} t/ha** on unseen years (last year's yield: {LY['mae_t_ha']}).",
          f"Fertiliser model: **{pct(FC['cv_accuracy_mean'], 0)}** in 5x5 repeated cross-validation on {fe['rows']} rows.",
          f"Leaf model: **{pct(LT['accuracy'])}** accuracy, **{pct(LT['accuracy_when_answered'])}** on photos it answers.",
          f"Server: **{LOAD['capacity_users_p95_under_2s']} users at once** with 95% of answers under 2 seconds, 0 errors."]:
    runs(para(style="List Bullet", after=2), x)

# ================================================================== slides
slide(1, "Title slide",
      "The evaluation heading, the project name AgriSense AI with a one-line description, the three presenters with "
      "enrollment numbers, programme, course, session and faculty, the NIIT University logo and the app's welcome screen.",
      "Good morning. We are " + ", ".join(n for n, _ in C.TEAM) + ". Our project is AgriSense AI, a smart farming assistant. "
      "It uses machine learning to help a farmer decide which crop to grow, how much it will yield, which fertiliser "
      "the soil needs, and whether a leaf is diseased. It runs as a web dashboard and an Android app, and both are live.",
      ["The phone screenshot is the real Android app's 3-second welcome screen.",
       "Keep this slide short: names, one-sentence summary, move on."],
      [("Is the system actually deployed?", f"Yes, at https://ai.software.microeagle.online, and the Android app uses the same server.")])

slide(2, "Problem Statement",
      "Four problems farmers face, an 'AI question' box that states the problem as one question, and a screenshot of "
      "the dashboard's overview page.",
      "A Soil Health Card gives a farmer N, P and K values, but it does not tell them which crop suits the field or "
      "which fertiliser to buy. Leaf diseases are usually noticed only after they spread. Weather, soil and yield data "
      "are spread across different websites, mostly in English.\nSo our AI question is: given soil, climate, location "
      "and a leaf photo, what should the farmer grow, how much will it yield, which fertiliser is needed, and is the leaf sick?",
      ["**N, P, K** are nitrogen, phosphorus and potassium, the three main plant nutrients.",
       "**Soil Health Card** is a Government of India scheme that gives farmers a soil test report.",
       "Writing the problem as one question shows the examiner you framed it as an **AI task** before choosing any algorithm."],
      [("Why is this an AI problem and not just a lookup table?",
        "The right crop or fertiliser depends on combinations of many values (seven soil and climate inputs for crops). "
        "Learning those patterns from thousands of labelled examples is what supervised machine learning does well.")])

slide(3, "Project Objectives",
      "Five numbered objectives: framing the problem as AI tasks, the data and features, the algorithms, evaluation "
      "and comparison, and a usable system.",
      "Our first objective was to turn each farmer question into an AI task: crop and fertiliser choice are "
      "classification, yield is regression, leaf diagnosis is image classification. Second, we used four public "
      "datasets. Third, we chose each algorithm by comparing several candidates with cross-validation. Fourth, every "
      "model is tested on unseen data against a simple baseline. Fifth, all models are served to a web dashboard and "
      "an Android app, with an assistant that explains results in 15 languages.",
      ["**Classification** predicts a category (which crop). **Regression** predicts a number (tonnes per hectare).",
       "**Cross-validation** trains and scores a model several times on different splits of the training data, then averages.",
       "A **baseline** is a trivial method, such as always guessing the most common class, that a real model must beat.",
       "Objectives say what we aim to achieve, not the steps; the sample deck's note asked for exactly this."],
      [("Why compare several algorithms instead of using one?",
        "No algorithm is best for every dataset. Comparing them with cross-validation on the training data lets the data pick the model, and the test set stays untouched for the final, honest score.")])

slide(4, "Workflow Diagram",
      "Ten boxes in a snake shape: problem definition, data collection, preprocessing, EDA, feature selection, "
      "train-test split, model training, model evaluation, deployment and prediction. Training and evaluation are dark "
      "because they repeat for each model.",
      "This is our complete workflow. We defined the four questions, collected data from Kaggle, data.gov.in and "
      "Mendeley, cleaned it, explored it, selected features using importance scores, and split it into training and "
      "test sets. Steps 6 to 8 run once per model. Finally the models are deployed behind an API and give predictions, "
      "which the AI assistant can explain.",
      ["**EDA (exploratory data analysis):** looking at class balance, value ranges and distributions before modelling.",
       "**Feature selection:** we kept only useful inputs. For fertiliser, five of eight columns had zero importance and were dropped.",
       "**Leak guard:** making sure near-identical images never appear in both training and test sets, which would inflate accuracy.",
       "Every metric is written to a JSON **model card**, so the app, report and slides always show the same numbers."],
      [("What is a model card?",
        "A JSON file written by the training script with the dataset, split, settings and every measured result. The app and our report read numbers from it instead of typing them by hand.")])

slide(5, "Workflow: AI Decision Chain",
      "A diagram of how the AI parts connect: soil sample, crop model, shortfall check, fertiliser model, result. "
      "Below it: the rule check, the supply filter, the assistant, and the separate leaf-photo model. Two boxes "
      "explain which parts are learned and which are reasoned.",
      "This slide shows how the intelligence fits together. A soil sample goes into the crop model, which picks a crop. "
      "We then compare the soil's N, P and K with what that crop normally needs. If nothing is short, the rule check "
      "says no fertiliser is needed. Otherwise the fertiliser model ranks fertilisers, and the supply filter only "
      "accepts one that supplies every short nutrient. The leaf model works separately on photos. So the system "
      "combines **learned** models with **rule-based reasoning**.",
      ["**Hybrid AI:** machine learning for patterns in data plus explicit rules for knowledge we already have (a fertiliser must contain the missing nutrient).",
       "The assistant is drawn with a dashed arrow because it is used only when the farmer asks for an explanation.",
       "The leaf model's 0.95 threshold means it refuses to name a disease when unsure."],
      [("Why not train one model from soil values straight to fertiliser?",
        "No dataset links soil tests to the fertiliser actually needed. The fertiliser data describes the nutrient to supply, not the soil. The reasoning step bridges the two, and we say on every result that this bridge is an approximation.")])

slide(6, "Methodology: Datasets",
      "A table of the four datasets with source, size, features, target and split; each dataset name is a clickable "
      "link. Below: the preprocessing steps and sample leaf images.",
      f"We used four datasets. Crop: {cr['rows']:,} rows with seven soil and climate features and 22 crops. Yield: "
      f"{yi['clean_rows']:,} cleaned government records of district crop production. Fertiliser: {fe['rows']} records "
      f"with seven fertiliser classes. Leaf: {lf['images']:,} leaf images in {lf['classes']} classes. For yield we kept "
      "only crops measured in tonnes, removed impossible values and merged duplicates. For leaves we resized images "
      "and removed synthetic copies that matched test images.",
      [f"Yield cleaning reduced {yi['raw_rows']:,} raw rows to {yi['clean_rows']:,}; the raw file had yields as high as 43,958 t/ha, which are data-entry errors.",
       "**Stratified split:** each class keeps the same share in training and test data.",
       "**Temporal split** (yield): train on earlier years, test on later years, like predicting the future.",
       "**70/15/15** for leaves: 70% training, 15% validation (to tune), 15% test (final score).",
       "**GODL** is the Government Open Data License - India; **CC BY 4.0** allows reuse with credit."],
      [("Why did the fertiliser model use only 3 of 8 features?",
        "Permutation importance of temperature, humidity, moisture, soil type and crop type was exactly zero, and every algorithm scored higher without them. Extra columns with no signal only add noise."),
       ("Where did the datasets come from?", "Kaggle (crop, yield copy, fertiliser), data.gov.in (original yield data) and Mendeley Data (leaf images). Links are on slide 24.")])

slide(7, "Methodology: Algorithms and Why",
      "Four cards, one per model, each listing the candidates compared and the reason for the choice. Below: the "
      "training and testing strategy.",
      "For crops we compared five classifiers and Random Forest had the best cross-validated accuracy. For yield we "
      "used LightGBM because it handles more than 700 districts as categories and trains on three lakh rows in "
      "minutes. For fertiliser, Logistic Regression was the simplest model that scored 100% in cross-validation. For "
      "leaves we used EfficientNet-B0 with transfer learning; it is small enough to run on a CPU and is calibrated so "
      "it refuses to guess below 0.95 confidence. In every case the test data stays unseen until the final score.",
      ["**Random Forest:** 400 decision trees, each trained on a random sample of rows; they vote. This reduces overfitting.",
       "**LightGBM:** gradient boosting, where each new tree corrects the errors of the previous ones. L1 loss means it minimises absolute error.",
       "**Logistic Regression:** a linear classifier that turns scores into probabilities with softmax.",
       "**EfficientNet-B0 and transfer learning:** a CNN pretrained on ImageNet, then fine-tuned on leaf photos. About 5.3 million parameters.",
       "**ONNX:** an exported model format, so the server runs the CNN without PyTorch.",
       "Refitting on all data after testing gives the deployed model more data; the reported numbers stay from the test run."],
      [("Why not use deep learning for the crop data too?",
        "It is small tabular data (2,200 rows, 7 numbers). Tree ensembles usually match or beat neural networks there, train in seconds and are easier to explain. Random Forest already reached 99.55%."),
       ("What does early stopping do?", "It stops adding trees when the validation error stops improving (iteration 975 for yield), which prevents overfitting.")])

slide(8, "Methodology: From Soil Reading to Fertiliser",
      "Six numbered steps of the reasoning that turns a soil reading into a fertiliser need, and a worked example for "
      "maize with a table of soil values, typical values, shortfall and status.",
      f"This is our reasoning step. First we take the chosen crop's typical N, P and K. Then we compute how short the "
      f"soil is for each nutrient. If nothing is short, we stop and say no fertiliser is needed. Otherwise we scale the "
      f"shortfall to the fertiliser data's range, mark which nutrients are required, and pick the best-ranked fertiliser "
      f"that supplies all of them. In this maize example nitrogen is {ch['shortfall']['N'] * 100:.1f}% short and potassium "
      f"{ch['shortfall']['K'] * 100:.0f}% short, so the answer must contain both: {ch['fert']}. Urea is rejected because "
      "it has no potassium.",
      ["**Shortfall** = (typical - actual) / typical. Under 5% counts as zero.",
       "**Typical level:** the crop's median in the crop dataset, or the middle of the Soil Health Card band for a lab test.",
       "**One-quarter rule:** a nutrient is required if its shortfall is at least a quarter of the largest shortfall.",
       "**Supply filter:** a rule that overrides the model's first choice if that fertiliser lacks a required nutrient.",
       "The app never gives a dose; doses must come from a soil test and the local Krishi Vigyan Kendra."],
      [("Is this part machine learning?",
        "No, it is rule-based (knowledge-based) reasoning. It prepares the input for the fertiliser model and checks its output. That is why we call the system a hybrid."),
       ("Why 17-17-17 and not DAP here?", "DAP (18-46-0) has no potassium, and potassium is short, so the supply filter rejects it. 17-17-17 supplies N, P and K.")])

slide(9, "System Architecture and Tech Stack",
      "The architecture diagram (clients, Traefik, FastAPI container, models, database and external services) and "
      "eight tech-stack cards from machine learning to deployment.",
      "Both the web dashboard and the Android app call one FastAPI server. The server loads the models once per worker "
      "and runs the leaf CNN through ONNX Runtime on the CPU. It fetches live weather and soil data from outside "
      "services and stores every result per user in SQLite. On the ML side we used scikit-learn, LightGBM, PyTorch "
      "and ONNX Runtime; the assistant uses the Mistral API.",
      ["**FastAPI:** a Python web framework for REST APIs.",
       "**Traefik:** a reverse proxy that provides HTTPS in front of the app.",
       "**Docker:** packages the app with its libraries so it runs the same everywhere.",
       "**Open-Meteo / NASA POWER:** weather forecast and history. **SoilGrids:** modelled soil maps.",
       "**Jetpack Compose:** Android's modern UI toolkit, written in Kotlin."],
      [("Why one server for both clients?", "One place for models, rules and security. A fix or a retrained model reaches the web and the app at the same time.")])

slide(10, "Experimental Setup",
      "A table, following the sample deck's guidelines, with hardware, software, language, libraries, dataset "
      "configuration, algorithm configuration and evaluation metrics.",
      "We trained on a Windows 11 PC with an NVIDIA RTX 5070 Ti GPU, which was needed only for the leaf CNN. The "
      "server is a VPS with two virtual CPUs and 8 GB of RAM. Everything is in Python 3.12. The table lists each "
      "dataset's size and split, the main hyperparameters of each algorithm, and the metrics: accuracy and F1 for "
      "classification, MAE and R² for yield, calibration error for the leaf model, and latency for the server.",
      ["**Hyperparameters** are settings chosen before training, for example 400 trees, learning rate 0.05, batch size 96.",
       "**Seed 42** fixes the random choices so results can be reproduced.",
       "**AdamW** is the optimiser that updates the CNN's weights; **label smoothing 0.05** stops it becoming over-confident.",
       "**Mixed precision** uses 16-bit numbers on the GPU to train faster (about 214 seconds per epoch)."],
      [("Do you need a GPU to run the app?", "No. The GPU was only used to train the leaf model. The deployed server runs all models on CPU.")])

slide(11, "Results & Discussions",
      "A summary table of each model's primary metric, baseline and result, three key points, and a chart comparing "
      "each classifier's accuracy with its majority-class baseline.",
      f"Here is the summary. The crop model reached {pct(CROP['test_accuracy'])} against a {pct(cr['majority_share'])} baseline. "
      f"The yield model's error is {LG['mae_t_ha']} tonnes per hectare, lower than last year's yield as a guess. The "
      f"fertiliser model scored {pct(FC['cv_accuracy_mean'], 0)} in cross-validation and the leaf model {pct(LT['accuracy'])}. "
      "All are far above their baselines.",
      ["**Majority baseline:** accuracy of always guessing the most common class. For crops it is 1 in 22.",
       "Yield has no accuracy because it is regression; it is compared on MAE instead.",
       f"The leaf model answers {pct(LT['answered_fraction'], 1)} of photos; the rest are marked 'needs review'."],
      [("Why is the baseline important?", "A high number alone means nothing. 90% accuracy is poor if guessing the common class already gives 90%. The baseline shows how much the model really learned.")])

slide(12, "Results: Crop Recommendation",
      "A chart of cross-validation and test accuracy for the five classifiers, three findings, and the crop "
      "confusion matrix.",
      f"Five classifiers were compared. Random Forest had the best cross-validated accuracy and reached "
      f"{pct(CROP['test_accuracy'])} on the 440 test rows, with a macro F1 of {CROP['test_macro_f1']}. Only two rows were "
      "wrong: a blackgram predicted as maize and a rice predicted as jute, which grow in similar conditions. We note "
      "that the dataset is very clean, so real soil tests will score lower.",
      ["**Confusion matrix:** rows are true crops, columns are predicted crops; everything on the diagonal is correct.",
       "**Macro F1:** the F1 score averaged equally over all 22 crops, so a rare crop counts as much as a common one.",
       "The most important inputs by permutation importance were humidity, nitrogen and rainfall."],
      [("Is 99.55% overfitting?", "No. Overfitting shows as high training accuracy but low test accuracy. This is measured on 440 rows never used in training or model selection."),
       ("Why did KNN do worst?", "KNN depends on distances, and features with different scales and relevance (rainfall in hundreds, pH below 10) distort them.")])

slide(13, "Results: Yield Prediction",
      "Two charts comparing MAE and R² of the model with three baselines, a per-crop table for the most common "
      "crops, and three notes.",
      f"We tested the yield model on {YLD['rows_test']:,} rows from 2017-18 onwards, years it never saw. Its MAE is "
      f"{LG['mae_t_ha']} t/ha and R² {LG['r2']}, better than last year's yield ({LY['mae_t_ha']}) and the 3-year mean "
      f"({M3['mae_t_ha']}). Last year's yield is a strong baseline because district yields change slowly, so our gain "
      "comes mostly from the years with big changes. Within one crop the R² is lower, between 0.34 and 0.74. The "
      "data has no rainfall or soil inputs, so the model cannot foresee a drought.",
      ["**MAE:** mean absolute error, the average size of the mistake in tonnes per hectare.",
       "**R²:** the share of variation in yield that the model explains; 1 is perfect, 0 is no better than the average.",
       "**Lag features:** the district's own past yields (last year, 3-year mean, trend), which carry most of the signal.",
       "**SHAP contributions:** for each prediction, how much each input pushed the yield up or down; shown on the dashboard."],
      [("Why is overall R² high but per-crop R² low?", "The overall figure benefits from big differences between crops (sugarcane versus pulses). Within one crop the differences are smaller and harder to predict."),
       ("Why not a random split?", "It would let the model learn from a district's future years, giving a falsely high score.")])

slide(14, "Results: Fertiliser Recommendation",
      "A horizontal chart of the eight candidates' cross-validation accuracy (teal = N, P, K only), the chosen model, "
      "and three findings.",
      f"We compared four algorithms, each on N, P and K only and on all eight features, using five-fold "
      f"cross-validation repeated five times. Every algorithm did better on N, P and K alone. KNN fell to 23% with all "
      f"features. Logistic Regression made no mistake in 25 folds and was chosen. With only {fe['rows']} rows, this means "
      "the seven fertilisers are cleanly separated by N, P and K in this data, not that the model is perfect.",
      ["**Repeated cross-validation (5x5):** 5-fold CV run 5 times with different shuffles, giving 25 scores; steadier on small data.",
       "**Error bars** on the chart show the spread across the 25 folds.",
       "This slide is a good example of **feature selection** improving every model."],
      [("Isn't 100% suspicious?", "On 99 rows it is plausible: each grade has a distinct N, P, K pattern (Urea is high N with zero P and K). We say clearly that the figure has wide uncertainty.")])

slide(15, "Results: Leaf-Disease Detection",
      "Four stat cards (test accuracy, macro recall, calibration error before and after, accuracy when it answers), the "
      "training curves, the four hardest classes and three notes.",
      f"On {LEAF['split']['test']:,} test images the model reached {pct(LT['accuracy'])} accuracy and {pct(LT['macro_recall'])} "
      f"macro recall. We used temperature scaling so the confidence is honest: calibration error fell from "
      f"{LT['ece_before_T']} to {LT['ece_after_T']}. Below 0.95 confidence the app does not name a disease. The hardest "
      "classes are corn leaf spot and northern leaf blight, which look alike. These are lab photos, so field photos "
      "will score lower.",
      ["**Macro recall:** the share of each class found, averaged over classes; important because classes are imbalanced (152 to 5,507 images).",
       f"**Temperature scaling:** dividing the network's scores by T = {LEAF['temperature']} before softmax so that 90% confidence means about 90% correct.",
       "**ECE (expected calibration error):** the average gap between stated confidence and real accuracy.",
       "**Training curves:** loss falls and validation accuracy rises over 8 epochs without a gap, so no overfitting."],
      [("Why refuse to answer sometimes?", "A wrong disease name could lead a farmer to spray the wrong chemical. Asking for a clearer photo or expert review is safer."),
       ("How did you handle class imbalance?", "Class-weighted loss, stratified split, synthetic images for small classes in training only, and macro recall as the main metric.")])

slide(16, "Results: Sample Outputs",
      "A table of real outputs from the deployed models: crop, fertiliser, leaf and yield inputs with the dataset's "
      "label or a reference and the system's output.",
      "These are real outputs from the running system. The crop, fertiliser and leaf rows show the right answer from "
      "the dataset next to the model's answer. The two yield rows predict 2021-22, one year after the data ends, so "
      "there is no true value yet; we show the district's average for comparison, with an 80% range.",
      ["The **80% range** for yield comes from the spread of the model's errors on the test years for that crop.",
       "These rows show the pipeline working end to end; the accuracy figures are on the earlier result slides."],
      [("Can you show it live?", "Yes, on the dashboard: choose Auto-fill from dataset on any tool; it picks a real record and shows the dataset's label beside the model's answer.")])

slide(17, "Results: Load and Capacity Test",
      "A line chart of median and 95th-percentile response time as simultaneous users grow, a throughput bar chart, and "
      "four stat cards.",
      f"We load-tested a copy of the server with simulated users. Up to {LOAD['capacity_users_p95_under_2s']} users at "
      f"once, 95% of answers came back within 2 seconds, at about {LOAD['capacity_rps_at_that_point']:.0f} requests per "
      "second. Beyond that the two CPU cores are full: throughput stays flat and waiting time grows, but there were no "
      f"errors in 32,061 requests. A leaf prediction takes about {B['leaf_disease']['mean_ms']:.0f} ms on one core.",
      ["**95th percentile (p95):** 95% of requests were faster than this time; it shows what slower users experience.",
       "**Throughput:** requests handled per second. It plateaus when the CPU is the limit.",
       "The test used a throwaway copy of the container, never the live database."],
      [("How would you support more users?", "Add CPU cores and server workers, or run more containers behind the proxy, and move from SQLite to PostgreSQL.")])

slide(18, "Result & Discussions Contd'",
      "Three cards (result interpretation, model comparison, discussion of findings, numbered 4 to 6 as in the sample "
      "deck) and a strip naming the best model for each task.",
      "To interpret the results: crop and leaf accuracies are near 100% because both datasets are clean. Comparing "
      "models, tree ensembles win on tabular data, a linear model is enough for fertiliser once only N, P and K are "
      "used, and the pretrained CNN works best for images. Our main findings: useless features hurt distance-based "
      "models most, past yields explain most of the yield, and for a farmer, honest confidence matters more than raw accuracy.",
      ["This slide answers the sample deck's points 4 to 6: interpret, compare, and explain why a model did better.",
       "Best models: Random Forest (crop), LightGBM (yield), Logistic Regression (fertiliser), EfficientNet-B0 (leaf)."],
      [("What was the most surprising result?", "KNN on the fertiliser data: 99% with N, P, K but 23% with all features. It shows clearly why feature selection matters.")])

slide(19, "Application: Web Dashboard (1/2)",
      "Screenshots of the Crop Recommendation page and the Fertiliser page after the full analysis.",
      "This is the web dashboard. On the left, the crop page shows the recommended crop, the alternatives and a radar "
      "chart of how well each input fits. On the right, Full auto analysis has taken a real soil sample, run the crop "
      "model and then the fertiliser model, and shows the suggested fertiliser with the nutrient need and the model's top three.",
      ["**Full auto analysis** is the AI chain from slide 5 running in one click.",
       "Every result is saved to the user's history with the model version."],
      [("Is the dashboard tied to a user account?", "Yes. Sign-in needs a password and a code sent by e-mail, and each user sees only their own data.")])

slide(20, "Application: Web Dashboard (2/2)",
      "Screenshots of the Yield Prediction page with feature contributions and the Weather page with live and historical data.",
      "The yield page shows the predicted yield with its range, and bars showing how much each input pushed the "
      "prediction up or down. The weather page shows the live forecast and daily history for the farm, which the "
      "farmer and the assistant can use alongside the models.",
      ["The contribution bars are the SHAP-style explanation from LightGBM: **explainable AI**.",
       "Weather comes from Open-Meteo and NASA POWER; the app says so when a service is unavailable instead of inventing numbers."],
      [])

slide(21, "Application: Android App",
      "Five phone screenshots: home, full auto analysis, fertiliser result, leaf scan and the AI assistant.",
      "This is the Android app, built in Kotlin with Jetpack Compose. It uses the same server as the website. From home "
      "the farmer can run the full analysis, see the fertiliser result, scan a leaf with the camera, and ask the AI "
      "assistant, which explains the result in their language and never gives doses.",
      ["The app signs in with the same e-mail code and keeps the session token in encrypted storage.",
       "The assistant answer shown explains a 20-20 fertiliser suggestion using the farmer's own result."],
      [("Does the app run the models on the phone?", "No. It sends inputs or the photo to the server, which runs the models, so all users get the same, latest models.")])

slide(22, "Conclusion",
      "Four headline numbers and four concluding points, including the main limitations.",
      "To conclude: we framed four farm decisions as AI tasks and joined two models with a reasoning step. Each "
      "algorithm was chosen by cross-validation and beat a baseline on unseen data. The system is live on the web and "
      "Android and handles about 100 users at once. Our main limits are clean lab-style datasets, no weather input for "
      "yield, only 99 fertiliser rows, and no field-photo test for the leaf model.",
      ["Stating limitations yourself shows you understand the results; examiners value this."],
      [("What would you do with more time?", "Collect field photos and real soil-test-plus-fertiliser records, and add weather to the yield model. See the next slide.")])

slide(23, "Future Scope",
      "Five numbered improvements.",
      "Next, we would add weather and soil inputs to the yield model, collect field photos from farmers to test and "
      "improve the leaf model outside the lab, replace the fertiliser bridge with real soil-test and fertiliser data, "
      "add an offline mode and Hindi voice input to the app, and move to PostgreSQL with more workers as usage grows.",
      ["Each item answers one limitation from the conclusion slide."],
      [])

slide(24, "References and Dataset Links",
      "Clickable links for the four datasets and six research papers.",
      "These are our data sources and the papers behind our methods: Random Forests by Breiman, LightGBM, EfficientNet, "
      "the calibration paper by Guo and others, the nine-layer CNN paper that published the leaf dataset, and PlantVillage.",
      ["**Guo et al. 2017** introduced temperature scaling, used for the leaf model.",
       "**Tan and Le 2019** introduced EfficientNet.",
       "**Geetharamani and Arun Pandian 2019** published the leaf image dataset we used."],
      [])

slide(25, "Thank You",
      "Thank you, the live link, the team and the course.",
      "Thank you. The system is live at the link shown, and we are happy to demonstrate it or answer questions.",
      ["Keep the dashboard open in a browser tab so you can demonstrate quickly if asked."],
      [])

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print("wrote", OUT)
