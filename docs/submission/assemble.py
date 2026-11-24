"""Assembles Project/: 05_Source_Code/, 06_Test_Cases.xlsx, 07_Test_Evidence/, README.md.
Test cases are parsed from the docstrings in tests/test_*.py; results come from tests/results.xml."""
import ast
import json
import platform
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "Project"
sys.path.insert(0, str(HERE))
from spec import AUTHOR, FR, NFR, PROJECT, URL  # noqa: E402

UI_SHOTS = ROOT / "tests" / "evidence"


# ------------------------------------------------------------------ test catalogue
def catalogue():
    cases = []
    for f in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_tc"):
                doc = ast.get_docstring(node) or ""
                lines = doc.splitlines()
                tc, module, title = [x.strip() for x in lines[0].split("|", 2)]
                fields = {}
                for line in lines[1:]:
                    m = re.match(r"\s*(pre|data|steps|expected):\s*(.*)", line)
                    if m:
                        key = m.group(1)
                        fields[key] = m.group(2)
                    elif key:
                        fields[key] += " " + line.strip()
                live = any(isinstance(d, ast.Attribute) and d.attr == "live" for d in node.decorator_list)
                kind = {"test_ui.py": "Automated - UI (Edge browser)", "test_models.py": "Automated - Model quality"}.get(
                    f.name, "Automated - API / integration")
                if live:
                    kind = "Automated - Live external service"
                cases.append(dict(id=tc, module=module, title=title, pre=fields.get("pre", "-"), data=fields.get("data", "-"),
                                  steps=fields.get("steps", ""), expected=fields.get("expected", ""), type=kind,
                                  test=f"tests/{f.name}::{node.name}", func=node.name))
    cases.sort(key=lambda c: c["id"])
    return cases


def results():
    root = ET.parse(ROOT / "tests" / "results.xml").getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    out = {}
    for tc in suite.iter("testcase"):
        fail = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
        out[tc.get("name")] = ("Fail" if fail is not None else "Skipped" if tc.find("skipped") is not None else "Pass",
                               float(tc.get("time")), (fail.get("message") if fail is not None else ""))
    return out, suite.get("timestamp", ""), float(suite.get("time"))


def req_map():
    m = {}
    for fid, _, _, _, tests in FR:
        for t in tests:
            m.setdefault(t, []).append(fid)
    for nid, _, _, tests in NFR:
        for t in tests:
            m.setdefault(t, []).append(nid)
    return m


# ------------------------------------------------------------------ workbook
def workbook(cases, res, stamp, total_time):
    wb = Workbook()
    F = "Arial"
    head = Font(name=F, bold=True, color="FFFFFF", size=10)
    hfill = PatternFill("solid", fgColor="2E7D4F")
    thin = Side(style="thin", color="C9D3CD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")
    normal = Font(name=F, size=9)
    rm = req_map()

    # --- Test Cases
    ws = wb.active
    ws.title = "Test Cases"
    cols = [("TC ID", 9), ("Module", 16), ("Test case title", 34), ("Type", 18), ("Requirement(s)", 14),
            ("Preconditions", 22), ("Test data", 26), ("Test steps", 46), ("Expected result", 46), ("Actual result", 34),
            ("Status", 9), ("Evidence", 30), ("Automated test", 36), ("Executed on", 17), ("Duration (s)", 10)]
    for i, (name, w) in enumerate(cols, 1):
        c = ws.cell(row=1, column=i, value=name)
        c.font, c.fill, c.alignment, c.border = head, hfill, Alignment(wrap_text=True, vertical="center"), border
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 30
    executed = stamp.replace("T", " ")[:16] if stamp else time.strftime("%Y-%m-%d %H:%M")
    for r, c in enumerate(cases, 2):
        status, dur, msg = res.get(c["func"], ("Not run", 0, ""))
        shots = sorted(p.name for p in UI_SHOTS.glob(f"{c['id']}*.png"))
        evidence = ("UI_screenshots/" + ", ".join(shots)) if shots else "pytest_output.txt, results.xml"
        if c["type"].endswith("Model quality"):
            evidence += "; model_evaluation/"
        if "Live" in c["type"]:
            evidence += "; live_deployment/"
        actual = ("Behaved as expected; all assertions passed." if status == "Pass" else f"Assertion failed: {msg[:200]}")
        row = [c["id"], c["module"], c["title"], c["type"], ", ".join(rm.get(c["id"], [])) or "-", c["pre"], c["data"],
               c["steps"].replace(" 2. ", "\n2. ").replace(" 3. ", "\n3. ").replace(" 4. ", "\n4. ").replace(" 5. ", "\n5. "),
               c["expected"], actual, status, evidence, c["test"], executed, round(dur, 2)]
        for i, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=i, value=v)
            cell.font, cell.alignment, cell.border = normal, wrap, border
        st = ws.cell(row=r, column=11)
        st.font = Font(name=F, size=9, bold=True, color="1B5E20" if status == "Pass" else "B71C1C")
        st.fill = PatternFill("solid", fgColor="E3F2E7" if status == "Pass" else "FDECEA")
    n = len(cases) + 1
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:O{n}"
    dv = DataValidation(type="list", formula1='"Pass,Fail,Blocked,Not run"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"K2:K{n}")

    # --- Summary
    s = wb.create_sheet("Summary", 0)
    s["A1"] = f"{PROJECT} - Test Summary"
    s["A1"].font = Font(name=F, bold=True, size=14, color="1B3A2A")
    info = [("Project", PROJECT), ("Prepared by", AUTHOR), ("System under test", URL + " (and local build)"),
            ("Executed", f"{executed} (automated run, total {total_time:.0f} s)"),
            ("How to re-run", "python -m pytest tests -v --junitxml=tests/results.xml"),
            ("Note", "Status column on 'Test Cases' is the recorded result of the run; all counts below are formulas.")]
    for i, (k, v) in enumerate(info, 3):
        s.cell(row=i, column=1, value=k).font = Font(name=F, bold=True, size=10)
        s.cell(row=i, column=2, value=v).font = Font(name=F, size=10)
    r0 = 11
    hdr = ["Module", "Total", "Passed", "Failed", "Pass rate"]
    for i, h in enumerate(hdr, 1):
        c = s.cell(row=r0, column=i, value=h)
        c.font, c.fill, c.border = head, hfill, border
    modules = []
    for c in cases:
        if c["module"] not in modules:
            modules.append(c["module"])
    for j, mname in enumerate(modules, r0 + 1):
        s.cell(row=j, column=1, value=mname)
        s.cell(row=j, column=2, value=f"=COUNTIF('Test Cases'!$B$2:$B${n},A{j})")
        s.cell(row=j, column=3, value=f"=COUNTIFS('Test Cases'!$B$2:$B${n},A{j},'Test Cases'!$K$2:$K${n},\"Pass\")")
        s.cell(row=j, column=4, value=f"=COUNTIFS('Test Cases'!$B$2:$B${n},A{j},'Test Cases'!$K$2:$K${n},\"Fail\")")
        s.cell(row=j, column=5, value=f"=IF(B{j}=0,0,C{j}/B{j})").number_format = "0.0%"
        for i in range(1, 6):
            s.cell(row=j, column=i).font, s.cell(row=j, column=i).border = Font(name=F, size=10), border
    t = r0 + 1 + len(modules)
    s.cell(row=t, column=1, value="Total")
    for col in "BCD":
        s[f"{col}{t}"] = f"=SUM({col}{r0 + 1}:{col}{t - 1})"
    s[f"E{t}"] = f"=IF(B{t}=0,0,C{t}/B{t})"
    s[f"E{t}"].number_format = "0.0%"
    for i in range(1, 6):
        s.cell(row=t, column=i).font, s.cell(row=t, column=i).border = Font(name=F, size=10, bold=True), border
    r1 = t + 2
    for i, h in enumerate(["Test type", "Total", "Passed"], 1):
        c = s.cell(row=r1, column=i, value=h)
        c.font, c.fill, c.border = head, hfill, border
    types = sorted({c["type"] for c in cases})
    for j, ty in enumerate(types, r1 + 1):
        s.cell(row=j, column=1, value=ty)
        s.cell(row=j, column=2, value=f"=COUNTIF('Test Cases'!$D$2:$D${n},A{j})")
        s.cell(row=j, column=3, value=f"=COUNTIFS('Test Cases'!$D$2:$D${n},A{j},'Test Cases'!$K$2:$K${n},\"Pass\")")
        for i in range(1, 4):
            s.cell(row=j, column=i).font, s.cell(row=j, column=i).border = Font(name=F, size=10), border
    s.column_dimensions["A"].width = 34
    s.column_dimensions["B"].width = 60
    for col in "CDE":
        s.column_dimensions[col].width = 12

    # --- Traceability
    tr = wb.create_sheet("Traceability")
    for i, (h, w) in enumerate([("Requirement", 12), ("Area", 14), ("Description", 70), ("Test cases", 34),
                                ("Tests", 8), ("Passed", 8), ("Covered & passing", 16)], 1):
        c = tr.cell(row=1, column=i, value=h)
        c.font, c.fill, c.border = head, hfill, border
        tr.column_dimensions[get_column_letter(i)].width = w
    rows = [(f, a, t, ", ".join(ts)) for f, a, t, _, ts in FR] + [(i, a, t, ", ".join(ts)) for i, a, t, ts in NFR]
    for j, (rid, area, text, tcs) in enumerate(rows, 2):
        vals = [rid, area, text, tcs or "Inspection / deployment",
                f"=SUMPRODUCT(ISNUMBER(SEARCH('Test Cases'!$A$2:$A${n},D{j}))*1)",
                f"=SUMPRODUCT(ISNUMBER(SEARCH('Test Cases'!$A$2:$A${n},D{j}))*('Test Cases'!$K$2:$K${n}=\"Pass\"))",
                f'=IF(E{j}=0,"Inspection",IF(F{j}=E{j},"Yes","No"))']
        for i, v in enumerate(vals, 1):
            c = tr.cell(row=j, column=i, value=v)
            c.font, c.alignment, c.border = normal, wrap, border
    tr.freeze_panes = "B2"

    # --- Environment
    env = wb.create_sheet("Environment")
    import importlib.metadata as md

    def ver(p):
        try:
            return md.version(p)
        except Exception:
            return "-"
    rows = [("Item", "Value"), ("Operating system", platform.platform()), ("Python", platform.python_version()),
            ("pytest", ver("pytest")), ("FastAPI", ver("fastapi")), ("Playwright", ver("playwright")),
            ("Browser", "Microsoft Edge (Chromium), headless, via Playwright channel 'msedge'"),
            ("scikit-learn", ver("scikit-learn")), ("LightGBM", ver("lightgbm")), ("ONNX Runtime", ver("onnxruntime")),
            ("PyTorch (training)", ver("torch") + " CUDA 12.8, NVIDIA GeForce RTX 5070 Ti"),
            ("Database under test", "Throwaway SQLite per run (never the live database)"),
            ("E-mail in tests", "OTP delivery captured in memory (API tests) or by a stand-in mailbox (UI tests)"),
            ("Live services in tests", "Open-Meteo, NASA POWER, ISRIC SoilGrids, Mistral API (real calls)"),
            ("Production", URL + " - Docker on Hostinger VPS, Traefik + Let's Encrypt")]
    for j, (k, v) in enumerate(rows, 1):
        a, b = env.cell(row=j, column=1, value=k), env.cell(row=j, column=2, value=v)
        for c in (a, b):
            c.font, c.border = (head if j == 1 else Font(name=F, size=10)), border
            if j == 1:
                c.fill = hfill
    env.column_dimensions["A"].width = 26
    env.column_dimensions["B"].width = 90
    cover_sheet(wb)
    path = OUT / "06_Test_Cases.xlsx"
    wb.save(path)
    return path


def cover_sheet(wb):
    """First tab: the same cover as the PDF documents (logo, course, team)."""
    sys.path.insert(0, str(ROOT / "docs" / "report"))
    import content as C
    from openpyxl.drawing.image import Image as XLImage
    cs = wb.create_sheet("Cover", 0)
    cs.sheet_view.showGridLines = False
    cs.column_dimensions["A"].width = 4
    for col in "BCDEFGH":
        cs.column_dimensions[col].width = 14
    logo = XLImage(str(ROOT / "docs" / "report" / "niit_logo.png"))
    logo.width, logo.height = 520, int(520 * 162 / 568)
    cs.add_image(logo, "B2")
    rows = [("B. Tech. CSE Semester V", 14, True), (f"L-T-P-C: {C.LTPC}", 14, True), (f"Session: {C.YEAR}", 14, True), ("", 10, False),
            (f"{C.COURSE} ({C.COURSE_CODE})", 15, True), ("TEST CASES", 15, True), (C.TITLE, 13, True), ("", 10, False)]
    rows += [(f"Name: {n}    Enrollment No.: {e}", 12, True) for n, e in C.TEAM]
    rows += [(f"Section: {C.SECTION}", 12, True), ("", 10, False), (f"Submitted To: {C.FACULTY}", 11, False),
             ("Submitted By: " + ", ".join(n for n, _ in C.TEAM), 11, False)]
    r = 12
    for text, size, bold in rows:
        cs.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
        c = cs.cell(row=r, column=2, value=text)
        c.font = Font(name="Times New Roman", size=size, bold=bold)
        c.alignment = Alignment(horizontal="center", vertical="center")
        if text.startswith(("Name:", "Section:")):
            c.fill = PatternFill("solid", fgColor="FFFF00")
        cs.row_dimensions[r].height = 22
        r += 1
    cs.print_area = "A1:I27"
    cs.page_setup.orientation = "portrait"
    cs.page_setup.fitToWidth = 1
    cs.page_setup.fitToHeight = 1
    cs.sheet_properties.pageSetUpPr.fitToPage = True
    cs.print_options.horizontalCentered = True
    wb.active = 0


# ------------------------------------------------------------------ evidence
def evidence():
    ev = OUT / "07_Test_Evidence"
    if ev.exists():
        shutil.rmtree(ev)
    (ev / "UI_screenshots").mkdir(parents=True)
    for p in sorted(UI_SHOTS.glob("*.png")):
        shutil.copy2(p, ev / "UI_screenshots" / p.name)
    shutil.copy2(ROOT / "tests" / "pytest_output.txt", ev / "pytest_output.txt")
    shutil.copy2(ROOT / "tests" / "results.xml", ev / "results.xml")
    me = ev / "model_evaluation"
    me.mkdir()
    for n in ("crop_model.json", "yield_model.json", "leaf_disease.json"):
        shutil.copy2(ROOT / "app" / "models" / n, me / n)
    for n in ("crop_comparison", "crop_confusion", "crop_importance", "yield_baselines", "yield_per_crop",
              "yield_importance", "leaf_history", "leaf_confusion", "leaf_recall", "leaf_counts"):
        p = ROOT / "docs" / "figs" / f"{n}.png"
        if p.exists():
            shutil.copy2(p, me / p.name)
    for n in ("leaf_full_train.log.keep", "leaf_train.log"):
        p = ROOT / "ml" / n
        if p.exists():
            shutil.copy2(p, me / n.replace(".keep", ""))
    ld = ev / "live_deployment"
    shutil.copytree(HERE / "live_evidence", ld)
    lt = ev / "load_test"
    lt.mkdir()
    for f in (ROOT / "tests" / "load" / "results").glob("*"):
        shutil.copy2(f, lt / f.name)
    for f in ("loadtest.py", "model_bench.py", "run_on_vps.sh", "report_figs.py"):
        shutil.copy2(ROOT / "tests" / "load" / f, lt / f)
    for f in (ROOT / "docs" / "figs").glob("load_*.png"):
        shutil.copy2(f, lt / f.name)
    shutil.copy2(ROOT / "docs" / "AgriSense_AI_Model_Report.pdf", ev / "AgriSense_AI_Model_Report.pdf")
    (ev / "README.md").write_text(
        "# Test evidence\n\n"
        "| Item | What it shows |\n|---|---|\n"
        "| `pytest_output.txt` | Console output of the full automated run (every test case, PASS/FAIL, duration) |\n"
        "| `results.xml` | Same run in JUnit XML (machine-readable; the workbook's Status column is filled from it) |\n"
        "| `UI_screenshots/` | Screenshots taken by the browser tests at the checked moment, named by test case (TC-059 ... TC-088) |\n"
        "| `model_evaluation/` | Model cards written by the training scripts (metrics, splits, confusion matrices) + charts + GPU training log |\n"
        "| `live_deployment/` | Smoke test run inside the live container, OTP mail-chain check and HTTPS certificate of the public site |\n"
        "| `AgriSense_AI_Model_Report.pdf` | Detailed model report with all evaluation figures |\n"
        "| `Test_Report.pdf` | Test approach and results, screenshots of the web dashboard and Android app, load and capacity test |\n"
        "| `load_test/` | Load-test scripts, raw results (bench.json, load.json, stats.txt, summary.json) and charts |\n", encoding="utf-8")


# ------------------------------------------------------------------ source code
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "storage", "leaf_best.pt", "staging", "backup_v1", "evidence",
                                "results.xml", "pytest_output.txt", "wf", "figs", "live_evidence", "*.log.keep")


def source():
    sc = OUT / "05_Source_Code"
    if sc.exists():
        shutil.rmtree(sc)
    sc.mkdir()
    for d in ("app", "ml", "tests", "deploy"):
        shutil.copytree(ROOT / d, sc / d, ignore=IGNORE)
    (sc / "docs").mkdir()
    shutil.copy2(ROOT / "docs" / "build_report.py", sc / "docs" / "build_report.py")
    shutil.copy2(ROOT / "docs" / "capture_screens.py", sc / "docs" / "capture_screens.py")
    shutil.copytree(HERE, sc / "docs" / "submission", ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", "wf", "figs", "live_evidence", "mobile", "mobile_framed", "*.png"))
    for f in ("Dockerfile", "docker-compose.yml", "requirements.txt", ".dockerignore", "pytest.ini", "README.md"):
        shutil.copy2(ROOT / f, sc / f)
    # the Android app (Android Studio project next to this one) - sources and Gradle files only
    android = ROOT.parent / "Ai_and_Soft_Engg"
    if android.exists():
        shutil.copytree(android, sc / "android", ignore=shutil.ignore_patterns(
            "build", ".gradle", ".idea", ".kotlin", "local.properties", "*.apk", "*.iml", "captures", ".cxx"))
    (sc / "config").mkdir()
    (sc / "config" / "api_keys.env.example").write_text(
        "# Copy to api_keys.env and fill in. Never commit the real file.\n"
        "MISTRAL_API_KEY=\nMISTRAL_MODEL=ministral-14b-latest\nMISTRAL_FALLBACK_MODEL=ministral-8b-latest,ministral-3b-latest\n"
        "# E-mail one-time codes (n8n workflow AgriSense_OTP_Delivery). Leave empty for password-only local development.\n"
        "OTP_WEBHOOK_URL=\nOTP_SHARED_SECRET=\n", encoding="utf-8")
    (sc / "requirements-dev.txt").write_text(
        "-r requirements.txt\npytest\nplaywright\nmatplotlib\nreportlab\nopenpyxl\npypdfium2\n"
        "torch  # CUDA build for training: pip install torch --index-url https://download.pytorch.org/whl/cu128\n"
        "torchvision\nlightgbm\nscikit-learn\npandas\n", encoding="utf-8")
    # no secret value may leave the machine: compare every file against the real key file's values
    secrets = [line.split("=", 1)[1].strip().strip('"') for line in
               (ROOT / "config" / "api_keys.env").read_text().splitlines()
               if "=" in line and ("KEY" in line or "SECRET" in line) and len(line.split("=", 1)[1].strip()) >= 12]
    for p in sc.rglob("*"):
        if p.is_file():
            t = p.read_bytes()
            assert not any(s.encode() in t for s in secrets), f"secret found in {p}"
    size = sum(p.stat().st_size for p in sc.rglob("*") if p.is_file()) / 1e6
    print(f"source: {sum(1 for p in sc.rglob('*') if p.is_file())} files, {size:.1f} MB")


def readme(cases, res, total_time):
    passed = sum(1 for c in cases if res.get(c["func"], ("",))[0] == "Pass")
    crop = json.loads((ROOT / "app/models/crop_model.json").read_text())
    yld = json.loads((ROOT / "app/models/yield_model.json").read_text())
    leaf = json.loads((ROOT / "app/models/leaf_disease.json").read_text())
    fert = json.loads((ROOT / "app/models/fertiliser_model.json").read_text())
    y = yld["results"]["LightGBM (this model)"]
    sys.path.insert(0, str(ROOT / "docs" / "report"))
    import content as C
    team = "\n".join(f"| {n} | {e} |" for n, e in C.TEAM)
    (OUT / "README.md").write_text(f"""# AgriSense AI - Smart Farming Assistant

{C.COURSE.title().replace("&", "and")} ({C.COURSE_CODE}) project, B. Tech. CSE Semester V, Session {C.YEAR}, Section {C.SECTION}.
Submitted to {C.FACULTY}.

| Name | Enrollment No. |
|---|---|
{team}

**Live system:** {URL}

AgriSense AI is a web platform and Android app for Indian farmers: crop recommendation, yield prediction, fertiliser guidance,
leaf-disease detection, live weather and soil data, and an AI assistant in 15 languages, with secure
accounts (e-mail one-time codes) and every result stored per user.

## Submission contents

| Item | Description |
|---|---|
| `01_Project_Proposal.pdf` | Problem, users, objectives, scope, proposed solution and technology |
| `02_SRS.pdf` | Requirements: introduction, overall description, {len(FR)} functional and {len(NFR)} non-functional requirements, interfaces, use cases, data requirements, acceptance criteria |
| `03_SDD.pdf` | Design: architecture, modules, classes, data model, interfaces, sequence flows, error handling, security, technology, deployment, traceability matrix, limitations |
| `04_Wireframes.pdf` | Wireframes of every web screen and the phone layout, navigation, review checklist |
| `05_Source_Code/` | Complete source: app, training scripts, tests, Docker and deployment files, and the Android app in `android/` (secrets removed) |
| `06_Test_Cases.xlsx` | {len(cases)} test cases with steps, expected/actual results, status, evidence and requirement traceability |
| `07_Test_Evidence/` | Test report (results, app screenshots, load test), test run output, UI screenshots, model evaluation, load-test data |

## Results at a glance

| Component | Method | Result on held-out data |
|---|---|---|
| Crop recommendation | {crop['selected_model']} (best of 5 by 5-fold CV) | {crop['test_accuracy'] * 100:.2f}% accuracy |
| Yield prediction | LightGBM, temporal test (unseen years) | R2 {y['r2']}, MAE {y['mae_t_ha']} t/ha (beats last-year and 3-year-mean baselines) |
| Leaf disease | EfficientNet-B0 fine-tuned on GPU, calibrated | {leaf['test']['accuracy'] * 100:.2f}% accuracy, {leaf['test']['accuracy_when_answered'] * 100:.2f}% when it answers |
| Fertiliser recommendation | {fert['chosen']['model']} on N, P, K (best of 8 by 5x5 repeated CV, {fert['rows']} rows) | {fert['chosen']['cv_accuracy_mean'] * 100:.1f}% cross-validated accuracy |
| Tests | pytest: API, model, live services, Edge UI | {passed} of {len(cases)} passed ({total_time:.0f} s) |

## Run locally

```
cd 05_Source_Code
python -m venv .venv && .venv\\Scripts\\activate
pip install -r requirements-dev.txt
copy config\\api_keys.env.example config\\api_keys.env   (add a Mistral key; OTP values optional)
python -m uvicorn app.main:app --port 8150
```

Open http://127.0.0.1:8150. Without `OTP_WEBHOOK_URL` the app signs in with password only (development mode).

Run the tests: `python -m pytest tests -v` (UI tests need Microsoft Edge; the datasets in `data/raw` are needed for
image-based tests and for retraining and are not included because of their size - see 01_Project_Proposal.pdf section 6).

Retrain: `python ml/train_crop.py`, `python ml/train_yield.py`, `python ml/train_fertiliser.py`, `python ml/train_leaf_full.py --epochs 8` (CUDA GPU).

Android app: open `android/` in Android Studio (its bundled JDK, Android SDK 36) and run, or `gradlew assembleDebug`.
It talks to the API set in `android/gradle.properties` (`agrisense.apiBase`).

## Deploy

`docker compose up -d --build` on a host with Traefik; route file in `deploy/agrisense.yml`.
""", encoding="utf-8")


def main():
    cases = catalogue()
    res, stamp, total = results()
    missing = [c["id"] for c in cases if c["func"] not in res]
    assert not missing, f"not in results.xml: {missing}"
    print("workbook:", workbook(cases, res, stamp, total).name, len(cases), "cases")
    evidence()
    source()
    readme(cases, res, total)
    print("done")


if __name__ == "__main__":
    main()
