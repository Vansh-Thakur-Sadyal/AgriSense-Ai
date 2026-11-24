"""Software Engineering (CS 301) presentation: 15 slides that follow the course handout units 1 to 17,
each applied to the AgriSense AI project. Reuses the slide helpers and look of build_aiml_ppt.py
(the department's sample evaluation deck).
Usage: python build_se_ppt.py <sample.pptx> <out.pptx>"""
from pathlib import Path

_src = (Path(__file__).resolve().parent / "build_aiml_ppt.py").read_text(encoding="utf-8").splitlines()
_end = next(i for i, ln in enumerate(_src) if ln.startswith("cr, fe, yi, lf ="))
exec(compile("\n".join(_src[:_end]), "build_aiml_ppt_helpers", "exec"))  # helpers, palette, data, opened deck

import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "docs" / "submission"))  # noqa: F821
from spec import FR, NFR  # noqa: E402

UML = ROOT / "docs" / "submission" / "figs"  # noqa: F821
WFR = ROOT / "docs" / "submission" / "wf"  # noqa: F821
COURSE_SE = "Software Engineering (CS 301)"
FAC_SE = "Dr. Shreyansh Sharma"
GREEN_OK = RGBColor(0x2E, 0x7D, 0x4F)  # noqa: F821


def unit_tag(s, text):
    """Small 'Unit n' label at top right, linking the slide to the course handout."""
    textbox(s, 9.9, 0.38, 2.9, 0.4, [text], 12, TEAL, align=PP_ALIGN.RIGHT)  # noqa: F821


def flow(s, labels, x, y, w, h, gap=0.3, fill=None, size=13, dark=()):
    """Row of boxes joined by arrows."""
    bw = (w - gap * (len(labels) - 1)) / len(labels)
    for i, t in enumerate(labels):
        bx = x + i * (bw + gap)
        d = i in dark
        box(s, bx, y, bw, h, NAVY if d else (fill or TINT))  # noqa: F821
        textbox(s, bx + 0.05, y, bw - 0.1, h, [t], size, WHITE if d else NAVY, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
        if i:
            arrow(s, bx - gap + 0.03, y + h / 2, bx - 0.03, y + h / 2)  # noqa: F821


# ================================================================== 1 title
s = prs.slides.add_slide(BLANK); N[0] += 1  # noqa: F821
textbox(s, 1.27, 0.56, 7.45, 0.57, ["**FINAL PROJECT EVALUATION**"], 28)  # noqa: F821
textbox(s, 1.27, 1.44, 7.6, 1.3, ["**AgriSense AI: A Smart Farming Assistant**",
                                  "A software engineering view: process, requirements, design, testing and quality"], 24, NAVY, after=4)  # noqa: F821
s.shapes[-1].text_frame.paragraphs[1].runs[0].font.size = Pt(18)  # noqa: F821
s.shapes[-1].text_frame.paragraphs[1].runs[0].font.color.rgb = GREY  # noqa: F821
textbox(s, 1.52, 3.3, 7.3, 1.3, ["**Presented By**"] + [f"{n}  |  {e}" for n, e in C.TEAM], 16, after=3)  # noqa: F821
textbox(s, 1.52, 4.85, 7.3, 0.45, [f"**Programme:** B.Tech CSE, Semester V, Section {C.SECTION}"], 16)  # noqa: F821
textbox(s, 1.52, 5.35, 7.3, 0.45, [f"**Course:** {COURSE_SE}, Session {C.YEAR}"], 16)  # noqa: F821
textbox(s, 1.52, 5.85, 7.3, 0.45, [f"**Faculty:** {FAC_SE}"], 16)  # noqa: F821
image(s, HERE / "niit_logo.png", 8.9, 0.5, 3.9, 1.3)  # noqa: F821
image(s, AND / "home.png", 9.75, 2.1, 2.3, 4.9, border=True)  # noqa: F821

# ================================================================== 2 unit 1
s = slide("1. Foundations: Software Engineering in AgriSense")  # noqa: F821
unit_tag(s, "Unit 1")
textbox(s, 0.6, 1.3, 6.0, 0.4, ["**Programming vs software engineering**"], 18, NAVY)  # noqa: F821
table(s, [["Programming only", "What we did as software engineering"],  # noqa: F821
          ["Write a model script", "Requirements, design, code, tests, deployment, maintenance"],
          ["Works on my laptop", "Docker image runs the same on any server"],
          ["Check output by eye", "88 automated tests traced to requirements"],
          ["One developer, no docs", "3-person team, Proposal, SRS, SDD, test reports"]],
      0.6, 1.75, 6.1, [2.4, 3.7], 13, 0.5)
textbox(s, 0.6, 4.5, 6.1, 0.4, ["**Main SE activities**"], 18, NAVY)  # noqa: F821
flow(s, ["Specify", "Design", "Build", "Validate", "Evolve"], 0.6, 5.0, 6.1, 0.8, gap=0.25, size=13)
textbox(s, 0.6, 6.0, 6.1, 0.9, ["Software engineering is the disciplined, measured way of building software that "
                                "works, can be trusted and can be changed later."], 13, GREY)  # noqa: F821
textbox(s, 7.1, 1.3, 5.7, 0.4, ["**Key stakeholders**"], 18, NAVY)  # noqa: F821
stake = [("Farmers", "main users: crop, fertiliser, disease answers"), ("Extension officers", "check many farmers' cases"),
         ("Students / researchers", "see how models were built"), ("Development team", "build, test and maintain"),
         ("Faculty evaluators", "review documents and results"), ("Data and service providers", "data.gov.in, Kaggle, Mendeley, Mistral, Azure")]
for i, (h_, t_) in enumerate(stake):
    y = 1.8 + i * 0.85
    circle_num(s, 7.1, y + 0.08, i + 1, 0.5)  # noqa: F821
    textbox(s, 7.75, y, 5.1, 0.8, [f"**{h_}**", t_], 13, after=0)  # noqa: F821

# ================================================================== 3 unit 2
s = slide("2. Well-Engineered Software: Quality Attributes")  # noqa: F821
unit_tag(s, "Unit 2")
table(s, [["Attribute", "How AgriSense meets it"],  # noqa: F821
          ["Functionality", f"{len(FR)} functional requirements: crop, yield, fertiliser, disease, assistant, weather, soil, history"],
          ["Usability", "15 languages, dark theme, field-level error messages, works at 375 px phone width"],
          ["Reliability", "Auto-restart container, /healthz check, 0 errors in 32,061 load-test requests"],
          ["Security", "scrypt passwords, e-mailed sign-in codes, HttpOnly cookies, HTTPS"],
          ["Efficiency", f"100 users at once with 95% of answers under 2 s on 2 CPU cores"],
          ["Maintainability", "Separate modules, model cards, one API for web and app"],
          ["Portability", "Docker image; models run on CPU (ONNX, scikit-learn, LightGBM)"]],
      0.6, 1.3, 7.3, [1.9, 5.4], 13, 0.52, bold_first_col=True)
textbox(s, 8.2, 1.3, 4.6, 0.4, ["**ETVX: model-training stage**"], 17, NAVY)  # noqa: F821
for i, (k, v) in enumerate([("Entry", "cleaned data, split fixed"), ("Task", "train candidates, cross-validate"),
                            ("Validation", "test vs baseline, write model card"), ("Exit", "beats baseline, tests pass")]):
    y = 1.8 + i * 0.82
    box(s, 8.2, y, 1.5, 0.68, NAVY)  # noqa: F821
    textbox(s, 8.2, y, 1.5, 0.68, [f"**{k}**"], 14, WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
    box(s, 9.8, y, 3.0, 0.68)  # noqa: F821
    textbox(s, 9.9, y, 2.85, 0.68, [v], 13, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
card(s, 8.2, 5.2, 4.6, 1.65, "Failure causes we avoided",
     ["Unclear requirements: written SRS first", "Untested changes: 88 automated tests", "Hidden numbers: every figure from a model card"], 12)  # noqa: F821

# ================================================================== 4 unit 3
s = slide("3. Project Governance: Milestones and Ethics")  # noqa: F821
unit_tag(s, "Unit 3")
image(s, UML / "gantt.png", 0.55, 1.25, 6.9, 2.9)  # noqa: F821
textbox(s, 0.6, 4.25, 6.8, 0.4, ["**Core deliverables**"], 17, NAVY)  # noqa: F821
flow(s, ["Proposal", "SRS", "SDD", "Wireframe", "Code", "Tests"], 0.6, 4.75, 6.8, 0.7, gap=0.2, size=12)
textbox(s, 0.6, 5.65, 6.8, 1.3, ["Each milestone ended with a reviewed document or a working, tested increment; "
                                 "the guideline's folder structure (01 to 07) holds them."], 13, GREY)  # noqa: F821
textbox(s, 7.8, 1.3, 5.0, 0.4, ["**Professional and ethical responsibilities**"], 17, NAVY)  # noqa: F821
eth = [("Honesty", "No invented numbers; limits stated on every result"),
       ("Safety", "The assistant never gives fertiliser or pesticide doses"),
       ("Privacy", "Users can export and delete all their data"),
       ("Security", "Keys never in code or the browser"),
       ("Licences", "Data used under GODL and CC BY 4.0, sources cited")]
for i, (h_, t_) in enumerate(eth):
    y = 1.8 + i * 1.0
    box(s, 7.8, y, 5.0, 0.88)  # noqa: F821
    textbox(s, 7.95, y + 0.06, 4.8, 0.8, [f"**{h_}:** {t_}"], 13, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821

# ================================================================== 5 unit 4
s = slide("4. SDLC Phases and Feasibility Study")  # noqa: F821
unit_tag(s, "Unit 4")
phases = [("Requirements", "Proposal, SRS"), ("Design", "SDD, ER, wireframes"), ("Implementation", "FastAPI, web, Android"),
          ("Testing", "88 tests, load test"), ("Deployment", "Docker, VPS, HTTPS"), ("Maintenance", "bug fixes, new features")]
for i, (h_, t_) in enumerate(phases):
    x = 0.6 + i * 2.05
    box(s, x, 1.35, 1.85, 1.3, NAVY if i in (0, 3) else TINT)  # noqa: F821
    dark = i in (0, 3)
    textbox(s, x + 0.05, 1.42, 1.75, 0.45, [f"**{h_}**"], 13, WHITE if dark else NAVY, align=PP_ALIGN.CENTER)  # noqa: F821
    textbox(s, x + 0.05, 1.9, 1.75, 0.7, [t_], 12, WHITE if dark else INK, align=PP_ALIGN.CENTER)  # noqa: F821
    if i:
        arrow(s, x - 0.17, 2.0, x - 0.03, 2.0)  # noqa: F821
textbox(s, 0.6, 2.75, 12.1, 0.35, ["Artifacts produced at each phase are shown under its name."], 12, GREY)  # noqa: F821
textbox(s, 0.6, 3.2, 6.0, 0.4, ["**Feasibility study**"], 17, NAVY)  # noqa: F821
table(s, [["Type", "Finding"],  # noqa: F821
          ["Technical", "Python ML on CPU; GPU needed only to train the leaf model"],
          ["Economic", "Open-source stack, free public data, one small VPS"],
          ["Operational", "Farmers use phones; 15 languages; e-mail sign-in"],
          ["Schedule", "About 14 weeks in iterative increments"]],
      0.6, 3.65, 6.0, [1.5, 4.5], 13, 0.55, bold_first_col=True)
textbox(s, 6.9, 3.2, 5.9, 0.4, ["**Risks and mitigation**"], 17, NAVY)  # noqa: F821
table(s, [["Risk", "Mitigation"],  # noqa: F821
          ["Poor or small datasets", "Baselines, CV, limits shown"],
          ["Outside API down", "Cache, fallback model, honest message"],
          ["Over-confident AI", "Calibration and 0.95 threshold"],
          ["Account misuse", "Two-step sign-in, rate limits"],
          ["Too many users", "Load test; scale plan"]],
      6.9, 3.65, 5.9, [2.6, 3.3], 13, 0.55)

# ================================================================== 6 units 5-6
s = slide("5. Process Models and Our Choice")  # noqa: F821
unit_tag(s, "Units 5 and 6")
table(s, [["Model", "Best when", "Limitation", "Fit here"],  # noqa: F821
          ["Waterfall", "Requirements fixed and clear", "Late feedback, costly change", "Low"],
          ["V model", "Each phase needs a matching test", "Still rigid", "Partly (test planning)"],
          ["Prototyping", "Users unsure of the UI", "Prototype mistaken for product", "Used for UI design"],
          ["RAD", "Fast delivery, reusable parts", "Needs skilled team, small scope", "Medium"],
          ["Spiral", "High risk, large projects", "Heavy risk analysis", "Medium"],
          ["Iterative / incremental", "Unknowns early, value in steps", "Needs good integration", "Chosen"]],
      0.6, 1.3, 7.6, [1.9, 2.3, 2.2, 1.2], 12, 0.52, bold_first_col=True)
row = s.shapes[-1].table.rows[6]
for c in row.cells:
    c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xD5, 0xEE, 0xE0)  # noqa: F821
card(s, 8.5, 1.3, 4.3, 2.75, "Why iterative incremental",
     ["Model accuracy was unknown at the start", "Each increment was working and tested",
      "Features added in stages: models, API, dashboard, security, app"], 13)
textbox(s, 8.5, 4.25, 4.3, 0.4, ["**Our increments**"], 16, NAVY)  # noqa: F821
for i, t_ in enumerate(["Data + 4 models", "API + database", "Web dashboard", "Security + OTP", "Android app"]):
    y = 4.7 + i * 0.44
    circle_num(s, 8.5, y, i + 1, 0.36)  # noqa: F821
    textbox(s, 9.0, y - 0.02, 3.8, 0.4, [t_], 13)  # noqa: F821

# ================================================================== 7 unit 7
s = slide("6. Agile and Lean Ideas in Practice")  # noqa: F821
unit_tag(s, "Unit 7")
textbox(s, 0.6, 1.3, 7.2, 0.4, ["**Kanban board: snapshot near the end of the project**"], 17, NAVY)  # noqa: F821
cols = [("To do", ["Offline mode", "Hindi voice input", "Field-photo testing"]),
        ("In progress", ["Evaluation slides"]),
        ("Testing", ["Fertiliser model", "Welcome screen"]),
        ("Done", ["Crop, yield, leaf models", "Web dashboard", "Android app", "Load test"])]
for i, (h_, items) in enumerate(cols):
    x = 0.6 + i * 1.83
    box(s, x, 1.8, 1.7, 0.5, NAVY)  # noqa: F821
    textbox(s, x, 1.8, 1.7, 0.5, [f"**{h_}**"], 13, WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
    for j, it in enumerate(items):
        box(s, x, 2.4 + j * 0.78, 1.7, 0.68, WHITE, line=SOFT)  # noqa: F821
        textbox(s, x + 0.05, 2.4 + j * 0.78, 1.6, 0.68, [it], 12, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
textbox(s, 0.6, 5.65, 7.2, 1.2, ["Work flowed left to right with little work in progress at a time; a card moved to "
                                 "Done only when its tests passed."], 13, GREY)  # noqa: F821
card(s, 8.15, 1.3, 4.65, 1.75, "Agile Manifesto values we followed",
     ["Working software over long documents between increments", "Responding to change: features added after feedback"], 12)
card(s, 8.15, 3.2, 4.65, 1.75, "Lean: waste removed",
     ["Unneeded 'Ask' buttons cut to the two that help", "Unused features dropped from the fertiliser model"], 12)
card(s, 8.15, 5.1, 4.65, 1.75, "Test-first habit (TDD idea)",
     ["Each change came with a test case ID", "All 88 tests rerun before every deployment"], 12)

# ================================================================== 8 unit 8
s = slide("7. SRS: Requirements Specification")  # noqa: F821
unit_tag(s, "Unit 8")
textbox(s, 0.6, 1.3, 4.0, 0.4, ["**SRS structure**"], 17, NAVY)  # noqa: F821
for i, t_ in enumerate(["Introduction and scope", "Overall description, users", f"{len(FR)} functional requirements",
                        f"{len(NFR)} non-functional requirements", "Interfaces, use cases", "Data and acceptance criteria"]):
    y = 1.78 + i * 0.6
    circle_num(s, 0.6, y, i + 1, 0.42)  # noqa: F821
    textbox(s, 1.15, y - 0.02, 3.5, 0.5, [t_], 13)  # noqa: F821
textbox(s, 0.6, 5.5, 4.0, 1.4, ["Good requirements are correct, unambiguous, complete, consistent, verifiable and traceable."], 13, GREY)  # noqa: F821
fr = {f[0]: f for f in FR}
nf = {n[0]: n for n in NFR}
table(s, [["ID", "Type", "Requirement (from our SRS)"],  # noqa: F821
          ["FR-04", "Functional", fr["FR-04"][2]],
          ["FR-17", "Functional", fr["FR-17"][2][:110] + "..."],
          ["NFR-01", "Non-functional", nf["NFR-01"][2]],
          ["NFR-07", "Non-functional", nf["NFR-07"][2][:105] + "..."]],
      4.95, 1.3, 7.85, [0.9, 1.6, 5.35], 12, 0.62)
textbox(s, 4.95, 4.55, 7.8, 0.4, ["**Traceability: one requirement end to end**"], 16, NAVY)  # noqa: F821
flow(s, ["FR-05 code limits", "otp.py: TTL, MAX_ATTEMPTS", "TC-005, TC-006 tests", "Pass"], 4.95, 5.05, 7.85, 0.95, gap=0.28, size=12, dark=(3,))

# ================================================================== 9 unit 9
s = slide("8. Requirements Engineering")  # noqa: F821
unit_tag(s, "Unit 9")
textbox(s, 0.6, 1.3, 6.0, 0.4, ["**Elicitation and analysis**"], 17, NAVY)  # noqa: F821
textbox(s, 0.6, 1.75, 6.0, 2.6, [
    "- **Stakeholder analysis:** farmers (high interest, low tech), officers, students, faculty.",
    "- **Document study:** Soil Health Card bands, government yield data, the course guideline.",
    "- **Scenario walkthroughs:** stepping through how a farmer chooses a crop and a fertiliser today.",
    "- **Prototype reviews:** wireframes checked before coding.",
], 14, bullet=True, after=6)
textbox(s, 0.6, 4.45, 6.0, 0.4, ["**Validation**"], 17, NAVY)  # noqa: F821
textbox(s, 0.6, 4.9, 6.0, 2.0, [
    "- Each requirement reviewed for being testable and unambiguous.",
    "- Acceptance criterion written per requirement (what must be observed).",
    "- Every requirement linked to at least one test case.",
], 14, bullet=True, after=6)
textbox(s, 6.9, 1.3, 5.9, 0.4, ["**MoSCoW prioritisation of our features**"], 17, NAVY)  # noqa: F821
mos = [("Must have", "Sign-in with e-mail code, crop, yield, fertiliser, leaf disease, history", NAVY, WHITE),
       ("Should have", "AI assistant, weather and soil, PDF and CSV reports, Android app", TEAL, WHITE),
       ("Could have", "15 languages, dark theme, full auto analysis", TINT, INK),
       ("Won't have (now)", "Doses, market prices, iOS app, offline mode", RGBColor(0xEE, 0xEE, 0xEE), INK)]  # noqa: F821
for i, (h_, t_, fc_, tc_) in enumerate(mos):
    y = 1.8 + i * 1.27
    box(s, 6.9, y, 5.9, 1.12, fc_)  # noqa: F821
    textbox(s, 7.05, y + 0.06, 5.6, 1.0, [f"**{h_}**", t_], 13, tc_, after=2)  # noqa: F821

# ================================================================== 10 units 10-11
s = slide("9. Design Thinking: From Farmer to Prototype")  # noqa: F821
unit_tag(s, "Units 10 and 11")
flow(s, ["Empathize", "Define", "Ideate", "Prototype", "Test"], 0.6, 1.35, 12.2, 0.75, gap=0.35, size=15, dark=(1, 3))
card(s, 0.6, 2.35, 4.0, 2.15, "Example persona: Ramesh, 42",
     ["Small farmer, 2 ha, Bhagalpur", "Has a Soil Health Card, an Android phone", "Reads Hindi, unsure which fertiliser to buy"], 12)
card(s, 0.6, 4.65, 4.0, 2.2, "How might we...",
     ["...turn a soil card into one clear fertiliser choice?", "...let a farmer check a sick leaf in seconds?"], 12)
textbox(s, 4.85, 2.35, 3.6, 0.4, ["**User stories**"], 16, NAVY)  # noqa: F821
textbox(s, 4.85, 2.8, 3.6, 4.1, [
    "- As a **farmer**, I want a fertiliser name for my soil so that I buy only what is short.",
    "- As a **farmer**, I want to photograph a leaf so that I know if it is diseased.",
    "- As an **officer**, I want each result saved so that I can review a farmer's history.",
], 13, bullet=True, after=8)
image(s, WFR / "07_fertiliser.png", 8.7, 2.3, 4.1, 3.9, "Wireframe: fertiliser page (prototype)", border=True)  # noqa: F821
textbox(s, 8.7, 6.55, 4.1, 0.4, ["Reviewed before any code was written"], 11, GREY, align=PP_ALIGN.CENTER)  # noqa: F821

# ================================================================== 11 unit 12
s = slide("10. Analysis and Design")  # noqa: F821
unit_tag(s, "Unit 12")
image(s, UML / "dfd1.png", 0.55, 1.25, 6.5, 4.1, "Analysis: DFD level 1 (what the system does)")  # noqa: F821
textbox(s, 0.6, 5.75, 6.4, 1.2, ["**Analysis** describes what the system must do (data flows, use cases); **design** "
                                 "decides how (modules, tables, API). Keeping them separate let us change the design "
                                 "without changing the requirements."], 13)  # noqa: F821
textbox(s, 7.35, 1.3, 5.4, 0.4, ["**Design: three-tier architecture**"], 16, NAVY)  # noqa: F821
for i, (h_, t_) in enumerate([("Presentation", "Web dashboard, Android app"), ("Application", "FastAPI: rules, models, security"),
                              ("Data", "SQLite, model files, cache")]):
    y = 1.8 + i * 0.95
    box(s, 7.35, y, 5.4, 0.8, NAVY if i == 1 else TINT)  # noqa: F821
    textbox(s, 7.5, y, 5.2, 0.8, [f"**{h_}:** {t_}"], 14, WHITE if i == 1 else INK, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
card(s, 7.35, 5.0, 2.6, 1.85, "Partitioning", ["Split by feature: auth, farms, models, assistant, reports"], 12)
card(s, 10.15, 5.0, 2.6, 1.85, "Abstraction", ["Clients see only REST endpoints, never the models or database"], 12)
textbox(s, 7.35, 4.58, 5.4, 0.4, ["Top-down: system, then tiers, then modules, then functions."], 12, GREY)  # noqa: F821

# ================================================================== 12 unit 13
s = slide("11. Modularity: Coupling and Cohesion")  # noqa: F821
unit_tag(s, "Unit 13")
image(s, UML / "modules.png", 0.55, 1.25, 6.4, 3.3)  # noqa: F821
table(s, [["Module", "Single job (cohesion)"],  # noqa: F821
          ["otp.py", "One-time codes only"], ["fertiliser.py", "Fertiliser reasoning and model"],
          ["assistant.py", "LLM prompt, call, dose check"], ["db.py", "Storage and hashing"],
          ["external.py", "Weather and soil services"]],
      0.6, 4.7, 6.3, [2.0, 4.3], 12, 0.37)
textbox(s, 7.3, 1.3, 5.5, 0.4, ["**Aim: low coupling, high cohesion**"], 17, NAVY)  # noqa: F821
scale = [("Data coupling", "functions pass only the values they need", GREEN_OK),
         ("Stamp coupling", "pass a whole record (used for prediction results)", TEAL),
         ("Control coupling", "a flag changes behaviour (fertiliser 'basis')", RGBColor(0xC9, 0x8B, 0x2B)),  # noqa: F821
         ("Common / content", "shared globals, reaching inside another module: avoided", RGBColor(0xB0, 0x3A, 0x2E))]  # noqa: F821
for i, (h_, t_, c_) in enumerate(scale):
    y = 1.8 + i * 0.82
    b = box(s, 7.3, y, 0.25, 0.68, c_)  # noqa: F821
    textbox(s, 7.7, y - 0.02, 5.1, 0.75, [f"**{h_}:** {t_}"], 13, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
card(s, 7.3, 5.2, 5.5, 1.65, "Refactoring examples",
     ["Fertiliser logic moved out of main.py into its own module", "Android tab navigation rewritten into one go() function"], 12)

# ================================================================== 13 units 14-15
s = slide("12. Software Testing")  # noqa: F821
unit_tag(s, "Units 14 and 15")
flow(s, ["Unit", "Integration", "System", "Acceptance"], 0.6, 1.3, 6.3, 0.7, gap=0.3, size=14)
textbox(s, 0.6, 2.15, 6.3, 0.4, ["**Black-box: equivalence classes and boundaries**"], 15, NAVY)  # noqa: F821
table(s, [["Input", "Invalid", "Valid", "Boundary tests"],  # noqa: F821
          ["Soil pH", "< 3, > 10", "3 to 10", "2.9, 3, 10, 10.1"],
          ["Wrong codes", "6th try", "1 to 5 tries", "5th and 6th try"],
          ["Code resend", "< 60 s", ">= 60 s", "59 s, 60 s"]],
      0.6, 2.6, 6.3, [1.5, 1.4, 1.5, 1.9], 12, 0.45, bold_first_col=True)
textbox(s, 0.6, 4.55, 6.3, 0.4, ["**White-box and grey-box**"], 15, NAVY)  # noqa: F821
textbox(s, 0.6, 4.95, 6.3, 1.9, [
    "- White-box: tests for each branch of the fertiliser rules (nothing short, one short, all short).",
    "- Grey-box: API tests that know the database schema and check rows after a request.",
], 13, bullet=True, after=5)
table(s, [["Suite", "Tests", "Covers"], ["test_auth.py", "21", "Sign-up, sign-in, codes, sessions"],  # noqa: F821
          ["test_features.py", "36", "Farms, models, reports, assistant"], ["test_models.py", "13", "Accuracy targets, validation"],
          ["test_ui.py", "18", "Edge browser, languages, phone width"]],
      7.2, 1.3, 5.6, [1.9, 0.8, 2.9], 12, 0.42)
textbox(s, 7.2, 3.55, 5.6, 0.4, ["**Defect life cycle**"], 15, NAVY)  # noqa: F821
flow(s, ["New", "Open", "Fixed", "Retest", "Closed"], 7.2, 4.0, 5.6, 0.6, gap=0.2, size=12, dark=(4,))
card(s, 7.2, 4.85, 5.6, 2.0, "Defects found and closed",
     ["App: Home tab reopened the Assistant (navigation state)", "App: weather hint shown wrongly (operator precedence)",
      "Server: model list missing the fertiliser model"], 12)

# ================================================================== 14 units 16-17
s = slide("13. Quality and Maintenance")  # noqa: F821
unit_tag(s, "Units 16 and 17")
card(s, 0.6, 1.3, 3.0, 1.6, "QA (prevent)", ["Coding rules, reviews, SRS, design before code"], 13)
card(s, 3.75, 1.3, 3.0, 1.6, "QC (detect)", ["Running the 88 tests, load test, checking every page"], 13)
textbox(s, 0.6, 3.15, 6.2, 0.4, ["**Quality metrics we measured**"], 15, NAVY)  # noqa: F821
table(s, [["Metric", "Value"], ["Tests passed", "88 of 88"], ["Load-test errors", "0 of 32,061 requests"],  # noqa: F821
          ["p95 at 100 users", f"{next(x['p95_ms'] for x in LOAD['step'] if x['users'] == 100):.0f} ms"],  # noqa: F821
          ["Requirements traced", f"{len(FR) + len(NFR)} of {len(FR) + len(NFR)}"]],
      0.6, 3.6, 6.2, [3.0, 3.2], 13, 0.5, bold_first_col=True)
textbox(s, 0.6, 6.25, 6.2, 0.4, ["Defect density and MTBF need longer live use; they are planned once the app has real users."], 11, GREY)  # noqa: F821
textbox(s, 7.1, 1.3, 5.7, 0.4, ["**Four types of maintenance, from our project**"], 15, NAVY)  # noqa: F821
mt = [("Corrective", "Fixed the app's weather-hint and navigation bugs"),
      ("Adaptive", "New map user agent after tile servers blocked the default; Android 12 splash"),
      ("Perfective", "Added the fertiliser model, welcome screen, trimmed buttons"),
      ("Preventive", "Model cards, automated tests, keys outside the code")]
for i, (h_, t_) in enumerate(mt):
    y = 1.8 + i * 1.0
    box(s, 7.1, y, 1.75, 0.85, NAVY)  # noqa: F821
    textbox(s, 7.1, y, 1.75, 0.85, [f"**{h_}**"], 13, WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
    box(s, 8.95, y, 3.85, 0.85)  # noqa: F821
    textbox(s, 9.05, y, 3.7, 0.85, [t_], 12, anchor=MSO_ANCHOR.MIDDLE)  # noqa: F821
card(s, 7.1, 5.85, 5.7, 1.0, "Modernisation path", ["SQLite to PostgreSQL, more workers, offline app mode"], 12)

# ================================================================== 15 conclusion
s = slide("14. Conclusion")  # noqa: F821
for i, (v, l) in enumerate([("32 + 15", "requirements specified"), ("88 / 88", "tests passed"),
                            ("100", "users at once under 2 s"), ("2", "clients on one API")]):
    x = 0.6 + i * 3.1
    box(s, x, 1.35, 2.9, 1.45)  # noqa: F821
    textbox(s, x + 0.1, 1.42, 2.7, 0.75, [f"**{v}**"], 28, TEAL, align=PP_ALIGN.CENTER)  # noqa: F821
    textbox(s, x + 0.1, 2.2, 2.7, 0.45, [l], 13, GREY, align=PP_ALIGN.CENTER)  # noqa: F821
textbox(s, 0.6, 3.1, 8.0, 3.2, [
    "- We followed an **iterative incremental** process from SRS to deployment.",
    "- A **three-tier, modular** design serves a web dashboard and an Android app from one API.",
    "- **Black-box, white-box, integration, UI and load testing** verified every requirement.",
    "- Quality was built in (QA) and checked (QC); maintenance is planned in four types.",
], 16, bullet=True, after=10)
box(s, 8.9, 3.1, 3.9, 2.6, NAVY)  # noqa: F821
textbox(s, 9.05, 3.25, 3.6, 2.4, ["**THANK YOU**", "", "Live: ai.software.microeagle.online", "Questions are welcome"],
        18, WHITE, align=PP_ALIGN.CENTER, after=2)  # noqa: F821
textbox(s, 0.6, 6.45, 12.1, 0.45, [f"{COURSE_SE}  |  {FAC_SE}  |  " + "  |  ".join(n for n, _ in C.TEAM)], 12, GREY,  # noqa: F821
        align=PP_ALIGN.CENTER)

prs.core_properties.title = "AgriSense AI - Software Engineering Evaluation"  # noqa: F821
prs.save(OUT)  # noqa: F821
print("wrote", OUT, N[0], "slides")  # noqa: F821
