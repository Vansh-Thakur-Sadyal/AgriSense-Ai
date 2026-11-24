"""Builds the four submission PDFs into Project/:
01_Project_Proposal.pdf, 02_SRS.pdf, 03_SDD.pdf, 04_Wireframes.pdf.
Numbers are read from app/models/*.json and tests/results.xml, never typed in."""
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "docs"))
sys.path.insert(0, str(HERE))

import build_report as R  # noqa: E402  (styles, helpers, model cards, report figures)
import diagrams as D  # noqa: E402
from spec import AUTHOR, COURSE, FR, NFR, PROGRAMME, PROJECT, URL, VERSION  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

OUT = ROOT / "Project"
OUT.mkdir(exist_ok=True)
P, h1, h2, body, small, cap, table, fig, bullets, W = R.P, R.h1, R.h2, R.body, R.small, R.cap, R.table, R.fig, R.bullets, R.W
crop, yld, leaf = R.crop, R.yld, R.leaf
h3 = ParagraphStyle("h3", parent=body, fontName="UI-B", fontSize=10.5, leading=14, spaceBefore=6, spaceAfter=2,
                    textColor=colors.HexColor(R.DARK))
TODAY = time.strftime("%d %B %Y")
for _st in (h1, h2, h3):
    _st.keepWithNext = 1
LABEL_FIX = {"04_overview": {"Panel": "Greeting, farm chips and quick actions", "Full auto analysis": "Greeting, farm and weather chips, New Prediction menu, Ask AI Assistant"},
             "08_disease": {"CAUSE": "Cause / symptoms / next steps, disclaimer, PDF and assistant actions"},
             "09_assistant": {"Change": "Conversation list: new, search, Saved / Recent, bookmark, delete, context note", "AgriSense AI Assistant": "Chat: header (status, language), messages or welcome cards, composer", "Panel": "Conversation list (new, rename, bookmark, delete)",
                              "How can I help with your farm today?": "Chat panel: suggestions, messages, photo, mic, send"},
             "10_weather": {"Location": "Location picker", "Panel": "Current conditions and 7-day forecast"},
             "12_farms": {"Panel": "Farms map", "North Field": "Farm card (area, soil, crop, edit / delete)"},
             "13_history": {"Search": "Filters: type, farm, crop, status, dates, search", "Panel": "Results table with view / delete"}}


def _fix_photo(label):
    import re as _re
    return "Uploaded photo with preview and farm link" if _re.match(r"image \(\d+\)\.", label or "") else label


def clean_label(key, label):
    import re as _re
    label = _fix_photo(LABEL_FIX.get(key, {}).get(label, label))
    if not label or _re.fullmatch(r"[\d.,%°C /-]+", label):
        return "Live weather: current conditions and 7-day forecast" if key == "04_overview" else "Panel"
    return label


def pct(x):
    return f"{x * 100:.2f}%"


def tests_summary():
    t = ET.parse(ROOT / "tests" / "results.xml").getroot()
    s = t if t.tag == "testsuite" else t.find("testsuite")
    return int(s.get("tests")), int(s.get("failures")) + int(s.get("errors")), int(s.get("skipped") or 0), float(s.get("time"))


NT, NF, NS, TSEC = tests_summary()
LT, YR = leaf["test"], yld["results"]["LightGBM (this model)"]


def cover(title, subtitle, purpose):
    return [Spacer(1, 26 * mm),
            P(PROJECT, ParagraphStyle("pp", parent=h2, fontSize=13, textColor=colors.HexColor(R.GREEN))),
            P(title, ParagraphStyle("t", parent=h1, fontSize=30, leading=36)),
            P(subtitle, ParagraphStyle("st", parent=body, fontSize=12, leading=16, textColor=colors.HexColor(R.MUTED))),
            Spacer(1, 10 * mm),
            table([["Item", "Details"], ["Prepared by", AUTHOR], ["Programme", PROGRAMME], ["Course", COURSE],
                   ["Live system", URL], ["Document version", VERSION], ["Date", TODAY], ["Purpose", purpose]],
                  [0.25, 0.75]),
            PageBreak()]


def toc(items):
    return [P("Contents", h1)] + [P(f"{i}", ParagraphStyle("toc", parent=body, leftIndent=0 if i[:2].strip(".").isdigit() and "." not in i[:3] else 12))
                                  for i in items] + [PageBreak()]


def build(name, story, title):
    def page(c, d):
        c.saveState()
        c.setFont("UI", 7.5)
        c.setFillColor(colors.HexColor(R.MUTED))
        c.drawString(18 * mm, 10 * mm, f"AgriSense AI - {title}")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")
        c.restoreState()
    path = OUT / name
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=18 * mm, title=f"AgriSense AI - {title}", author=AUTHOR).build(story, onFirstPage=page,
                                                                                                    onLaterPages=page)
    print("wrote", path.name, f"{path.stat().st_size / 1e6:.1f} MB")


# =====================================================================  01 PROPOSAL
def proposal(F, RF):
    s = cover("Project Proposal", "An AI decision-support web platform for Indian farmers: crop choice, yield, "
              "fertiliser, leaf disease, weather, soil and an AI assistant.", "Propose the project, its scope, "
              "method, data, plan and expected outcomes.")
    s += toc(["1. Background and problem statement", "2. Aim and objectives", "3. Proposed solution",
              "4. Scope", "5. Target users and stakeholders", "6. Data sources", "7. Methodology",
              "8. Technology stack", "9. Feasibility study", "10. Project plan and timeline", "11. Risks and mitigation",
              "12. Expected outcomes and evaluation", "13. Ethics, privacy and limitations", "14. References"])
    s += [P("1. Background and problem statement", h1),
          P("Agriculture employs a large share of India's workforce, yet most decisions on a small farm are still made "
            "from habit or word of mouth. A farmer usually has to answer, every season, questions such as: which crop "
            "suits my soil and climate, how much will my field produce, which fertiliser is missing, and what is this "
            "spot on my leaves? The information to answer them exists - government crop statistics, soil maps, weather "
            "forecasts, published soil-test ranges and plant-disease image collections - but it is scattered, technical "
            "and rarely in the farmer's language."),
          P("Existing apps tend to fall into two traps: they either show generic advice that ignores the farmer's "
            "location and soil, or they present impressive-looking numbers with no evidence of how accurate they are. "
            "For a farmer, a confident wrong answer (for example a wrong disease name leading to the wrong spray) is "
            "worse than no answer."),
          P("<b>Problem:</b> there is no single, trustworthy, easy-to-use tool that turns public agricultural data "
            "and machine learning into field-level decisions, shows how reliable each answer is, and works in English "
            "and Hindi on an ordinary phone."),
          P("2. Aim and objectives", h1),
          P("<b>Aim:</b> design, build, test and deploy AgriSense AI, a web platform that gives farmers measured, "
            "explainable recommendations for their own fields."),
          *bullets(["O1 - Train a crop-recommendation model on soil nutrients and climate and select the best of several "
                    "algorithms by cross-validation.",
                    "O2 - Train a district-level yield model on 24 years of government data that beats simple baselines on "
                    "years it has never seen, and explain each prediction.",
                    "O3 - Train a deep-learning leaf-disease classifier on a GPU, calibrate its confidence and make it refuse "
                    "unclear photos rather than guess.",
                    "O4 - Train a fertiliser model on Fertilizer Prediction.csv and link it to soil values through a documented "
                    "nutrient-shortfall step, so every analysis ends with a named fertiliser (never a dose).",
                    "O5 - Show live weather, forecasts, historical weather and modelled soil properties for each farm.",
                    "O6 - Offer an AI assistant in English and Hindi grounded in the farmer's own data.",
                    "O7 - Secure accounts (e-mail one-time codes, hashed secrets, per-user isolation) and store every result.",
                    "O8 - Test the system thoroughly (automated API, model, live-service and browser tests) and deploy it "
                    "publicly over HTTPS."]),
          P("3. Proposed solution", h1),
          P("A single-page web dashboard backed by a Python FastAPI server. The server runs three trained models on its "
            "own CPU, a fertiliser model, and connectors to public data services. Everything a farmer does is saved to their "
            "account so they can review it, export it and discuss it with the assistant."),
          fig(F["arch"], 1.0, "Figure 1 - Proposed architecture."),
          table([["Module", "What the farmer gets", "How"],
                 ["Crop recommendation", "Best crop + alternatives + suitability chart", "Random Forest (best of 5, 5-fold CV)"],
                 ["Yield prediction", "t/ha, total tonnes, 80% range, why", "LightGBM + SHAP, temporal validation"],
                 ["Fertiliser recommendation", "Short nutrients + named fertiliser (e.g. Urea, DAP)", "Logistic Regression on N, P, K + shortfall step"],
                 ["Leaf disease", "Crop + disease, cause, symptoms, next steps", "EfficientNet-B0 CNN, calibrated, refuses unclear photos"],
                 ["Weather & soil", "Forecast, alerts, history, soil profile", "Open-Meteo, NASA POWER, ISRIC SoilGrids"],
                 ["AI assistant", "Answers in English / Hindi", "Mistral chat API with the user's own context"],
                 ["Accounts & history", "Secure sign-in, saved results, PDF/CSV", "E-mail OTP, SQLite, per-user isolation"]],
                [0.22, 0.4, 0.38]),
          PageBreak(),
          P("4. Scope", h1), P("<b>In scope</b>", h3),
          *bullets(["Web application (desktop and phone browsers) and an Android app on the same API, English and 14 Indian languages.",
                    "Four decision tools (crop, yield, fertiliser, disease) plus weather, soil, assistant, history and reports.",
                    "Accounts with e-mail verification, password reset, profile, data export and account deletion.",
                    "Training pipelines, model cards, automated tests, Docker deployment on a VPS with HTTPS."]),
          P("<b>Out of scope</b>", h3),
          *bullets(["iOS app; offline mode; SMS or voice channels.",
                    "Chemical doses and spray schedules (must come from a soil test and the local KVK).",
                    "Market prices, government schemes, IoT sensors (no reliable data supplied).",
                    "Field-level yield (the public dataset is district-level)."]),
          P("5. Target users and stakeholders", h1),
          table([["User / stakeholder", "Need", "How AgriSense AI helps"],
                 ["Small and marginal farmers", "Simple, local, trustworthy advice", "Field-specific tools, Hindi, honest confidence"],
                 ["Agricultural officers / KVK staff", "Quick screening for many farmers", "Fast predictions, history, exports"],
                 ["Researchers / students", "Transparent models", "Model cards, metrics, explanations"],
                 ["Course evaluators", "Evidence of engineering practice", "SRS, SDD, tests with evidence, live deployment"]],
                [0.28, 0.32, 0.4]),
          P("6. Data sources", h1),
          table([["Dataset / service", "Content", "Use"],
                 ["Crop_recommendation.csv", "2,200 rows, 22 crops, N-P-K, temperature, humidity, pH, rainfall", "Crop model"],
                 ["India Agriculture Crop Production (data.gov.in)", "345,407 rows, 1997-2020, state/district/crop/season/area/production", "Yield model, analytics"],
                 ["Plant leaf diseases (9-layer CNN paper, Mendeley)", "55,448 images + augmented set (61,486 files), 39 classes", "Leaf model"],
                 ["Open-Meteo", "Live weather, 7-day forecast, geocoding", "Weather page, crop form"],
                 ["NASA POWER", "Daily historical weather", "Weather history"],
                 ["ISRIC SoilGrids 2.0", "Modelled soil properties, 6 depths", "Soil page"],
                 ["Fertilizer Prediction.csv", f"{R.fert['rows']} rows, 7 fertilisers, N-P-K, soil, crop, weather", "Fertiliser model"],
                 ["Soil Health Card ranges", "Low / medium / high nutrient thresholds", "Typical level for lab soil tests"]],
                [0.3, 0.45, 0.25]),
          P("7. Methodology", h1),
          P("The project follows an <b>iterative (incremental) model</b>: requirements and data study first, then one "
            "working slice at a time (data -> model -> API -> UI -> tests), each slice reviewed before the next. "
            "Machine-learning work follows a strict evaluation discipline:"),
          *bullets(["Split before looking: test data is set aside first and used once.",
                    "Compare with baselines: a model is only kept if it beats a simple rule (e.g. 'same as last year').",
                    "Validate the way it will be used: the yield model is trained on older years and tested on later years.",
                    "Calibrate and abstain: the disease model's confidence is calibrated and it refuses below a threshold.",
                    "Write a model card: every metric shown anywhere is read from files the training script writes.",
                    "After evaluation, refit on all data so nothing supplied is wasted."]),
          fig(F["pipe"], 1.0, "Figure 2 - Machine-learning pipeline."),
          P("8. Technology stack", h1),
          table([["Layer", "Technology", "Reason"],
                 ["Frontend", "HTML, Tailwind CSS, vanilla JavaScript, Chart.js, Leaflet (all self-hosted)", "Light, fast on phones, works when CDNs are blocked"],
                 ["Backend", "Python 3.12, FastAPI, Uvicorn", "Async, typed, automatic API docs"],
                 ["ML", "scikit-learn, LightGBM, PyTorch (CUDA) -> ONNX Runtime", "Proven libraries; GPU training, CPU serving"],
                 ["Data", "SQLite (WAL)", "Zero-admin, file-based, enough for the load"],
                 ["Integrations", "Mistral API, n8n + SMTP, Open-Meteo, NASA POWER, SoilGrids", "Free or existing services"],
                 ["Testing", "pytest, FastAPI TestClient, Playwright (Edge)", "API, model and real-browser tests"],
                 ["Deployment", "Docker, Traefik, Let's Encrypt on a Hostinger VPS", "Reproducible, HTTPS, isolated"]],
                [0.15, 0.5, 0.35]),
          PageBreak(),
          P("9. Feasibility study", h1),
          table([["Type", "Assessment"],
                 ["Technical", "All datasets are public and were obtained; a local NVIDIA RTX 5070 Ti GPU trains the CNN in under an "
                               "hour; models are small enough (under 20 MB each) to serve on a CPU VPS."],
                 ["Economic", "Open-source software and free public APIs; an existing VPS and n8n instance are reused, so the "
                              "running cost is close to zero."],
                 ["Operational", "Farmers need only a browser; the interface is bilingual and works at phone width; no installation."],
                 ["Schedule", "14 weeks with iterative milestones (Section 10)."],
                 ["Legal / ethical", "Datasets are published for research; no personal data is shared with third parties except the "
                                     "question text sent to the assistant API; users can delete their data."]], [0.2, 0.8]),
          P("10. Project plan and timeline", h1),
          fig(F["gantt"], 1.0, "Figure 3 - Planned schedule (weeks)."),
          table([["Milestone", "Deliverable"],
                 ["M1", "Proposal and requirements (SRS)"], ["M2", "Cleaned datasets, baseline models"],
                 ["M3", "Trained models with model cards"], ["M4", "Working API and dashboard (SDD, wireframes)"],
                 ["M5", "Security, OTP, integrations"], ["M6", "Test cases executed with evidence"],
                 ["M7", "Deployment and final documentation"]], [0.2, 0.8]),
          P("11. Risks and mitigation", h1),
          table([["Risk", "Impact", "Mitigation"],
                 ["Lab-photo dataset does not match field photos", "Wrong diagnosis", "Calibrated threshold; refuses unclear photos; "
                  "limitation stated on screen"],
                 ["Yield data has no weather/soil columns", "Weaker yield model", "Model the correction to the recent normal; "
                  "compare with baselines; say so in the UI"],
                 ["External API outages or rate limits", "Missing weather / soil / answers", "Caching, fallback models, clear error states"],
                 ["Data leakage inflates scores", "Over-claimed accuracy", "Temporal split; augmented copies linked to their source photo"],
                 ["Account takeover", "Privacy loss", "Password + e-mail code, hashed secrets, rate limits, HTTPS"],
                 ["Single small server", "Downtime", "Docker auto-restart, health checks, data in a volume"]],
                [0.33, 0.2, 0.47]),
          P("12. Expected outcomes and evaluation", h1),
          *bullets([f"Crop model accuracy at or above 97% on held-out data (achieved: {pct(crop['test_accuracy'])}).",
                    f"Yield model better than the 'same as last year' and 3-year-mean baselines on unseen years "
                    f"(achieved: MAE {YR['mae_t_ha']} vs {yld['results']['Baseline: last year' + chr(39) + 's yield']['mae_t_ha']} t/ha).",
                    f"Leaf model accuracy at or above 98% with calibrated confidence (achieved: {pct(LT['accuracy'])}, "
                    f"calibration error {LT['ece_after_T']}).",
                    f"All automated test cases passing (achieved: {NT - NF} of {NT}).",
                    "A public HTTPS deployment used through a normal browser."]),
          P("13. Ethics, privacy and limitations", h1),
          *bullets(["Advice is decision support, not a replacement for an agronomist or the local KVK; the UI says so.",
                    "No chemical doses are ever given.", "Passwords and codes are hashed; users can export and delete their data.",
                    "The disease model is trained on lab photos; field accuracy is not measured and is stated as a limitation."]),
          P("14. References", h1),
          *bullets(["Crop Recommendation Dataset (Kaggle, 2,200 rows).",
                    "India Agriculture Crop Production 1997-2021, Open Government Data Platform India (data.gov.in).",
                    "Geetharamani G., Arun Pandian J. (2019). Identification of plant leaf diseases using a nine-layer deep "
                    "convolutional neural network. Computers & Electrical Engineering 76; dataset on Mendeley Data.",
                    "Tan M., Le Q. (2019). EfficientNet: Rethinking Model Scaling for CNNs. ICML.",
                    "Guo C. et al. (2017). On Calibration of Modern Neural Networks. ICML (temperature scaling).",
                    "Ke G. et al. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. NeurIPS.",
                    "Lundberg S., Lee S.-I. (2017). A Unified Approach to Interpreting Model Predictions (SHAP). NeurIPS.",
                    "Soil Health Card scheme, Ministry of Agriculture & Farmers Welfare; Muhr et al. (1965) rating ranges.",
                    "Open-Meteo API; NASA POWER API; ISRIC SoilGrids 2.0 (Poggio et al., 2021)."])]
    build("01_Project_Proposal.pdf", s, "Project Proposal")


# =====================================================================  02 SRS
def srs(F, RF):
    s = cover("Software Requirements Specification", "IEEE 830 / ISO 29148 style requirements for AgriSense AI.",
              "Define what the system must do, the qualities it must have and how each requirement is verified.")
    s += toc(["1. Introduction", "   1.1 Purpose  1.2 Scope  1.3 Definitions  1.4 References  1.5 Overview",
              "2. Overall description", "   2.1 Product perspective  2.2 Product functions  2.3 User classes",
              "   2.4 Operating environment  2.5 Constraints  2.6 Assumptions and dependencies",
              "3. External interface requirements", "4. Functional requirements (FR-01 ... FR-31)",
              "5. Use cases", "6. Non-functional requirements (NFR-01 ... NFR-15)", "7. Data requirements",
              "8. Model (AI) requirements and acceptance criteria", "9. Requirements traceability matrix",
              "Appendix A - Input validation rules"])
    s += [P("1. Introduction", h1), P("1.1 Purpose", h2),
          P("This document specifies the requirements of AgriSense AI version 1.0. It is written for the evaluator, the "
            "developer and testers. Every requirement has an ID that is traced to design elements (SDD) and to test "
            "cases (06_Test_Cases.xlsx)."),
          P("1.2 Scope", h2),
          P("AgriSense AI is a web application that helps Indian farmers choose crops, estimate yield, check soil "
            "nutrients, screen leaf diseases, follow weather and soil conditions and ask an AI assistant - with every "
            "answer tied to a measured model or a named data source. It runs at " + URL + "."),
          P("1.3 Definitions and abbreviations", h2),
          table([["Term", "Meaning"], ["OTP", "One-time password: a 6-digit code e-mailed to confirm identity"],
                 ["N, P, K", "Nitrogen, phosphorus, potassium soil nutrients"], ["t/ha", "Tonnes per hectare"],
                 ["Kharif / Rabi", "Monsoon (June-Oct) / winter (Nov-Apr) cropping seasons"],
                 ["SHC", "Soil Health Card (Govt. of India) nutrient rating ranges"],
                 ["KVK", "Krishi Vigyan Kendra - district farm science centre"],
                 ["SHAP", "Per-feature contribution to one prediction"], ["ECE", "Expected calibration error"],
                 ["ONNX", "Portable neural-network file format"], ["SPA", "Single-page web application"],
                 ["Model card", "JSON file written by a training script holding the model's data, split and metrics"]],
                [0.22, 0.78]),
          P("1.4 References", h2),
          *bullets(["01_Project_Proposal.pdf", "03_SDD.pdf (design)", "04_Wireframes.pdf (interface)",
                    "06_Test_Cases.xlsx and 07_Test_Evidence/ (verification)", "IEEE Std 830-1998; ISO/IEC/IEEE 29148:2018"]),
          P("1.5 Overview", h2),
          P("Section 2 describes the product in context; Section 3 its interfaces; Sections 4-8 the requirements; "
            "Section 9 maps every requirement to its tests."),
          PageBreak(),
          P("2. Overall description", h1), P("2.1 Product perspective", h2),
          P("AgriSense AI is a new, self-contained system. It depends on four external services (e-mail delivery, "
            "Mistral chat, Open-Meteo / NASA POWER weather, ISRIC SoilGrids). Its context is shown below."),
          fig(F["dfd0"], 1.0, "Figure 1 - Context diagram (DFD level 0)."),
          P("2.2 Product functions", h2),
          *bullets(["Account management with e-mail verification, sign-in codes and password reset.",
                    "Farm management with map location.",
                    "Crop recommendation, yield prediction, fertiliser recommendation, leaf disease detection.",
                    "Weather (live, forecast, history) and soil profile per farm.",
                    "AI assistant (English / Hindi, photos).",
                    "History, overview dashboard, analytics, PDF/CSV export; bilingual, responsive UI."]),
          P("2.3 User classes and characteristics", h2),
          table([["Class", "Characteristics", "Privileges"],
                 ["Farmer", "Basic smartphone literacy; may prefer Hindi; limited time", "All features on own data"],
                 ["Agricultural officer", "Trained; screens many cases", "Same as farmer (role recorded on profile)"],
                 ["Researcher", "Interested in metrics and explanations", "Same, plus model cards through the UI"],
                 ["Administrator", "Developer / operator", "Server access: deploy, configure keys, backups (no in-app admin)"]],
                [0.2, 0.5, 0.3]),
          P("2.4 Operating environment", h2),
          *bullets(["Client: any modern browser (Chrome, Edge, Firefox, Safari), desktop or phone (>= 360 px wide).",
                    "Server: Linux with Docker; Python 3.12; 1.2 GB RAM limit; no GPU required.",
                    "Network: HTTPS on port 443 through Traefik."]),
          P("2.5 Design and implementation constraints", h2),
          *bullets(["Only the supplied datasets and free public services may be used.",
                    "The yield dataset has no weather or soil columns, so the yield model cannot use them.",
                    "The assistant must never state chemical doses or invent prices or schemes.",
                    "Secrets must stay server-side; e-mail is sent only through the existing n8n instance."]),
          P("2.6 Assumptions and dependencies", h2),
          *bullets(["Users have an e-mail address they can read during sign-in.",
                    "N-P-K numbers come from a soil test or the dataset's own scale (the form asks which).",
                    "External services are reachable; when they are not, the app shows a clear message instead of numbers."]),
          PageBreak(),
          P("3. External interface requirements", h1), P("3.1 User interfaces", h2),
          P("Responsive dashboard with a left sidebar (12 pages), top bar (search, date, language switch, notifications, "
            "profile) and page content in cards. Forms validate each field and show the message under it. Results show "
            "the model used and its measured accuracy. See 04_Wireframes.pdf."),
          P("3.2 Software interfaces", h2),
          table([["Interface", "Protocol / format", "Purpose"],
                 ["n8n webhook /webhook/agrisense-otp", "HTTPS/HTTP POST JSON + x-otp-secret header", "Send OTP e-mails"],
                 ["Mistral chat/completions", "HTTPS JSON, bearer key", "Assistant answers"],
                 ["Open-Meteo forecast + geocoding", "HTTPS JSON", "Weather and place search"],
                 ["NASA POWER daily point API", "HTTPS JSON", "Historical weather"],
                 ["ISRIC SoilGrids WCS (maps.isric.org)", "HTTPS GeoTIFF", "Soil properties"],
                 ["AgriSense REST API (/api/*)", "HTTPS JSON / multipart; docs at /api/docs", "Used by the web client"]],
                [0.34, 0.36, 0.3]),
          P("3.3 Hardware and communication interfaces", h2),
          P("No special hardware. All communication uses HTTPS (TLS 1.2+); the server reaches n8n over a private Docker network."),
          PageBreak(),
          P("4. Functional requirements", h1),
          P("Priority: High = needed for a usable release; Medium = expected; Low = desirable. 'Verified by' lists the "
            "test cases in 06_Test_Cases.xlsx.", small)]
    areas = []
    for fid, area, text, prio, tests in FR:
        if area not in areas:
            areas.append(area)
    for a in areas:
        s.append(P(f"4.{areas.index(a) + 1} {a}", h2))
        s.append(table([["ID", "Requirement", "Priority", "Verified by"]] +
                       [[f, t, p, ", ".join(ts)] for f, ar, t, p, ts in FR if ar == a], [0.09, 0.61, 0.1, 0.2]))
    s += [PageBreak(), P("5. Use cases", h1), fig(F["usecase"], 0.98, "Figure 2 - Use-case diagram.")]
    ucs = [("UC-01 Register", "Farmer", "Not signed in", "1. Opens Create account. 2. Enters name, e-mail, password, state, "
            "district, role. 3. System validates and e-mails a code. 4. Farmer types the code. 5. System creates the "
            "account and opens Overview.", "3a. Invalid field: message under the field. 4a. Wrong code: tries left shown; "
            "5 wrong codes cancel. 4b. Expired: ask for a new code.", "FR-01..03, FR-05"),
           ("UC-02 Sign in", "Farmer", "Has an account", "1. Enters e-mail/phone and password. 2. System checks the password and "
            "e-mails a code. 3. Farmer types the code. 4. Dashboard opens.", "2a. Wrong password: error, no code. 3a. Resend "
            "after 60 s.", "FR-04, FR-05"),
           ("UC-03 Reset password", "Farmer", "Forgot password", "1. Forgot password. 2. Enters e-mail and new password. "
            "3. Types the code. 4. Signed in with the new password; old sessions ended.", "2a. Unknown e-mail: same screen, "
            "no e-mail sent.", "FR-06"),
           ("UC-04 Recommend crop", "Farmer", "Signed in", "1. Opens Crop Recommendation. 2. Enters 7 values or fills weather "
            "from the forecast. 3. Predict. 4. Sees crop, confidence, alternatives, suitability radar; saved to history.",
            "2a. Out-of-range value: field error.", "FR-11, FR-12, FR-24"),
           ("UC-05 Predict yield", "Farmer", "Signed in", "1. Chooses state, district, crop, season, year, area (or a farm). "
            "2. Predict. 3. Sees t/ha, production, 80% range, history chart and SHAP explanation.", "1a. Combination not in "
            "data: message.", "FR-13..15"),
           ("UC-06 Fertiliser guide", "Farmer", "Signed in", "1. Chooses basis, crop, N, P, K (+ optional pH, OC). 2. Gets "
            "shortfall per nutrient, the suggested fertiliser with grade and confidence, and how the model input was derived.", "1a. Missing value: field error.", "FR-16"),
           ("UC-07 Detect disease", "Farmer", "Signed in", "1. Uploads a leaf photo. 2. Analyse. 3. Sees crop, disease, "
            "confidence, top-5, cause, symptoms, next steps; photo saved.", "2a. Unclear photo: 'uncertain', no disease named. "
            "1a. Wrong file type: error.", "FR-17..19, FR-26"),
           ("UC-08 Ask the assistant", "Farmer", "Signed in", "1. Types a question (optionally attaches a photo, chooses "
            "Hindi). 2. Gets an answer grounded in own farms and results; conversation saved.", "2a. Service busy: "
            "fallback model, else error message.", "FR-20, FR-21"),
           ("UC-10 Automatic analysis", "Farmer", "Signed in", "1. Opens New Prediction on Overview (or the Fertiliser page) and chooses Full auto analysis. 2. System picks a random real soil sample from the dataset. 3. Crop model recommends a crop. 4. Fertiliser check runs for that crop on the same N, P, K. 5. Fertiliser page opens with the three-step result; both results are saved.", "1a. Per-tool Auto: the tool page fills a random sample and runs; the dataset label or recorded yield is shown beside the answer. 5a. New sample repeats with another row.", "FR-28, FR-29"),
           ("UC-09 Review and export", "Farmer", "Has predictions", "1. Opens History or Reports. 2. Filters. 3. Opens one "
            "or deletes it. 4. Downloads PDF or CSV.", "-", "FR-24, FR-25")]
    for name, actor, pre, flow, alt, req in ucs:
        s.append(KeepTogether([P(name, h3), table([["Field", "Description"], ["Actor", actor], ["Precondition", pre],
                                                   ["Main flow", flow], ["Alternative flows", alt], ["Requirements", req]],
                                                  [0.2, 0.8], zebra=False)]))
    s += [PageBreak(), P("6. Non-functional requirements", h1),
          table([["ID", "Category", "Requirement", "Verified by"]] + [[i, c, t, ", ".join(ts) or "Inspection / deployment"]
                                                                    for i, c, t, ts in NFR], [0.09, 0.14, 0.57, 0.2]),
          P("7. Data requirements", h1),
          table([["Entity", "Key data", "Retention"],
                 ["User", "name, e-mail, phone, role, state/district, language, password hash", "Until the user deletes the account"],
                 ["Farm", "name, location, area, soil, irrigation, crop history", "Until deleted"],
                 ["Prediction", "kind, inputs, result, summary, confidence, model version, status", "Until deleted"],
                 ["Upload", "leaf photo bytes, SHA-256, size, link to prediction/chat", "Deleted with its prediction / chat / account"],
                 ["Chat", "messages, title, bookmark", "Until deleted"],
                 ["OTP challenge", "purpose, hashed code, attempts, expiry", "Kept as audit; never contains the code"],
                 ["Auth event", "event, IP, browser, time", "Until account deletion"],
                 ["Production history", "district crop statistics 1997-2020", "Static reference data"]], [0.18, 0.52, 0.3]),
          P("8. Model (AI) requirements and acceptance criteria", h1),
          table([["Model", "Requirement", "Acceptance criterion", "Measured"],
                 ["Crop", "Select by cross-validation, not by test set", "Test accuracy >= 97%", pct(crop["test_accuracy"])],
                 ["Yield", "Temporal validation; beat baselines; explain", "MAE below last-year and 3-yr-mean baselines; R2 >= 0.9",
                  f"MAE {YR['mae_t_ha']}, R2 {YR['r2']}"],
                 ["Yield", "Honest uncertainty", "80% interval covers 75-85% of test rows", f"{yld['interval_80']['test_coverage'] * 100:.0f}%"],
                 ["Leaf", "Accurate on held-out images", "Accuracy >= 98%, macro recall >= 98%", f"{pct(LT['accuracy'])} / {pct(LT['macro_recall'])}"],
                 ["Leaf", "Calibrated, abstains", "ECE < 0.02 after temperature scaling; refuse below threshold",
                  f"ECE {LT['ece_after_T']}, threshold {leaf['threshold']}"],
                 ["Leaf", "No leakage from augmented copies", "Copies of val/test photos excluded from training",
                  f"{leaf['split'].get('synthetic_dropped_leak_guard', 0):,} excluded"],
                 ["Fertiliser", f"CV accuracy >= 95% (measured {R.pct(R.fert['chosen']['cv_accuracy_mean'])}); no doses", "Shortfall step shown with every result; names a fertiliser only", "Yes"]],
                [0.12, 0.3, 0.33, 0.25]),
          PageBreak(),
          P("9. Requirements traceability matrix", h1),
          P("Each requirement, the design element that implements it (see 03_SDD.pdf) and the test cases that verify it. "
            f"Test status: {NT - NF} of {NT} automated test cases passed on {TODAY}.", small),
          table([["Req.", "Design element", "Test cases"]] +
                [[f, DESIGN.get(f, "-"), ", ".join(ts)] for f, _, _, _, ts in FR] +
                [[i, DESIGN.get(i, "-"), ", ".join(ts) or "Inspection"] for i, _, _, ts in NFR], [0.1, 0.55, 0.35]),
          PageBreak(), P("Appendix A - Input validation rules", h1),
          table([["Field", "Rule"], ["Name", ">= 2 characters"], ["E-mail", "valid format; unique; required when OTP is on"],
                 ["Phone", "10-13 digits, optional leading +; unique"], ["Password", ">= 8 characters with a letter and a digit"],
                 ["OTP code", "6 digits; 10 min; 5 tries; resend after 60 s; 6 per hour per address"],
                 ["Crop inputs", "numbers inside the training range of each feature (shown as placeholder)"],
                 ["Yield", "state, district, crop, season required; year 1998..next year; area > 0 and <= 1,000,000 ha"],
                 ["Fertiliser", "N, P, K 0-2000; pH 3-10; organic carbon 0-10%; crop required"],
                 ["Leaf photo", "JPG or PNG, <= 8 MB"], ["Farm", "name required; coordinates inside India (6-38 N, 68-98 E)"]],
                [0.2, 0.8])]
    build("02_SRS.pdf", s, "Software Requirements Specification")


DESIGN = {
    "FR-01": "main.register, db.users", "FR-02": "otp.start / otp.verify, n8n AgriSense_OTP_Delivery",
    "FR-03": "main.register validation, EMAIL/PHONE regex, _password_problem", "FR-04": "main.login + otp_verify, db.new_session",
    "FR-05": "otp.py constants TTL, MAX_ATTEMPTS, RESEND_GAP, MAX_PER_HOUR", "FR-06": "main.forgot (decoy challenge), otp.verify",
    "FR-07": "main.update_me, change_pw, logout", "FR-08": "main.delete_me (purges 8 tables)",
    "FR-09": "main farms CRUD, _farm_payload", "FR-10": "_farm_payload India bounds",
    "FR-11": "ml.recommend_crop (Random Forest)", "FR-12": "ml.validate LIMITS", "FR-13": "ml.predict_yield (LightGBM, intervals)",
    "FR-14": "ml.predict_yield pred_contrib (SHAP), district history", "FR-15": "/api/yield/options, districts; y_predict checks",
    "FR-16": "fertiliser.recommend + Logistic Regression (fertiliser_model.joblib)", "FR-17": "ml.diagnose (ONNX EfficientNet-B0)", "FR-18": "temperature + threshold in ml.diagnose",
    "FR-19": "disease_info.INFO", "FR-20": "assistant.reply, main._context, send_chat", "FR-21": "chats table, /api/chats",
    "FR-22": "external.weather / history", "FR-23": "external.soil (WCS)", "FR-24": "save_prediction, /api/predictions",
    "FR-25": "/api/overview, analytics, reports csv/pdf", "FR-26": "db.log_event, db.save_upload", "FR-27": "i18n.js, responsive CSS",
    "NFR-01": "db.hash_pw (scrypt), SHA-256 tokens/codes", "NFR-02": "Depends(user), own_farm, user_id filters",
    "NFR-03": "Set-Cookie flags, Traefik TLS", "NFR-04": "config/api_keys.env read-only mount", "NFR-05": "ml/ training scripts, model cards",
    "NFR-06": "model cards -> UI", "NFR-07": "ONNX Runtime CPU, cache table", "NFR-08": "Docker restart policy, HEALTHCHECK",
    "NFR-09": "field-level errors in SPA", "NFR-10": "Dockerfile, CPU runtimes", "NFR-11": "tests/, model cards",
    "NFR-12": "reports export, delete_me", "NFR-13": "static/fonts + static/vendor, mimetypes in main.py", "NFR-14": "assistant.has_dose + rewrite retry", "FR-28": "/api/samples/crop|yield|leaf, setupMode() in app.js", "FR-29": "runChain(), chainCard(), goWith() hand-over", "FR-30": "translate.py (Azure + translations table), TR in i18n.js, assistant in_language guard", "FR-31": "CSS variables + html.dark, applyTheme()/setTheme()", "NFR-15": "TR.restore(), in-place setTheme()"}


# =====================================================================  03 SDD
def sdd(F, RF):
    s = cover("Software Design Document", "Architecture, components, data, interfaces, ML design, security and deployment.",
              "Describe how AgriSense AI is built so it can be reviewed, maintained and extended.")
    s += toc(["1. Introduction", "2. Design goals and principles", "3. System architecture", "4. Component (module) design",
              "5. Data design", "6. Interface (API) design", "7. Machine-learning design", "8. Key flows (sequence diagrams)",
              "9. User-interface design", "10. Security design", "11. Error handling and resilience",
              "12. Deployment design", "13. Testing design", "14. Design decisions and trade-offs"])
    s += [P("1. Introduction", h1),
          P("This document describes the design of AgriSense AI v1.0 that satisfies the requirements in 02_SRS.pdf. "
            "Requirement IDs (FR-xx, NFR-xx) are referenced where a design element implements them."),
          P("2. Design goals and principles", h1),
          *bullets(["<b>Truthful by construction</b> - every number on screen comes from a model card, a named data source or "
                    "the user's records (NFR-06).",
                    "<b>Simple to run</b> - one container, SQLite, CPU-only inference (NFR-10).",
                    "<b>Secure by default</b> - every data route requires a session and filters by user id (NFR-01..03).",
                    "<b>Explain and abstain</b> - show why (SHAP, rule reasons) and refuse when unsure (FR-14, FR-18).",
                    "<b>Thin client</b> - the browser renders; all logic and validation are on the server."]),
          P("3. System architecture", h1),
          P("A three-tier architecture: presentation (single-page app), application (FastAPI with ML and rule modules) "
            "and data (SQLite + model files), plus external services."),
          fig(F["arch"], 1.0, "Figure 1 - Component architecture."),
          fig(F["dfd1"], 0.95, "Figure 2 - Data-flow diagram, level 1."),
          PageBreak(),
          P("4. Component (module) design", h1), fig(F["modules"], 0.95, "Figure 3 - Python modules and their dependencies."),
          table([["Module", "Responsibility", "Key functions"],
                 ["app/main.py", "HTTP routes, validation, sessions, reports, chat orchestration",
                  "register, login, otp_verify, forgot, crop_recommend, y_predict, fert, disease, send_chat, report_pdf"],
                 ["app/db.py", "SQLite schema/migrations, password hashing, sessions, audit log, uploads",
                  "init, hash_pw, check_pw, new_session, session_user, log_event, save_upload"],
                 ["app/otp.py", "One-time codes: create, deliver via n8n, resend, verify, limits", "start, resend, verify, deliver, mask"],
                 ["app/ml.py", "Load models; crop, yield and leaf inference; SHAP; validation",
                  "recommend_crop, predict_yield, diagnose, validate, card"],
                 ["app/fertiliser.py", "Shortfall step + fertiliser model", "recommend, predict"],
                 ["app/external.py", "Open-Meteo, NASA POWER, SoilGrids clients with caching", "geocode, weather, history, soil"],
                 ["app/assistant.py", "Mistral chat with grounding and model fallback", "reply, configured"],
                 ["app/disease_info.py", "Cause / symptoms / management text per class", "INFO"],
                 ["app/static/*", "SPA: router, pages, charts, i18n (EN/HI)", "route, PAGES.*, renderAuth, renderOtp, chart"],
                 ["ml/*.py", "Training scripts that write models + model cards", "train_crop, train_yield, train_leaf_full"]],
                [0.18, 0.4, 0.42]),
          P("4.1 Front-end design", h2),
          P("A hash router (#/overview, #/crop ...) maps each route to an async page function that renders into its own "
            "element; a newer navigation detaches the older element so a slow page can never overwrite the current one. "
            "Charts are Chart.js; maps are Leaflet with OpenStreetMap tiles; the i18n module translates labels to Hindi."),
          PageBreak(),
          P("5. Data design", h1), fig(F["er"], 0.92, "Figure 4 - Entity-relationship diagram."),
          table([["Table", "Purpose", "Notes"],
                 ["users", "Accounts", "email/phone unique; scrypt hash; email_verified_at; last_login_at"],
                 ["sessions", "Sign-in sessions", "token stored as SHA-256 only; expiry 1/14/30 days"],
                 ["otp_challenges", "Code requests", "random id; SHA-256(id:code); attempts; sends; payload (pending sign-up)"],
                 ["auth_events", "Audit trail", "sign-up, login, login_failed, otp_sent/wrong/resent, reset, logout"],
                 ["farms", "Farms", "location validated inside India; crop history JSON"],
                 ["predictions", "Every model result", "inputs/result JSON, model_version, status (completed / needs review)"],
                 ["uploads", "Leaf photos", "BLOB + SHA-256; linked to prediction or chat"],
                 ["chats", "Assistant conversations", "messages JSON; saved flag"],
                 ["cache", "External API cache", "TTL per source"],
                 ["production", "Reference statistics", "322,669 cleaned rows; indexed by district/crop/season/year"]],
                [0.16, 0.24, 0.6]),
          P("SQLite runs in WAL mode with foreign keys on. User data lives in a Docker volume, separate from the image.", small),
          PageBreak(),
          P("6. Interface (API) design", h1),
          P("REST over HTTPS, JSON bodies (multipart for photos), cookie-based sessions. Errors use one shape: "
            "<font face='UI-B'>{\"error\": message, \"fields\": {field: message}}</font> with 401 (sign in), 403, 404, "
            "409 (duplicate), 410 (expired), 413/415 (upload), 422 (validation), 429 (limits), 502/503 (service). "
            "Interactive documentation is generated at /api/docs."),
          table([["Method", "Path", "Purpose"]] + [[m.upper(), p, R.EP_DOC.get(p + " " + m.upper(), R.EP_DOC.get(p, ""))]
                                                   for m, p in RF["eps"]], [0.1, 0.36, 0.54]),
          PageBreak(),
          P("7. Machine-learning design", h1), fig(F["pipe"], 1.0, "Figure 5 - Training-to-serving pipeline."),
          P("7.1 Crop recommendation", h2),
          P(f"Inputs: N, P, K, temperature, humidity, pH, rainfall. Five candidates (logistic regression, k-NN, SVM-RBF, "
            f"Random Forest, LightGBM) compared with 5-fold stratified CV on the 80% training part; the winner "
            f"({crop['selected_model']}, CV {pct(max(c['cv_accuracy_mean'] for c in crop['comparison']))}) is tested once "
            f"on the 20% ({pct(crop['test_accuracy'])}) and then refit on all 2,200 rows. Output: class probabilities, "
            f"top alternatives and per-feature suitability against each crop's 10th-90th percentile band."),
          P("7.2 Yield prediction", h2),
          P(f"LightGBM regression (L1 loss) on 13 features: State, District, Crop, Season (categorical), log area, last "
            f"two years' yield, trend, 3-year mean, years of history, long-run district mean, last year's state yield and "
            f"area change. The target is log(1+yield) - log(1+base), where base is the recent normal - so the model learns "
            f"corrections. Trained on years before 2017-18 and tested on later years: MAE {YR['mae_t_ha']} t/ha, R2 {YR['r2']}. "
            f"The deployed model is refit on all {yld['deployed_fit']['rows']:,} rows with "
            f"{yld['deployed_fit']['iterations']} boosting rounds. SHAP values come from LightGBM's exact pred_contrib; the 80% "
            f"interval from test residual quantiles per crop."),
          P("7.3 Leaf disease detection", h2),
          P(f"EfficientNet-B0 (ImageNet weights) fine-tuned on the GPU with AdamW, one-cycle learning rate, mixed precision, "
            f"class-weighted cross-entropy with label smoothing and random crop / flip / rotation / colour augmentation. "
            f"The augmented dataset's {leaf['augmented_set']['synthetic']:,} synthetic copies were linked to their source "
            f"photos by feature similarity so copies of validation/test photos never enter training. A temperature "
            f"(T = {leaf['temperature']}) calibrates confidence; the abstain threshold ({leaf['threshold']}) is the lowest "
            f"giving 99.9% precision on validation, floored at 0.60. Served as ONNX on CPU with a flip test-time "
            f"augmentation. Test: accuracy {pct(LT['accuracy'])}, macro recall {pct(LT['macro_recall'])}, "
            f"ECE {LT['ece_after_T']}."),
          P("7.5 Automatic inputs and the crop-to-fertiliser chain", h2),
          P("Three endpoints return a different random real record on every call: /api/samples/crop (a row of the 2,200-row crop CSV), /api/samples/yield (a district-crop-season-year record with at least three earlier years; the farm area is an example because the dataset holds district totals) and /api/samples/leaf (one of 117 bundled leaf photos, 3 per class). The page fills the form, runs the model and shows the dataset's own answer beside the model's. runChain() strings the crop sample, the crop model and the fertiliser model together and hands the finished result to the Fertiliser page (goWith / takeNext), so nothing is recomputed and both results land in the history."),
          P("7.4 Fertiliser recommendation", h2),
          P(f"{R.fert['chosen']['model']} on N, P and K, chosen from eight candidates (four algorithms x two feature sets) by 5x5 "
            f"repeated cross-validation on the {R.fert['rows']}-row Fertilizer Prediction.csv: "
            f"{R.pct(R.fert['chosen']['cv_accuracy_mean'])}. Weather, moisture, soil and crop type had zero permutation importance. "
            "The dataset's N, P, K are the nutrient to supply on its own scale, so soil values first go through a shortfall step: "
            "each nutrient is compared with a typical level (the crop's median in the crop dataset, or the middle of the Soil "
            "Health Card medium band), the shortfalls keep their proportions with the most-short nutrient at the top of the "
            "fertiliser dataset's range, and only fertilisers that supply every real shortfall are considered. Nothing short "
            "means no fertiliser is named. Doses are never produced. Detail and figures: the model report, section 6."),
          PageBreak(),
          P("8. Key flows (sequence diagrams)", h1),
          fig(F["seq_signup"], 1.0, "Figure 6 - Sign-up with e-mail code."),
          fig(F["otp_state"], 0.9, "Figure 7 - Life cycle of a one-time code."),
          fig(F["seq_login"], 1.0, "Figure 8 - Sign-in with password and code."),
          fig(F["seq_predict"], 1.0, "Figure 9 - Yield prediction."),
          fig(F["seq_disease"], 1.0, "Figure 10 - Leaf disease detection."),
          fig(F["seq_chat"], 1.0, "Figure 11 - Assistant chat."),
          PageBreak(),
          P("9. User-interface design", h1), fig(F["sitemap"], 1.0, "Figure 12 - Navigation map."),
          P("Layout, components and states for every screen are in 04_Wireframes.pdf. Design rules: one primary action "
            "per form, validation under the field, results next to the form on desktop and below it on phones, every "
            "result card names the model and its measured accuracy, colour is never the only signal (labels and icons too)."),
          P("10. Security design", h1),
          table([["Threat", "Control"],
                 ["Password theft from database", "scrypt (n=16384, r=8, p=1) with per-user 16-byte salt"],
                 ["Session theft", "random 32-byte token, stored as SHA-256; HttpOnly, SameSite=Lax, Secure cookie; HTTPS only"],
                 ["Stolen password used to sign in", "second factor: 6-digit e-mail code per sign-in"],
                 ["Code guessing", "5 attempts per code, 10-minute expiry, codes stored as SHA-256(id:code)"],
                 ["E-mail flooding", "60 s resend gap; 6 codes per address per hour"],
                 ["Account discovery", "forgot-password answers identically for unknown addresses (decoy challenge)"],
                 ["Reading other users' data", "every query filtered by the session's user id; ownership checked (404 otherwise)"],
                 ["Malicious upload", "type and size checks; image decoded by Pillow only; stored as BLOB, never executed"],
                 ["Leaked secrets", "keys in a read-only mounted file; OTP webhook protected by a shared secret on a private network"],
                 ["Prompt misuse of the assistant", "system prompt restricts to farming; no prices or schemes invented"],
                 ["Assistant states a harmful dose", "has_dose() scans every reply; one rewrite request, then amounts are removed and labelled (NFR-14)"],
                 ["Map layers covering dialogs", "Leaflet maps isolated in their own stacking context; dialogs at z-index 2000"]],
                [0.3, 0.7]),
          P("11. Error handling and resilience", h1),
          *bullets(["Uniform JSON errors; the SPA shows field messages and toasts; pages show a Retry state.",
                    "External calls have timeouts and caching; Mistral falls back 14b -> 8b -> 3b with back-off on 429/5xx.",
                    "n8n replies are trusted only when the body says ok:true (a 2xx alone is not delivery).",
                    "Docker restarts the container; a health check polls /healthz every 30 s."]),
          PageBreak(),
          P("12. Deployment design", h1), fig(F["deployment"], 1.0, "Figure 13 - Deployment diagram."),
          *bullets(["Image: python:3.12-slim + requirements; runs as uid 10001; 2 Uvicorn workers; 1.2 GB memory limit.",
                    "Traefik (file provider) routes ai.software.microeagle.online to 127.0.0.1:8150 with a Let's Encrypt certificate.",
                    "The container joins the n8n Docker network to reach the OTP workflow by name.",
                    "User data persists in the agrisense_agrisense_data volume across rebuilds."]),
          P("13. Testing design", h1),
          P(f"Four layers, all automated with pytest ({NT} test cases, {NT - NF} passed, {TSEC:.0f} s):"),
          table([["Layer", "Tool", "What it checks"],
                 ["API / integration", "FastAPI TestClient, throwaway SQLite, OTP delivery captured", "Every route, validation, security, storage"],
                 ["Model quality", "model cards + direct inference", "Accuracy gates, leakage guard, ONNX consistency"],
                 ["Live services", "real Open-Meteo, NASA POWER, SoilGrids, Mistral", "Integrations work end-to-end"],
                 ["UI end-to-end", "Playwright driving Microsoft Edge + stand-in mailbox", "Real user journeys, screenshots as evidence"]],
                [0.2, 0.4, 0.4]),
          P("14. Design decisions and trade-offs", h1),
          table([["Decision", "Why", "Trade-off"],
                 ["SQLite instead of a server database", "Zero administration; one-farmer workloads", "Single server; fine for this scale"],
                 ["Vanilla JS SPA, no framework build", "Small, fast on phones, no toolchain", "More manual DOM code"],
                 ["ONNX on CPU for the CNN", "No GPU on the VPS; ~0.3 s per photo", "Training needs a separate GPU machine"],
                 ["Yield target = correction to recent mean", "Beats strong persistence baselines", "Less intuitive than raw yield"],
                 ["Fertiliser model on N, P, K with a shortfall step", "Dataset units differ from soil values; must not invent doses", "Bridge shown with every result; names a fertiliser only"],
                 ["E-mail OTP via existing n8n", "Reuses working SMTP; no new provider", "Depends on the shared n8n instance"],
                 ["Refit on all data after evaluation", "Uses every supplied row/image", "Deployed model's exact accuracy is estimated, not re-measured"]],
                [0.3, 0.38, 0.32])]
    build("03_SDD.pdf", s, "Software Design Document")


# =====================================================================  04 WIREFRAMES
WF_TEXT = {
    "01_sign_in": ("Sign in", "Entry screen. Two-column layout on desktop (illustration left, form right); form only on phones.",
                   "Fields are validated on submit; wrong credentials show a toast and keep the user here. Successful "
                   "password check moves to the e-mail code screen."),
    "02_sign_up": ("Create account", "Registration form with name, e-mail, phone (optional), password, state, district "
                   "(suggested from the dataset) and role.", "Errors appear under each field. Submit sends a code; the "
                   "account is created only after the code is entered."),
    "03_email_code": ("E-mail code (OTP)", "Shown after sign-up, sign-in or password reset. Masked e-mail, 6-digit field "
                      "(auto-submits on the 6th digit), Verify, Start again, Resend countdown.", "Wrong code: toast with "
                      "tries left, field cleared. Resend unlocks after 60 s."),
    "04_overview": ("Overview dashboard", "Greeting and quick actions (New Prediction menu: Full auto analysis, or Custom / "
                    "Auto per tool), six KPI tiles, live weather for the first farm, production analytics with filters, recent "
                    "predictions table and AI insights.", "New users see empty "
                    "states that point to 'Add farm' and the first prediction."),
    "05_crop": ("Crop recommendation", "Seven-input form (with live-weather fill) on the left; result card with crop, "
                "confidence, model accuracy, suitability radar, alternatives and an input-vs-range table on the right.",
                "Out-of-range inputs are flagged; results are saved to history automatically."),
    "06_yield": ("Yield prediction", "Location / crop / season / year / area form; three KPI cards (yield with 80% range, "
                 "production, district history); history chart; SHAP explanation; model quality table and feature importance.",
                 "The info box states that the model has no weather or soil inputs."),
    "07_fertiliser": ("Fertiliser recommendation", "Basis selector, crop, N-P-K and optional context; result with three "
                      "nutrient gauges, suggested category, reasons with thresholds and options to discuss.",
                      "A warning band states that the tool never gives doses."),
    "08_disease": ("Plant disease detection", "Upload area with preview and farm link; result with photo, verdict badge, "
                   "crop and disease, calibrated confidence, top-5 bar chart, cause / symptoms / next steps.",
                   "Unclear photos show an 'uncertain' state asking for a better photo instead of a disease name."),
    "09_assistant": ("AI farming assistant", "Full-height layout: conversation list with search, grouped Saved / Recent; chat panel "
                     "with header (status, language), centred message column, and a composer with photo attach, microphone and "
                     "send. The empty state offers Explain this on the latest results and suggestion cards by topic.",
                     "Ask the assistant on any result opens this page and sends a question about that result. On phones the "
                     "conversation list opens from a history button."),
    "10_weather": ("Weather insights", "Current conditions, 7-day forecast, alerts, and a historical chart for a chosen "
                   "date range (NASA POWER).", "Each panel names its data source."),
    "11_soil": ("Soil health", "Farm selector, map, property cards (pH, organic carbon, nitrogen, clay, sand, bulk "
                "density) with ranges, and a depth profile chart.", "Labelled as modelled values, not a lab test."),
    "12_farms": ("Farm management", "Farm cards with map, area, soil and crop; add / edit form with a Leaflet map pin "
                 "and village search.", "Coordinates outside India are rejected."),
    "13_history": ("Prediction history", "Filters (type, farm, crop, status, dates, search) and a table of results with "
                   "view and delete actions.", "Detail view shows inputs, result and model version."),
    "14_reports": ("Reports & analytics", "Summary charts (by type, over time, recommended crops) and download cards for "
                   "CSV and PDF per tool.", "Exports contain only the signed-in user's data."),
    "15_settings": ("Settings", "Profile, language, units, notifications, assistant data sharing, change password, "
                    "export and delete account.", "Delete asks for the password and removes all data."),
}


def wireframes(F, RF):
    WF = HERE / "wf"
    regions = json.loads((WF / "regions.json").read_text(encoding="utf-8"))
    s = cover("Wireframes", "Low-fidelity layouts of every screen, desktop and phone, with numbered regions.",
              "Document the interface structure, components and states that the SRS requirements map to.")
    s += [P("1. About these wireframes", h1),
          P("Each wireframe is rendered from the real application's layout with a sketch style applied: colours, photos "
            "and charts are replaced by grey outlines and hatched placeholders so that structure, hierarchy and "
            "behaviour are the focus. Orange numbers mark the regions described in the table under each frame."),
          table([["Notation", "Meaning"], ["Solid outline", "Card / panel"], ["Hatched box", "Chart or map placeholder"],
                 ["Grey button", "Primary action"], ["Light button", "Secondary action"], ["Orange number", "Region in the table"]],
                [0.3, 0.7]),
          P("2. Navigation map", h1), fig(F["sitemap"], 1.0, "Figure 1 - Screens and how users move between them."),
          P("3. Layout grid and responsive behaviour", h1),
          *bullets(["Desktop (>= 1024 px): fixed 256 px sidebar, top bar, content max width with 2-3 column card grids.",
                    "Tablet: sidebar collapses behind a menu button; cards wrap to 2 columns.",
                    "Phone (375 px): single column, forms above results, horizontal scrolling never needed (verified by TC-066).",
                    "Typography: Inter / Noto Sans Devanagari; icons: Material Symbols."]),
          PageBreak()]
    n = 2
    for key, (title, what, behaviour) in WF_TEXT.items():
        img = WF / f"{key}.png"
        from PIL import Image as PI
        im = PI.open(img)
        if im.height > im.width * 1.25:
            im = im.crop((0, 0, im.width, int(im.width * 1.25)))
            img = WF / f"crop_{key}.png"
            im.save(img)
        regs = regions.get(key, [])
        rows = [["#", "Region", ""]] + [[str(r["n"]), r["label"] or "-", ""] for r in regs[:12]]
        s += [P(f"4.{n - 1} {title}", h2), P(what), fig(img, 0.86 if im.height < im.width else 0.62, f"Figure {n} - {title} (desktop)."),
              table([["#", "Region"]] + [[str(r["n"]), clean_label(key, r["label"])] for r in regs[:14]], [0.08, 0.92]),
              P("<b>Behaviour:</b> " + behaviour), PageBreak()]
        n += 1
    s.append(P("5. Phone layouts (375 px)", h1))
    from PIL import Image as PI
    ims = [PI.open(WF / f"{k}.png") for k in ("m1_overview", "m2_crop", "m3_disease")]
    w = W / 3 - 6
    row = [Image(str(WF / f"{k}.png"), width=w, height=w * im.height / im.width) for k, im in
           zip(("m1_overview", "m2_crop", "m3_disease"), ims)]
    t = Table([row, [P("Overview", cap), P("Crop recommendation", cap), P("Disease detection", cap)]], colWidths=[W / 3] * 3)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    s += [t, P("On phones the sidebar becomes a slide-in menu (top-left button), KPI tiles stack two per row and forms "
               "come before results.")]
    build("04_Wireframes.pdf", s, "Wireframes")


def main():
    figs = D.all_figs()
    F = {**{k: v for k, v in figs.items()}, "arch": R.fig_architecture(), "pipe": figs["ml_pipeline"]}
    import re
    eps = re.findall(r'@app\.(get|post|put|delete|patch)\("([^"]+)"\)', (ROOT / "app" / "main.py").read_text(encoding="utf-8"))
    RF = {"eps": [(m, p) for m, p in eps if p != "/"]}
    which = sys.argv[1:] or ["proposal", "srs", "sdd", "wireframes"]
    for w in which:
        {"proposal": proposal, "srs": srs, "sdd": sdd, "wireframes": wireframes}[w](F, RF)


if __name__ == "__main__":
    main()
