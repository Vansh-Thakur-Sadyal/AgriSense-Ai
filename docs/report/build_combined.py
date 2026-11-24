"""Build the single combined project report (DOCX) in the order of the course guideline:
cover -> contents -> 1 proposal -> 2 SRS -> 3 SDD -> 4 wireframes -> 5 implementation -> 6 testing (incl. load test)
-> 7 assumptions, limitations, future work -> 8 references.

Numbers come from the model cards, docs/submission/spec.py, tests/results.xml (via assemble.catalogue) and the
load-test summary. Run:  .venv/Scripts/python docs/report/build_combined.py <load results dir>
"""
import json
import sys
import time
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "docs" / "submission"))
sys.path.insert(0, str(ROOT / "docs"))
import assemble  # noqa: E402
import build_report as R  # noqa: E402
from spec import FR, NFR  # noqa: E402
import content as C  # noqa: E402

LOAD = json.loads((Path(sys.argv[1]) / "summary.json").read_text())
OUT = ROOT / "Project" / "AgriSense_AI_Project_Report.docx"
FIGS, SUB, SHOTS, WF = ROOT / "docs" / "figs", ROOT / "docs" / "submission" / "figs", ROOT / "docs" / "screens", ROOT / "docs" / "submission" / "wf"
AND = FIGS / "android"
INK = RGBColor(0x1F, 0x38, 0x64)
FONT = "Times New Roman"

doc = Document()
st = doc.styles
st["Normal"].font.name = FONT
st["Normal"].font.size = Pt(12)
st["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st["Normal"].paragraph_format.space_after = Pt(6)
st["Normal"].paragraph_format.line_spacing = 1.15
for name, size, before in (("Heading 1", 16, 18), ("Heading 2", 13, 12), ("Heading 3", 12, 8)):
    s = st[name]
    s.font.name, s.font.size, s.font.bold, s.font.color.rgb = FONT, Pt(size), True, INK
    s._element.rPr.rFonts.set(qn("w:asciiTheme"), "") if False else None
    rf = s._element.rPr.find(qn("w:rFonts"))
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(a), None)
    rf.set(qn("w:ascii"), FONT); rf.set(qn("w:hAnsi"), FONT)
    s.paragraph_format.space_before, s.paragraph_format.space_after = Pt(before), Pt(6)
    s.paragraph_format.keep_with_next = True

sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Cm(2.54))
WIDTH = 21.0 - 2 * 2.54

FIG_N, TAB_N = [0], [0]


# ---------------------------------------------------------------- helpers
def para(text="", bold=False, italic=False, size=None, align=None, after=None, style=None, color=None):
    p = doc.add_paragraph(style=style)
    if text:
        add_runs(p, text, bold, italic, size, color)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def add_runs(p, text, bold=False, italic=False, size=None, color=None):
    """**bold** spans inside text are rendered bold."""
    for i, chunk in enumerate(text.split("**")):
        if not chunk:
            continue
        r = p.add_run(chunk)
        r.bold = bold or i % 2 == 1
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    return p


def body(text):
    p = para(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def h(text, level):
    return doc.add_heading(text, level)


def bullets(items):
    for t in items:
        p = doc.add_paragraph(style="List Bullet")
        add_runs(p, t)
        p.paragraph_format.space_after = Pt(3)


def numbered(items):
    for t in items:
        p = doc.add_paragraph(style="List Number")
        add_runs(p, t)
        p.paragraph_format.space_after = Pt(3)


def shade(cell, hexfill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexfill)
    tcPr.append(sh)


def caption(kind, text):
    if kind == "Figure":
        FIG_N[0] += 1; n = FIG_N[0]
    else:
        TAB_N[0] += 1; n = TAB_N[0]
    p = para(f"{kind} {n}: {text}", italic=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
    if kind == "Table":
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(4)
    return p


def table(rows, widths, title=None, size=10, header=True):
    if title:
        caption("Table", title)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tot = sum(widths)
    for i, row in enumerate(rows):
        tr = t.rows[i]
        if header and i == 0:
            trPr = tr._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
        cant = OxmlElement("w:cantSplit"); tr._tr.get_or_add_trPr().append(cant)
        for j, val in enumerate(row):
            c = tr.cells[j]
            c.width = Cm(WIDTH * widths[j] / tot)
            c.paragraphs[0].text = ""
            add_runs(c.paragraphs[0], str(val), bold=header and i == 0, size=size)
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
            c.paragraphs[0].paragraph_format.line_spacing = 1.0
            if header and i == 0:
                shade(c, "D9E2F3")
    para(after=4)
    return t


def figure(path, text, width=WIDTH, max_h=19.0):
    path = Path(path)
    w, hgt = Image.open(path).size
    width_cm = min(width, max_h * w / hgt)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    caption("Figure", text)


def figure_row(paths, text, height=11.0):
    """Several phone screenshots side by side in a borderless table, one caption."""
    t = doc.add_table(rows=1, cols=len(paths))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, (pth, label) in enumerate(paths):
        c = t.rows[0].cells[j]
        p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        w, hh = Image.open(pth).size
        wcm = min(WIDTH / len(paths) - 0.4, height * w / hh)
        p.add_run().add_picture(str(pth), width=Cm(wcm))
        q = c.add_paragraph(); q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_runs(q, label, size=9)
    caption("Figure", text)


def code(text):
    for line in text.strip("\n").split("\n"):
        p = doc.add_paragraph()
        r = p.add_run(line if line else " ")
        r.font.name = "Consolas"; r.font.size = Pt(8.5)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        pf = p.paragraph_format
        pf.space_after = Pt(0); pf.line_spacing = 1.0
        pPr = p._p.get_or_add_pPr(); sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "F2F2F2"); pPr.append(sh)
    para(after=4)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def field(p, instr):
    r = p.add_run()
    a = OxmlElement("w:fldChar"); a.set(qn("w:fldCharType"), "begin"); r._r.append(a)
    i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = instr; r._r.append(i)
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "separate"); r._r.append(b)
    r2 = p.add_run("Right-click and choose Update Field to show the contents.")
    c = OxmlElement("w:fldChar"); c.set(qn("w:fldCharType"), "end"); p.add_run()._r.append(c)


pct = lambda x: f"{x * 100:.1f}%"
crop, yld, leaf, fert = R.crop, R.yld, R.leaf, R.fert
YR = yld["results"]["LightGBM (this model)"]
LT = leaf["test"]
cases = assemble.catalogue()
res, stamp, total_time = assemble.results()
passed = sum(1 for c in cases if res.get(c["func"], ("",))[0] == "Pass")
RUN_DATE = time.strftime("%d %B %Y", time.strptime(stamp[:10], "%Y-%m-%d")) if stamp else ""
req_of = {}
for fid, *_r, tests in FR:
    for tc in tests:
        req_of.setdefault(tc, []).append(fid)
for nid, _c, _t, tests in NFR:
    for tc in tests:
        req_of.setdefault(tc, []).append(nid)

# ================================================================ cover (own section, no page number)
logo = HERE / "niit_logo.png"
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run().add_picture(str(logo), width=Cm(13.5))
for t, sz, after in (("B. Tech. CSE Semester V", 16, 2), (f"L-T-P-C: {C.LTPC}", 16, 2), (f"Session: {C.YEAR}", 16, 30),
                     (f"{C.COURSE} ({C.COURSE_CODE})", 17, 2), ("PROJECT REPORT", 17, 14), (C.TITLE, 15, 26)):
    para(t, bold=True, size=sz, align=WD_ALIGN_PARAGRAPH.CENTER, after=after)
for name, enr in C.TEAM:
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
    r = p.add_run(f"Name: {name}    Enrollment No.: {enr}"); r.bold = True; r.font.size = Pt(14)
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=40)
r = p.add_run(f"Section: {C.SECTION}"); r.bold = True; r.font.size = Pt(14); r.font.highlight_color = WD_COLOR_INDEX.YELLOW
grey = RGBColor(0x80, 0x80, 0x80)
t = doc.add_table(rows=1, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
l, rcell = t.rows[0].cells
add_runs(l.paragraphs[0], f"Submitted To: {C.FACULTY}", size=13, color=grey)
add_runs(rcell.paragraphs[0], "Submitted By:", size=13, color=grey)
for name, enr in C.TEAM:
    q = rcell.add_paragraph(); add_runs(q, f"{name} ({enr})", size=13, color=grey); q.paragraph_format.space_after = Pt(0)

# body section with page numbers
new = doc.add_section(WD_SECTION.NEW_PAGE)
new.footer.is_linked_to_previous = False
fp = new.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
field(fp, "PAGE")
pg = new._sectPr.find(qn("w:pgNumType"))
if pg is None:
    pg = OxmlElement("w:pgNumType"); new._sectPr.append(pg)
pg.set(qn("w:start"), "1")
doc.sections[0].footer.is_linked_to_previous = False

para("Contents", bold=True, size=16, color=INK, after=8)
field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
page_break()

# ================================================================ 1. proposal
h("1. Problem Definition and Project Proposal", 1)
h("1.1 Problem", 2)
body("A small farmer in India usually decides what to sow and which fertiliser to buy from habit or from the "
     "advice of the shop that sells it. Soil Health Cards give N, P and K values, but most farmers cannot turn those "
     "numbers into a decision. Leaf diseases are often noticed only after they spread, and weather, soil and market "
     "information sit on different websites, mostly in English.")
body("AgriSense AI brings these decisions into one place. A farmer signs in, adds a farm on a map and gets a crop "
     "suggestion, a yield estimate, a fertiliser suggestion and a leaf-disease check, plus live weather and soil data "
     "for that farm. Every answer comes from a trained model or a named public data source, and every result is saved "
     "so it can be looked at again or discussed with an AI assistant in the farmer's own language.")
h("1.2 Users", 2)
table([["User", "Need"],
       ["Farmer (main user)", "Quick answers on crop, fertiliser and leaf health; Hindi or another Indian language; works on a phone"],
       ["Agricultural officer", "Check many farmers' cases and explain results"],
       ["Student / researcher", "See how each model was trained and how accurate it is"]], [0.3, 0.7], "Target users")
h("1.3 Objectives", 2)
numbered(["Train a crop-recommendation model on soil nutrients and climate, choosing the algorithm by cross-validation.",
          "Train a district-level yield model that beats simple baselines on years it has never seen.",
          "Train a leaf-disease classifier on a GPU and make it refuse unclear photos instead of guessing.",
          "Train a fertiliser model and connect it to the farmer's soil values, so every analysis ends with a named fertiliser (never a dose).",
          "Show live weather, forecasts, weather history and modelled soil data for each farm.",
          "Provide an AI assistant that answers in 15 languages using the farmer's own data.",
          "Secure accounts with e-mail codes, store every result, and offer both a web dashboard and an Android app on one API.",
          "Test the system (functional, model, live-service, UI and load tests) and deploy it over HTTPS."])
h("1.4 Scope", 2)
table([["In scope", "Out of scope"],
       ["Web dashboard and Android app using the same server API", "iOS app, offline mode, SMS or voice channels"],
       ["Crop, yield, fertiliser and leaf-disease tools", "Fertiliser and pesticide doses or spray schedules"],
       ["Weather, soil, assistant, history, PDF/CSV reports", "Market prices and government schemes (no reliable data)"],
       ["Accounts with e-mail verification, profile and account deletion", "Field-level yield (the public data is per district)"],
       ["English and 14 Indian languages, light and dark themes", "In-app administrator panel"]], [0.5, 0.5], "Project scope")
h("1.5 Technology", 2)
table([["Part", "Technology", "Reason"],
       ["Server", "Python 3.12, FastAPI, SQLite", "ML libraries are Python-first; SQLite needs no administration"],
       ["Models", "scikit-learn, LightGBM, PyTorch to ONNX", "Trained on our GPU, served on the server's CPU"],
       ["Web client", "HTML, JavaScript, Tailwind CSS, Chart.js, Leaflet", "Small and fast on phones, no build step"],
       ["Android app", "Kotlin, Jetpack Compose, OkHttp, osmdroid", "Native app that reuses the server API"],
       ["Services", "Mistral (assistant), Azure Translator, Open-Meteo, NASA POWER, ISRIC SoilGrids, n8n (e-mail)", "Free or already available to us"],
       ["Hosting", "Docker on a Linux VPS behind Traefik with Let's Encrypt", "One command deploy, HTTPS"]],
      [0.17, 0.43, 0.40], "Technology choices")
body(f"The system is live at **{R.URL if hasattr(R, 'URL') else 'https://ai.software.microeagle.online'}**.")
page_break()

# ================================================================ 2. SRS
h("2. Software Requirements Specification (SRS)", 1)
h("2.1 Introduction", 2)
body("This section states what AgriSense AI must do. Each requirement has an ID that is traced to the design "
     "(Section 3) and to the test cases (Section 6). Priority High means the release is not usable without it, "
     "Medium means it is expected, and Low means it is useful but optional.")
table([["Term", "Meaning"], ["OTP", "One-time 6-digit code sent by e-mail to confirm the user"],
       ["N, P, K", "Nitrogen, phosphorus and potassium in the soil"], ["t/ha", "Tonnes per hectare"],
       ["Kharif / Rabi", "Monsoon (June-October) and winter (November-April) seasons"],
       ["KVK", "Krishi Vigyan Kendra, the district farm science centre"],
       ["Model card", "JSON file written by a training script with the data split and measured accuracy"],
       ["p95", "95th percentile: 95% of requests were at least this fast"]], [0.22, 0.78], "Definitions")
h("2.2 Overall Description", 2)
body("AgriSense AI is a new, self-contained system. It depends on outside services for e-mail, weather, soil maps, "
     "translation and the assistant. Figure 1 shows the system and everything it talks to.")
figure(SUB / "dfd0.png", "Context diagram (data-flow diagram, level 0)")
table([["User class", "Characteristics", "Access"],
       ["Farmer", "Basic phone skills; may prefer an Indian language", "All features on own data"],
       ["Agricultural officer", "Trained; looks at many cases", "Same as farmer; role saved on the profile"],
       ["Researcher", "Interested in metrics", "Same, plus model details in the interface"],
       ["Administrator", "Developer who runs the server", "Server access only (deploy, keys, backups)"]],
      [0.22, 0.45, 0.33], "User classes")
body("**Constraints.** Only the supplied datasets and free public services may be used. The yield dataset has no "
     "weather or soil columns, so the yield model cannot use them. Secrets stay on the server. The assistant must never "
     "state a chemical dose.")
h("2.3 Functional Requirements", 2)
table([["ID", "Requirement", "Priority", "Acceptance criteria"]] +
      [[f, t, pr, C.ACCEPT[f]] for f, _a, t, pr, _ts in sorted(FR, key=lambda x: x[0])],
      [0.08, 0.45, 0.11, 0.36], "Functional requirements", size=9)
FR_TAB = TAB_N[0]
h("2.4 Non-Functional Requirements", 2)
table([["ID", "Category", "Requirement"]] + [[i, c, t] for i, c, t, _ in sorted(NFR, key=lambda x: x[0])],
      [0.1, 0.15, 0.75], "Non-functional requirements", size=9)
h("2.5 External Interfaces", 2)
table([["Type", "Interface", "Details"],
       ["User", "Web dashboard", "Sidebar with 12 pages, top bar with search, language and theme; works from 360 px wide"],
       ["User", "Android app", "Bottom bar (Home, Predict, Scan, AI Assistant, Farms); camera and gallery for leaf photos"],
       ["Software", "AgriSense REST API /api/*", "JSON over HTTPS; cookie session for the web, bearer token for the app"],
       ["Software", "n8n webhook", "POST with a shared secret header; sends the OTP e-mail"],
       ["Software", "Mistral chat, Azure Translator", "HTTPS JSON with server-side keys"],
       ["Software", "Open-Meteo, NASA POWER, SoilGrids WCS", "HTTPS; responses cached in the database"],
       ["Hardware", "None special", "Phone camera for leaf photos; GPS for 'use my location'"],
       ["Communication", "HTTPS (TLS 1.2+)", "Traefik terminates TLS; the server reaches n8n on a private Docker network"]],
      [0.15, 0.3, 0.55], "External interfaces")
h("2.6 Use Cases", 2)
figure(SUB / "usecase.png", "Use-case diagram")
for uid, name, actor, goal, pre, flow, alt, post in C.USE_CASES:
    table([["Field", f"{uid}: {name}"], ["Actor", actor], ["Goal", goal], ["Precondition", pre], ["Main flow", flow],
           ["Alternate flow", alt], ["Postcondition", post]], [0.22, 0.78], f"Use case {uid}, {name}", size=9.5)
h("2.7 Data Requirements", 2)
table([["Entity", "Main attributes", "Validation"],
       ["User", "name, e-mail, phone, role, state, district, language, password hash", "e-mail format, unique; password 8+ chars with a letter and a digit"],
       ["Farm", "name, state, district, village, lat/lon, area, soil type, irrigation", "name required; location inside India"],
       ["Prediction", "kind, inputs, result, summary, confidence, model version, status", "inputs checked per tool (below)"],
       ["Upload", "leaf photo, SHA-256, size, linked prediction or chat", "JPG or PNG, up to 8 MB"],
       ["Chat", "title, messages, bookmarked", "-"],
       ["OTP challenge", "purpose, hashed code, attempts, expiry", "6 digits, 10 min, 5 tries, 60 s between sends"],
       ["Auth event", "event, IP address, browser, time", "-"]], [0.15, 0.48, 0.37], "Data entities")
table([["Input", "Rule"], ["Crop inputs", "Each of the 7 values must lie in the range seen in training (shown as a placeholder)"],
       ["Yield", "State, district, crop and season required; year 1998 to next year; area above 0"],
       ["Fertiliser", "N, P, K from 0 to 2000; pH 3 to 10; organic carbon 0 to 10%"],
       ["Farm", "Latitude 6-38 N, longitude 68-98 E"]], [0.2, 0.8], "Input validation rules")
h("2.8 Acceptance Criteria", 2)
body(f"A functional requirement is complete when the condition in Table {FR_TAB} is observed and all test cases traced to it "
     "pass. The models also have measured targets, set before the final evaluation:")
table([["Model", "Target", "Measured"],
       ["Crop recommendation", "Test accuracy at least 97%", pct(crop["test_accuracy"])],
       ["Yield prediction", "Lower error than last-year and 3-year-mean baselines on unseen years", f"MAE {YR['mae_t_ha']} t/ha, R² {YR['r2']}"],
       ["Leaf disease", "Accuracy at least 98%, calibration error below 0.02", f"{pct(LT['accuracy'])}, ECE {LT['ece_after_T']}"],
       ["Fertiliser", "Cross-validated accuracy at least 95%", pct(fert["chosen"]["cv_accuracy_mean"])],
       ["Server (NFR-07)", "95% of requests under 2 s at normal load", f"Met up to {LOAD['capacity_users_p95_under_2s']} simultaneous users"]],
      [0.25, 0.5, 0.25], "Model and performance acceptance criteria")
page_break()

# ================================================================ 3. SDD
h("3. Software Design Document (SDD)", 1)
h("3.1 System Architecture", 2)
body("The system follows the layered structure the guideline suggests, with two presentation clients on one API. "
     "The web dashboard and the Android app hold no business rules: both call the same REST API, so a change on the "
     "server reaches both at once.")
table([["Layer", "Responsibility", "Implemented by"],
       ["Presentation", "Accept input, show results, translate the interface", "Web SPA (app/static), Android app (Kotlin, Compose)"],
       ["API / service", "Routes, validation, sessions, business rules", "app/main.py (FastAPI), otp.py, fertiliser.py, assistant.py"],
       ["Model (ML)", "Load trained models and run predictions", "app/ml.py, app/models/*"],
       ["Repository", "Store and read data", "app/db.py (SQLite)"],
       ["Integration", "Weather, soil, e-mail, translation, chat", "app/external.py, translate.py, n8n workflow"]],
      [0.17, 0.4, 0.43], "Layers of the architecture")
figure(FIGS / "architecture.png", "Component architecture")
h("3.2 Module and Component Design", 2)
figure(SUB / "modules.png", "Server modules and their dependencies", width=14)
table([["Module", "Responsibility"],
       ["main.py", "HTTP routes, validation, sessions, reports, chat orchestration"],
       ["db.py", "Schema, password hashing, sessions, audit log, uploads"],
       ["otp.py", "Create, send (through n8n), resend and verify one-time codes"],
       ["ml.py", "Crop, yield and leaf-disease inference; input limits; SHAP"],
       ["fertiliser.py", "Shortfall step and the fertiliser model"],
       ["external.py", "Open-Meteo, NASA POWER and SoilGrids clients with caching"],
       ["assistant.py", "Mistral chat with the user's context, language and dose checks"],
       ["translate.py", "Azure Translator with a database cache and a daily budget"]], [0.25, 0.75], "Server modules")
h("3.3 Class Design", 2)
body("The server is written in Python, where most units are modules of functions rather than classes; they are listed "
     "in the guideline's class format. The Android client is object-oriented Kotlin.")
table([["Class / module", "Key attributes", "Key methods"],
       ["db (repository)", "connection, schema", "hash_pw, new_session, log_event, save_upload, one, rows, run"],
       ["otp (service)", "TTL, MAX_ATTEMPTS, RESEND_GAP", "start, resend, verify, deliver"],
       ["ml (model service)", "crop, yield and leaf models, LIMITS", "validate, recommend_crop, predict_yield, diagnose"],
       ["fertiliser (service)", "fertiliser model, grades, MIN_SHORTFALL", "recommend, predict, supplies"],
       ["assistant (service)", "model list, system prompt", "reply, has_dose"],
       ["Session (Kotlin)", "token, language, theme (encrypted storage)", "init, signIn, signOut"],
       ["Api (Kotlin)", "OkHttp client, base URL", "get, post, put, delete, multipart"],
       ["AppState (Kotlin)", "user, farms, chain, pendingAsk", "loadFarms, meta, signOut"],
       ["Tr (Kotlin)", "language, cached translations", "use, t"]], [0.25, 0.35, 0.4], "Main classes and modules")
h("3.4 Data Model", 2)
figure(SUB / "er.png", "Entity-relationship diagram", width=14)
body("SQLite stores twelve tables. Passwords are scrypt hashes; session tokens and OTP codes are stored only as SHA-256 "
     "hashes. The production table holds 322,669 cleaned district records used by the yield model and the charts.")
h("3.5 Interface Design", 2)
table([["Method", "Path", "Purpose"],
       ["POST", "/api/auth/register, /login, /otp/verify, /forgot", "Accounts and e-mail codes"],
       ["GET / PUT / DELETE", "/api/me", "Profile and account deletion"],
       ["GET / POST / PUT / DELETE", "/api/farms", "Farms"],
       ["POST", "/api/crop/recommend", "Crop model"],
       ["POST", "/api/yield/predict", "Yield model"],
       ["POST", "/api/fertiliser", "Shortfall step and fertiliser model"],
       ["POST", "/api/disease", "Leaf photo (multipart)"],
       ["POST", "/api/chat", "Assistant"],
       ["GET", "/api/weather, /api/soil", "Live data for a farm"],
       ["GET", "/api/samples/crop|yield|leaf|fertiliser", "Random real dataset records"],
       ["GET", "/api/predictions, /api/reports/pdf|csv", "History and exports"],
       ["GET", "/api/meta/options, /api/i18n/*", "Option lists and translations shared by both clients"]],
      [0.2, 0.4, 0.4], "Main API endpoints")
figure(SUB / "sitemap.png", "Navigation map of the web dashboard", width=14)
NAV_FIG = FIG_N[0]
h("3.6 Sequence and Activity Flows", 2)
figure(SUB / "seq_signup.png", "Sign-up with an e-mail code")
figure(SUB / "seq_disease.png", "Leaf disease detection")
figure(SUB / "ml_pipeline.png", "From training to serving")
h("3.7 Error Handling and Validation", 2)
bullets(["Every error returns JSON with a message and, where relevant, the field it belongs to; both clients show it under that field.",
         "Model inputs are checked against the range seen in training, so the models never get values they cannot handle.",
         "If an outside service fails, the page says so and offers Retry instead of showing stale or invented numbers.",
         "The leaf model refuses to name a disease below its confidence threshold and marks the result for review.",
         "Any assistant reply that contains an application amount is rewritten once, and remaining amounts are removed."])
h("3.8 Security Design", 2)
table([["Threat", "Control"],
       ["Password theft from the database", "scrypt with a per-user salt"],
       ["Stolen password", "Second factor: an e-mailed code at every sign-in"],
       ["Code guessing or e-mail flooding", "5 tries per code, 10-minute expiry, 60 s between sends, 6 codes per hour"],
       ["Session theft", "Random 32-byte token stored as SHA-256; HttpOnly, SameSite=Lax, Secure cookie; HTTPS only"],
       ["Account discovery", "Forgot password answers the same way for unknown e-mails"],
       ["Reading another user's data", "Every query filtered by the signed-in user's id"],
       ["Malicious upload", "Type and size checks; image decoded only, never executed"],
       ["Leaked keys", "Keys in a read-only file on the server, never sent to a client"]], [0.35, 0.65], "Threats and controls")
h("3.9 Technology Stack", 2)
body("Python 3.12, FastAPI and Uvicorn (2 workers) on the server; scikit-learn, LightGBM and ONNX Runtime for the models; "
     "SQLite for storage; plain JavaScript with Tailwind CSS, Chart.js and Leaflet for the web; Kotlin with Jetpack "
     "Compose, OkHttp and osmdroid for Android; Docker, Traefik and Let's Encrypt for hosting; pytest and Playwright for tests.")
h("3.10 Deployment", 2)
figure(SUB / "deployment.png", "Deployment diagram")
body("The server runs as one Docker container (non-root user, 1.2 GB memory limit, health check every 30 s) on a "
     "2-vCPU VPS. Traefik routes HTTPS traffic to it. User data lives in a Docker volume, so a new release replaces the "
     "code without touching the data.")
h("3.11 Traceability Matrix", 2)
table([["Req. ID", "Design element", "Implementation", "Test cases"]] +
      [[f, C.TRACE[f][0], C.TRACE[f][1], ", ".join(ts)] for f, _a, _t, _p, ts in sorted(FR, key=lambda x: x[0])],
      [0.13, 0.3, 0.3, 0.27], "Requirement to design, code and tests", size=9)
page_break()

# ================================================================ 4. wireframes
h("4. Wireframes and UI Design", 1)
body("The wireframes were drawn before the screens were built. They fix layout, navigation, fields and buttons, not "
     "colours; the numbered markers point out the main regions of each screen.")
table([["Screen", "Purpose", "Requirements"],
       ["Sign in / sign up / e-mail code", "Accounts with a second factor", "FR-01 to FR-06"],
       ["Overview", "Farm summary, weather, latest results, full auto analysis", "FR-25, FR-29"],
       ["Crop, Yield, Fertiliser, Disease", "The four tools, each with custom input or dataset auto-fill", "FR-11 to FR-19, FR-28"],
       ["Assistant", "Chat in the chosen language", "FR-20, FR-21"],
       ["Farms", "Map and farm details", "FR-09, FR-10"],
       ["History, Reports, Settings", "Review, export and profile", "FR-07, FR-24, FR-25"]], [0.3, 0.48, 0.22], "Screens and the requirements they cover")
SCREEN_TAB = TAB_N[0]
for f, t in (("01_sign_in.png", "Sign-in wireframe"), ("04_overview.png", "Overview wireframe"),
             ("07_fertiliser.png", "Fertiliser wireframe as first drawn, when the page showed only a nutrient category. "
                                   "The final page names the fertiliser (Section 5.3)"),
             ("08_disease.png", "Disease detection wireframe")):
    figure(WF / f, t, max_h=14)
figure_row([(WF / "m1_overview.png", "Overview"), (WF / "m2_crop.png", "Crop tool"), (WF / "m3_disease.png", "Disease")],
           "Phone-width wireframes", height=10)
h("4.1 Wireframe Review Checklist", 2)
table([["Checklist item (guideline 6.3)", "How it is met"],
       ["Every major requirement has a screen", f"Table {SCREEN_TAB} maps every screen to its requirements"],
       ["Navigation is clear", f"Sidebar on the web, bottom bar in the app; navigation map in Figure {NAV_FIG}"],
       ["Inputs have labels and validation", "Every field shows its unit and allowed range; errors appear under the field"],
       ["Buttons have meaningful names", "Verbs that say what happens: Predict Suitable Crop, Recommend fertiliser, Scan a leaf"],
       ["Error and success messages", "Field errors, toasts on save, Retry state when a service fails"],
       ["Usable on the target device", "Tested at 375 px (TC-066) and on an Android phone"]], [0.4, 0.6], "Wireframe review")
page_break()

# ================================================================ 5. implementation
h("5. Implementation", 1)
body("The guideline's example prototype is a Java console program. Our prototype is larger: a working web system and an "
     "Android app. The server is Python because the machine-learning libraries we needed (scikit-learn, LightGBM, ONNX "
     "Runtime) are written for it. The Android app is Kotlin, which runs on the same JVM-style runtime as Java and uses "
     "the same object-oriented design (classes, encapsulation, interfaces).")
h("5.1 Project Structure", 2)
code("""
Ai and Software Engg/            (server, web client, models, tests)
  app/main.py                    API routes, sessions, validation
  app/db.py  otp.py  ml.py       repository, e-mail codes, model serving
  app/fertiliser.py              shortfall step + fertiliser model
  app/external.py  assistant.py  weather/soil clients, AI assistant
  app/static/                    web dashboard (HTML, JS, CSS)
  app/models/                    trained models + model cards (JSON)
  ml/train_*.py                  training scripts (crop, yield, leaf, fertiliser)
  tests/                         88 automated tests + load test (tests/load)
  Dockerfile  docker-compose.yml
Ai_and_Soft_Engg/                (Android app, Kotlin)
  app/src/main/java/com/example/agrisense/
    data/Api.kt  Session.kt      HTTP client, encrypted session
    ui/home  predict  scan  assistant  farms  more   screens
""")
h("5.2 Machine-Learning Models", 2)
table([["Model", "Data", "Method", "Result"],
       ["Crop recommendation", "2,200 rows, 22 crops", f"{crop['selected_model']}, best of 5 by 5-fold CV", f"{pct(crop['test_accuracy'])} test accuracy"],
       ["Yield prediction", "345,407 district records, 1997-2020", "LightGBM on the change from the 3-year mean", f"MAE {YR['mae_t_ha']} t/ha, R² {YR['r2']} on unseen years"],
       ["Leaf disease", "61,486 images, 39 classes", "EfficientNet-B0 fine-tuned on GPU, calibrated", f"{pct(LT['accuracy'])} test accuracy"],
       ["Fertiliser", "99 rows, 7 fertilisers", f"{fert['chosen']['model']} on N, P, K, best of 8 by repeated CV", f"{pct(fert['chosen']['cv_accuracy_mean'])} cross-validated"]],
      [0.2, 0.24, 0.32, 0.24], "Trained models")
figure(FIGS / "crop_comparison.png", "Crop model: cross-validation and test accuracy of five algorithms", width=13)
figure(FIGS / "fert_comparison.png", "Fertiliser model: eight candidates; N, P, K alone beat all features", width=13)
body("The fertiliser dataset records the nutrient to supply on its own scale, while a soil sample records what is already "
     "in the soil. The fertiliser service therefore compares each nutrient with the crop's typical level, turns the "
     "shortfall into a nutrient need in the same proportions, and asks the model. It only accepts a fertiliser that "
     "supplies every nutrient that is short (simplified from app/fertiliser.py):")
code('''
def recommend(inputs, crop_profiles):
    typical, unit = _typical(basis, crop, crop_profiles)        # crop median or Soil Health Card band
    for n, v in values.items():
        s = max(0.0, (typical[n] - v) / typical[n])             # shortfall as a fraction
        shortfall[n] = 0.0 if s < MIN_SHORTFALL else s
    top_s = max(shortfall.values())
    need = {n: shortfall[n] / top_s * NEED_MAX[n] for n in NAMES}   # keep proportions
    if all(v <= 0 for v in need.values()):
        return "No fertiliser needed"
    require = [n for n in NAMES if shortfall[n] >= 0.25 * top_s]
    return predict(need, require)                                # model's best fertiliser that supplies them
''')
h("5.3 Web Dashboard", 2)
figure(SHOTS / "02_overview.png", "Overview page", max_h=15)
figure(SHOTS / "05_fertiliser.png", "Full auto analysis: soil sample, crop model, then the fertiliser model", max_h=17)
figure(SHOTS / "06_disease.png", "Leaf disease detection", max_h=15)
h("5.4 Android App", 2)
body("The app has no database or business rules of its own. It signs in with the same e-mail code, keeps a bearer token "
     "in encrypted storage and calls the same API, so every result appears on both the web and the phone.")
figure_row([(AND / "welcome.png", "Welcome screen"), (AND / "home.png", "Home"), (AND / "chain.png", "Full analysis")],
           "Android app (screenshots from a Samsung phone)")
figure_row([(AND / "fertiliser.png", "Fertiliser result"), (AND / "scan.png", "Leaf scan"), (AND / "farm.png", "Farm on the map")],
           "Android app: results and farms")
figure_row([(AND / "hindi.png", "Settings in Hindi"), (AND / "dark.png", "Dark theme"), (AND / "assistant.png", "Assistant")],
           "Android app: language, theme and assistant")
page_break()

# ================================================================ 6. testing
h("6. Testing", 1)
h("6.1 Approach", 2)
layers = {}
for c in cases:
    layers[c["type"]] = layers.get(c["type"], 0) + 1
table([["Layer", "Tool", "Cases"]] + [[k.replace("Automated - ", ""), {"API / integration": "FastAPI TestClient, throwaway database",
                                                                       "Model quality": "Model cards and direct inference",
                                                                       "Live services": "Real Open-Meteo, NASA POWER, SoilGrids, Mistral",
                                                                       "UI end-to-end": "Playwright driving Microsoft Edge"}.get(k.replace("Automated - ", ""), "pytest"), str(v)]
                                      for k, v in sorted(layers.items())], [0.3, 0.55, 0.15], "Test layers")
body(f"All {len(cases)} test cases are automated and run with one command (python -m pytest tests). On {RUN_DATE} "
     f"**{passed} of {len(cases)} passed** in {total_time:.0f} seconds. Each case lists its requirement, type "
     "(positive, negative or boundary), input and expected result.")
h("6.2 Test Cases", 2)
kind = lambda tc: "Boundary" if tc in C.BOUNDARY else "Negative" if tc in C.NEGATIVE else "Positive"
table([["TC ID", "Req.", "Type", "Test input", "Expected result", "Result"]] +
      [[c["id"], ", ".join(req_of.get(c["id"], [])) or "-", kind(c["id"]), f"{c['title']}. {c['data']}".replace(". -", ""),
        c["expected"], res.get(c["func"], ("Not run",))[0]] for c in cases],
      [0.08, 0.1, 0.1, 0.32, 0.32, 0.08], "Test cases and results", size=8)
counts = {k: sum(1 for c in cases if kind(c["id"]) == k) for k in ("Positive", "Negative", "Boundary")}
body(f"The set has {counts['Positive']} positive, {counts['Negative']} negative and {counts['Boundary']} boundary cases.")
figure(ROOT / "tests" / "evidence" / "TC-072b_fertiliser_from_chain.png", "Evidence from TC-072: the full analysis ends on the fertiliser result", max_h=13)

# ---------------- 6.4 load test
h("6.3 Load and Capacity Testing", 2)
b = LOAD["bench"]; hst = LOAD["host"]
body("The functional tests show the system is correct for one user. The load test answers a different question: how "
     "many farmers can use it at the same time on the real server before it slows down, and what happens when too many "
     "arrive at once.")
body(f"**Setup.** The test ran on the production VPS ({hst['vcpus']} vCPU, {hst['cpu'].replace(' 32-Core Processor', '')}, "
     "8 GB RAM shared with other services) against a separate copy of the live container: the same image, the same two "
     "worker processes and the same 1.2 GB memory limit, but its own empty database and no e-mail codes. Live users and "
     "live data were not touched. The load generator ran on the same machine, limited to half a CPU, so the network did "
     "not affect the numbers; it does take a little CPU from the server, so the capacity below is slightly cautious.")
figure(FIGS / "load_setup.png", "Load-test setup on the production VPS")
body("Simulated users follow the way the app is actually used: page data and history most often, model calls less, leaf "
     "photos least (me 20%, overview 15%, history 10%, crop 20%, fertiliser 20%, yield 10%, leaf photo 5%). The chat "
     "assistant was left out because it calls a paid outside API. Each user waits about one second between requests, "
     "as a person reading a result would.")
table([["Test", "What it measures", "How"],
       ["Model benchmark", "Time for one prediction, no web layer", "Each model called directly in the server container"],
       ["Baseline", "Response time with no other traffic", "Each endpoint alone, one request at a time"],
       ["Throughput", "Most requests per second an endpoint can serve", "Each endpoint alone, 8 clients, no pauses, 20 s"],
       ["Step (capacity)", "How many users before the 2 s target is missed", "10, 25, 50, 100, 150, 200 users, 30 s each"],
       ["Spike (load handling)", "Behaviour when users jump suddenly", "5 users, then 150 at once for 30 s, then back to 5"]],
      [0.2, 0.4, 0.4], "Load tests run")
h("6.3.1 Model speed", 3)
figure(FIGS / "load_models.png", "Time per prediction on the server CPU (one core)")
table([["Model", "Mean (ms)", "p95 (ms)", "Predictions per second, one core"]] +
      [[lbl, f"{b[k]['mean_ms']:.1f}", f"{b[k]['p95_ms']:.1f}", f"{b[k]['per_second_one_core']:,.0f}"]
       for k, lbl in (("crop_recommendation", "Crop (Random Forest)"), ("yield_prediction", "Yield (LightGBM)"),
                      ("fertiliser", "Fertiliser (Logistic Regression)"), ("leaf_disease", "Leaf disease (CNN)"))],
      [0.4, 0.18, 0.18, 0.24], "Model benchmark")
slow = max(("crop_recommendation", "yield_prediction", "fertiliser", "leaf_disease"), key=lambda k: b[k]["mean_ms"])
body(f"The slowest model is {dict(crop_recommendation='crop recommendation', yield_prediction='yield prediction', fertiliser='the fertiliser model', leaf_disease='leaf disease')[slow]} "
     f"at {b[slow]['mean_ms']:.0f} ms. The Random Forest has 400 trees and every tree is evaluated for each request. "
     f"The fertiliser model is a single linear layer and takes under a millisecond.")
h("6.3.2 Endpoints alone", 3)
figure(FIGS / "load_endpoints.png", "Response time alone and under 8 clients (left); requests per second (right)")
eps = list(LOAD["baseline"])
table([["Endpoint", "Alone, p50 (ms)", "8 clients, p95 (ms)", "Requests / s"]] +
      [[e, f"{LOAD['baseline'][e]['p50_ms']:.0f}", f"{LOAD['throughput'][e]['p95_ms']:.0f}", f"{LOAD['throughput'][e]['rps']:.0f}"] for e in eps],
      [0.4, 0.2, 0.2, 0.2], "Endpoint latency and throughput")
h("6.3.3 Capacity (step test)", 3)
figure(FIGS / "load_step.png", "Users against throughput and response time")
table([["Users", "Requests / s", "Median (ms)", "p95 (ms)", "p99 (ms)", "Errors"]] +
      [[str(s["users"]), f"{s['rps']:.1f}", f"{s['p50_ms']:.0f}", f"{s['p95_ms']:.0f}", f"{s['p99_ms']:.0f}", f"{s['errors']}"] for s in LOAD["step"]],
      [0.14, 0.18, 0.17, 0.17, 0.17, 0.17], "Step test results")
cap = LOAD["capacity_users_p95_under_2s"]
top_rps = max(s["rps"] for s in LOAD["step"])
body(f"Up to **{cap} simultaneous users** the server keeps 95% of responses under 2 seconds, meeting NFR-07. Beyond that "
     f"the throughput stops growing at about {top_rps:.0f} requests per second: both CPUs are busy, so extra users wait in "
     "a queue and response times rise. No request failed at any step; the server slows down rather than dropping "
     "requests.")
figure(FIGS / "load_resources.png", "CPU and memory of the server container during the step test")
body(f"CPU reached {LOAD['peak_cpu_percent']:.0f}% (200% means both vCPUs fully used) while memory stayed at "
     f"{LOAD['peak_mem_mib']:.0f} MiB of the 1,200 MiB limit. The limit is processing power, not memory, so the first "
     "upgrade would be more CPU cores and more worker processes.")
h("6.3.4 Load handling (spike test)", 3)
figure(FIGS / "load_spike.png", "Sudden jump from 5 to 150 users and back")
sp = LOAD["spike"]
body(f"When 150 users arrived at once, the server served {sp['requests']:,} requests in 30 seconds with "
     f"{sp['errors']} errors; p95 rose to {sp['p95_ms'] / 1000:.1f} s while the queue built up. Within a few seconds of the "
     f"load dropping back to 5 users, p95 returned to {sp['after_p95_ms']:.0f} ms. Nothing crashed or restarted.")
body(f"In total the load test sent {LOAD['total_requests']:,} requests and {LOAD['total_errors']} failed.")
table([["Finding", "Result"],
       ["Capacity within the 2 s target", f"{cap} simultaneous active users"],
       ["Maximum throughput (mixed traffic)", f"about {top_rps:.0f} requests per second"],
       ["Errors under load", f"{LOAD['total_errors']} of {LOAD['total_requests']:,} requests"],
       ["Bottleneck", "CPU (both vCPUs); memory under half the limit"],
       ["Slowest model", "Crop recommendation (Random Forest, 400 trees)"],
       ["Recovery after a spike", "Immediate; no restarts"]], [0.45, 0.55], "Load-test summary")
page_break()

# ================================================================ 7. assumptions, limitations, future
h("7. Assumptions, Limitations and Future Enhancements", 1)
h("7.1 Assumptions", 2); bullets(C.ASSUMPTIONS)
h("7.2 Limitations", 2); bullets(C.LIMITATIONS)
h("7.3 Future Enhancements", 2); bullets(C.FUTURE)

# ================================================================ 8. references
h("8. References", 1)
REFS = (["Crop Recommendation Dataset (Kaggle), 2,200 rows, 22 crops.",
          "India Agriculture Crop Production 1997-2021, Open Government Data Platform India (data.gov.in).",
          "Pandian, J. A. and Gopal, G. (2019). Data for: Identification of Plant Leaf Diseases Using a 9-layer Deep Convolutional Neural Network. Mendeley Data.",
          "Fertilizer Prediction dataset (Kaggle), 99 rows, 7 fertilisers.",
          "Soil Health Card scheme, Ministry of Agriculture and Farmers Welfare, Government of India.",
          "Open-Meteo weather API; NASA POWER daily data; ISRIC SoilGrids 2.0.",
          "Tan, M. and Le, Q. (2019). EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks. ICML.",
          "Ke, G. et al. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. NeurIPS.",
          "IEEE Std 830-1998, Recommended Practice for Software Requirements Specifications.",
          "Software Engineering Project Documentation and Implementation Guideline, Version 1.0, September 2026."])
for i, ref in enumerate(REFS, 1):
    p = para(f"[{i}]  {ref}", after=3)
    p.paragraph_format.left_indent = Cm(0.9); p.paragraph_format.first_line_indent = Cm(-0.9)

OUT.parent.mkdir(exist_ok=True)
doc.save(OUT)
print("wrote", OUT, f"{FIG_N[0]} figures, {TAB_N[0]} tables")
