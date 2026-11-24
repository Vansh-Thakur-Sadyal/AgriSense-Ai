"""End-to-end UI tests in Microsoft Edge (Playwright). Starts the real app on a throwaway database
plus a stand-in OTP mailbox, drives the pages like a user, and saves a screenshot per test into
tests/evidence/ as test evidence."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "tests" / "evidence"
EVID.mkdir(parents=True, exist_ok=True)
APP_PORT, HOOK_PORT = 8161, 8162
BASE = f"http://127.0.0.1:{APP_PORT}"
LEAF = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"
pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def server():
    tmp = Path(tempfile.mkdtemp(prefix="agrisense_ui_"))
    log = tmp / "mailbox.jsonl"
    log.write_text("")
    hook = subprocess.Popen([sys.executable, str(ROOT / "tests" / "fake_mailbox.py"), str(HOOK_PORT), str(log), "ui-secret"])
    env = {**os.environ, "AGRISENSE_STORAGE": str(tmp / "db"),
           "OTP_WEBHOOK_URL": f"http://127.0.0.1:{HOOK_PORT}/hook", "OTP_SHARED_SECRET": "ui-secret"}
    app = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(APP_PORT)], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            if httpx.get(BASE + "/healthz").status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    yield log
    app.terminate(); hook.terminate()


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        yield b
        b.close()


def code_for(log, email):
    for _ in range(40):
        for line in reversed(log.read_text().splitlines()):
            j = json.loads(line)
            if j["to"] == email:
                return j["code"]
        time.sleep(0.25)
    raise AssertionError("no code e-mailed")


def shot(page, name):
    time.sleep(0.6)
    page.screenshot(path=str(EVID / f"{name}.png"))


def signed_in_page(browser, log, name="UI Tester"):
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    email = f"ui{time.time_ns()}@agrisense.test"
    page.goto(BASE + "/")
    page.click("#swap")
    page.fill("#af [name=name]", name)
    page.fill("#af [name=email]", email)
    page.fill("#af [name=password]", "Farm12345")
    page.click("#ago")
    page.wait_for_selector("#of")
    page.fill("#of [name=code]", code_for(log, email))
    page.wait_for_selector("#view h1", timeout=15000)
    return page, email


def test_tc059_ui_signup_with_otp(server, browser):
    """TC-059 | UI - Authentication | Sign-up through the e-mail code screen to the dashboard
    pre: App running, mailbox stand-in
    data: name, new e-mail, Farm12345
    steps: 1. Open the site. 2. Create account. 3. Fill the form and submit. 4. Type the e-mailed code.
    expected: "Check your e-mail" screen shows the masked address; typing 6 digits signs in and opens Overview with a greeting."""
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    email = f"ui{time.time_ns()}@agrisense.test"
    page.goto(BASE + "/")
    page.click("#swap")
    page.fill("#af [name=name]", "Asha Devi")
    page.fill("#af [name=email]", email)
    page.fill("#af [name=password]", "Farm12345")
    shot(page, "TC-059a_signup_form")
    page.click("#ago")
    page.wait_for_selector("#of")
    assert "Check your e-mail" in page.inner_text("#of") and "*" in page.inner_text("#of")
    shot(page, "TC-059b_otp_screen")
    page.fill("#of [name=code]", code_for(server, email))
    page.wait_for_selector("#view h1", timeout=15000)
    assert "Asha" in page.inner_text("#view h1") and page.url.endswith("#/overview")
    shot(page, "TC-059c_dashboard_after_code")


def test_tc060_ui_wrong_password(server, browser):
    """TC-060 | UI - Authentication | Wrong password shows an error and no code screen
    pre: Account exists
    data: wrong password
    steps: 1. Sign in with a wrong password.
    expected: Error toast "Email/phone or password is incorrect"; still on the sign-in form."""
    page, email = signed_in_page(browser, server)
    page.click("#logout")
    page.wait_for_selector("#af")
    page.fill("#af [name=identifier]", email)
    page.fill("#af [name=password]", "Wrong9999")
    page.click("#ago")
    page.wait_for_selector("#toasts >> text=password is incorrect")
    assert page.query_selector("#of") is None
    shot(page, "TC-060_wrong_password")


def test_tc061_ui_wrong_code(server, browser):
    """TC-061 | UI - Authentication | Wrong code keeps the user on the code screen
    pre: Sign-up submitted
    data: code 000000
    steps: 1. Sign up. 2. Type 000000.
    expected: Error toast with tries left; field cleared; still on "Check your e-mail"."""
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    page.goto(BASE + "/")
    page.click("#swap")
    page.fill("#af [name=name]", "Wrong Code")
    page.fill("#af [name=email]", f"ui{time.time_ns()}@agrisense.test")
    page.fill("#af [name=password]", "Farm12345")
    page.click("#ago")
    page.wait_for_selector("#of")
    page.fill("#of [name=code]", "000000")
    page.wait_for_selector("#toasts >> text=tries left")
    assert page.query_selector("#of") and page.input_value("#of [name=code]") == ""
    shot(page, "TC-061_wrong_code")


def test_tc062_ui_crop(server, browser):
    """TC-062 | UI - Crop recommendation | Form to result card
    pre: Signed in
    data: N 90, P 42, K 43, 21, 82, 6.5, 203
    steps: 1. Open Crop Recommendation. 2. Fill the 7 fields. 3. Press Predict Suitable Crop.
    expected: Result card shows Rice with confidence and alternatives."""
    page, _ = signed_in_page(browser, server)
    page.goto(BASE + "/#/crop")
    page.wait_for_selector("#cf")
    for k, v in {"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82, "ph": 6.5, "rainfall": 203}.items():
        page.fill(f"#cf [name={k}]", str(v))
    page.click("#cgo")
    page.wait_for_selector("text=Rice", timeout=15000)
    shot(page, "TC-062_crop_result")


def test_tc063_ui_disease(server, browser):
    """TC-063 | UI - Disease detection | Upload a leaf photo and see the diagnosis
    pre: Signed in
    data: Tomato___Early_blight image
    steps: 1. Open Plant Disease Detection. 2. Choose the photo. 3. Analyse Image.
    expected: "Tomato - Early blight" with confidence and cause / symptoms / next steps."""
    page, _ = signed_in_page(browser, server)
    page.goto(BASE + "/#/disease")
    page.wait_for_selector("#file", state="attached")
    page.set_input_files("#file", str(sorted((LEAF / "Tomato___Early_blight").iterdir())[5]))
    page.click("#dgo")
    page.wait_for_selector("text=Early blight", timeout=20000)
    assert "Fungus" in page.inner_text("#view") or "Alternaria" in page.inner_text("#view")
    shot(page, "TC-063_disease_result")


def test_tc064_ui_all_pages_open(server, browser):
    """TC-064 | UI - Navigation | Every sidebar page opens without an error
    pre: Signed in (new user, no farm)
    data: -
    steps: 1. Click each of the 12 sidebar entries plus Help.
    expected: No page shows "This page could not load"."""
    page, _ = signed_in_page(browser, server)
    for k in ["overview", "crop", "yield", "fertiliser", "disease", "assistant", "weather", "soil", "farms",
              "history", "reports", "settings", "help"]:
        page.goto(BASE + f"/#/{k}")
        time.sleep(1.8)
        assert "could not load" not in page.inner_text("#view"), k
    shot(page, "TC-064_help_page")


def test_tc065_ui_hindi(server, browser):
    """TC-065 | UI - Language | Switch the interface to Hindi
    pre: Signed in
    data: -
    steps: 1. Pick Hindi in the language menu of the top bar.
    expected: Sidebar labels change to Devanagari and the page re-renders without an error (also when switched while the page is still loading)."""
    page, _ = signed_in_page(browser, server)
    page.select_option("#lang-sel", "hi")   # immediately, while Overview may still be loading
    time.sleep(4)
    nav = page.inner_text("#sidebar nav")
    assert any("ऀ" <= ch <= "ॿ" for ch in nav)
    assert "could not load" not in page.inner_text("#view")
    shot(page, "TC-065_hindi")


def test_tc066_ui_mobile(server, browser):
    """TC-066 | UI - Responsive | Phone width (375 px) has no horizontal scrolling
    pre: Signed in
    data: viewport 375 x 812
    steps: 1. Open Overview and Crop on a 375 px wide screen.
    expected: Page width equals the viewport (no sideways scroll); menu button visible."""
    page, _ = signed_in_page(browser, server)
    page.set_viewport_size({"width": 375, "height": 812})
    for k in ["overview", "crop"]:
        page.goto(BASE + f"/#/{k}")
        time.sleep(2)
        assert page.evaluate("document.documentElement.scrollWidth") <= 376, k
    shot(page, "TC-066_mobile")


def test_tc068_ui_offline_cdns(server, browser):
    """TC-068 | UI - Resilience | The interface renders correctly when Google Fonts and CDNs are blocked
    pre: Browser can reach only the AgriSense server (all other hosts blocked)
    data: -
    steps: 1. Block every request that is not to the app. 2. Sign up and reach Overview. 3. Inspect icons and fonts.
    expected: Icon font loaded from the app; every icon is about one glyph wide (no ligature names like "dashboard" as text); no page error."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    blocked = []

    def gate(route):
        if route.request.url.startswith(BASE):
            return route.continue_()
        blocked.append(route.request.url)
        return route.abort()
    ctx.route("**/*", gate)
    page = ctx.new_page()
    email = f"ui{time.time_ns()}@agrisense.test"
    page.goto(BASE + "/")
    page.click("#swap")
    page.fill("#af [name=name]", "Offline Tester")
    page.fill("#af [name=email]", email)
    page.fill("#af [name=password]", "Farm12345")
    page.click("#ago")
    page.wait_for_selector("#of")
    page.fill("#of [name=code]", code_for(server, email))
    page.wait_for_selector("#view h1", timeout=15000)
    time.sleep(3)
    assert page.evaluate("document.fonts.check('20px \"Material Symbols Outlined\"', 'dashboard')")
    wide = page.evaluate("""[...document.querySelectorAll('.material-symbols-outlined')]
        .filter(e => e.offsetParent).filter(e => e.scrollWidth > parseFloat(getComputedStyle(e).fontSize) * 1.5)
        .map(e => e.textContent)""")
    assert wide == [], wide
    assert "could not load" not in page.inner_text("#view")
    assert not any(u.startswith(("https://fonts.", "https://cdn")) for u in blocked), blocked
    shot(page, "TC-068_cdns_blocked")


def test_tc072_ui_new_prediction_full_auto(server, browser):
    """TC-072 | UI - Automatic input | New Prediction menu -> Full auto analysis lands on the fertiliser result
    pre: Signed in, on Overview
    data: random dataset sample
    steps: 1. Click New Prediction. 2. Check the menu is fully visible and clickable. 3. Click Full auto analysis.
    expected: Menu is not clipped (it extends below the hero card and is the topmost element); the Fertiliser page opens with the crop -> fertiliser card and the suggested fertiliser (or "No fertiliser needed")."""
    page, _ = signed_in_page(browser, server)
    page.click("#newpred")
    menu = page.locator("#newpred-menu")
    assert menu.is_visible()
    hero = page.locator("#view section").first.bounding_box()
    box = menu.bounding_box()
    assert box["y"] + box["height"] > hero["y"] + hero["height"]
    assert page.evaluate("(() => { const b = document.querySelector('#np-chain').getBoundingClientRect(); return document.elementFromPoint(b.x + 20, b.y + 10).closest('#np-chain') !== null; })()")
    shot(page, "TC-072a_new_prediction_menu")
    page.click("#np-chain")
    page.wait_for_selector("text=Crop \u2192 fertiliser analysis", timeout=20000)
    res = page.inner_text("#fres").lower()
    assert page.url.endswith("#/fertiliser") and "suggested fertiliser" in res and "ask the assistant about this" in res
    shot(page, "TC-072b_fertiliser_from_chain")


def test_tc073_ui_auto_fill_pages(server, browser):
    """TC-073 | UI - Automatic input | Auto-fill from dataset on Crop, Yield and Disease pages
    pre: Signed in
    data: random dataset samples
    steps: 1. Crop page -> Auto-fill. 2. Recommend fertiliser from the crop result. 3. Yield page -> Auto-fill. 4. Disease page -> Auto-fill.
    expected: Each form fills with a real sample and the prediction runs; the dataset label or recorded yield is shown next to the result; the crop result button opens the fertiliser analysis."""
    page, _ = signed_in_page(browser, server)
    page.goto(BASE + "/#/crop"); page.wait_for_selector("#cmode")
    page.click("#cmode [data-mode=auto]")
    page.wait_for_selector("text=Dataset sample row", timeout=15000)
    assert page.input_value("#cf [name=N]") != ""
    shot(page, "TC-073a_crop_auto")
    page.click("#tofert")
    page.wait_for_selector("text=Crop \u2192 fertiliser analysis", timeout=15000)
    page.goto(BASE + "/#/yield"); page.wait_for_selector("#ymode")
    page.click("#ymode [data-mode=auto]")
    page.wait_for_selector("text=The dataset recorded", timeout=20000)
    shot(page, "TC-073b_yield_auto")
    page.goto(BASE + "/#/disease"); page.wait_for_selector("#dmode")
    page.click("#dmode [data-mode=auto]")
    page.wait_for_selector("text=Dataset label", timeout=20000)
    shot(page, "TC-073c_disease_auto")


def test_tc074_ui_farm_dialog_above_map(server, browser):
    """TC-074 | UI - Farm management | Add-farm dialog is drawn above the farm map
    pre: Signed in with a farm that has a map location
    data: -
    steps: 1. Open Farm Management (map shown). 2. Click Add farm. 3. Check what is on top at the dialog title and fields.
    expected: The dialog, not the map, is the topmost element; Save and Cancel are reachable."""
    page, _ = signed_in_page(browser, server)
    page.request.post(BASE + "/api/farms", data={"name": "field 1", "state": "Punjab", "district": "HOSHIARPUR", "lat": 31.95, "lon": 75.55, "area_ha": 1})
    page.goto(BASE + "/#/farms"); page.wait_for_selector("#fmap .leaflet-tile-pane", state="attached", timeout=15000)
    page.click("#addfarm"); page.wait_for_selector("#modal .card")
    assert page.evaluate("""(() => { const r = document.querySelector('#modal .card').getBoundingClientRect();
        return [[r.x + r.width / 2, r.y + 20], [r.x + 30, r.y + 140]].every(([x, y]) => document.elementFromPoint(x, y).closest('#modal') !== null); })()""")
    shot(page, "TC-074_farm_dialog_above_map")


def test_tc075_ui_assistant_from_result(server, browser):
    """TC-075 | UI - AI assistant | Ask the assistant from a result opens the assistant and asks about it
    pre: Signed in; Mistral API configured
    data: a fertiliser result
    steps: 1. Run a fertiliser check. 2. Click Ask the assistant. 3. Wait for the reply.
    expected: Assistant page opens, the sent question names the result, a reply appears and the conversation is listed."""
    page, _ = signed_in_page(browser, server)
    page.goto(BASE + "/#/fertiliser"); page.wait_for_selector("#ff")
    page.select_option("#ff [name=crop]", "rice")
    for k, v in {"N": 210, "P": 18, "K": 95}.items():
        page.fill(f"#ff [name={k}]", str(v))
    page.click("#fgo"); page.wait_for_selector("#fask")
    page.click("#fask")
    page.wait_for_selector(".bubble-user", timeout=10000)
    assert "fertiliser result" in page.inner_text(".bubble-user").lower()
    page.wait_for_function("document.querySelectorAll('.bubble-bot').length > 0 && !document.body.innerText.includes('Thinking')", timeout=60000)
    assert page.locator(".asst-item").count() >= 1
    shot(page, "TC-075_assistant_answer")


def test_tc079_ui_dark_mode(server, browser):
    """TC-079 | UI - Theme | Dark mode switches every surface and is remembered
    pre: Signed in
    data: -
    steps: 1. Click the moon button in the top bar. 2. Check page and card colours on Overview and Farms. 3. Reload.
    expected: html has class "dark"; page and card backgrounds are dark with light text; the choice survives a reload; the sun button switches back."""
    page, _ = signed_in_page(browser, server)
    page.click("#theme-btn")
    time.sleep(1.5)
    lum = """(el) => { const c = getComputedStyle(el).backgroundColor.match(/\\d+/g).map(Number); return (0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]) / 255; }"""
    assert page.evaluate("document.documentElement.classList.contains('dark')")
    assert page.eval_on_selector("body", lum) < 0.2 and page.eval_on_selector("#view .card", lum) < 0.2
    txt = page.eval_on_selector("#view h1", "(e) => getComputedStyle(e).color.match(/\\d+/g).map(Number)")
    assert sum(txt[:3]) / 3 > 180
    shot(page, "TC-079a_dark_overview")
    page.goto(BASE + "/#/farms"); time.sleep(2)
    page.reload(); time.sleep(3)
    assert page.evaluate("document.documentElement.classList.contains('dark')")
    shot(page, "TC-079b_dark_after_reload")
    page.click("#theme-btn"); time.sleep(1)
    assert not page.evaluate("document.documentElement.classList.contains('dark')")


def test_tc080_ui_translate_14_languages(server, browser):
    """TC-080 | UI - Language | The interface translates into the chosen language and back
    pre: Signed in; Azure Translator configured
    data: languages Tamil, Bengali, Hindi, then English
    steps: 1. Pick Tamil in the top bar. 2. Check the sidebar and page text. 3. Repeat for Bengali and Hindi. 4. Pick English.
    expected: The language picker lists 15 languages; sidebar and headings appear in the chosen script; the user's name is not translated; icons stay icons; English restores the original text."""
    page, _ = signed_in_page(browser, server, name="Asha Devi")
    assert page.locator("#lang-sel option").count() == 15
    scripts = {"ta": ("\u0b80", "\u0bff"), "bn": ("\u0980", "\u09ff"), "hi": ("\u0900", "\u097f")}
    for code, (lo, hi) in scripts.items():
        page.select_option("#lang-sel", code)
        page.wait_for_function(f"[...document.querySelector('#sidebar nav').innerText].some(ch => ch >= '{lo}' && ch <= '{hi}')", timeout=20000)
        time.sleep(2.5)
        assert "Asha" in page.inner_text("#view h1")
        assert page.evaluate("[...document.querySelectorAll('.material-symbols-outlined')].every(e => /^[a-z_0-9]+$/.test(e.textContent.trim()))")
        shot(page, f"TC-080_{code}")
    page.select_option("#lang-sel", "en")
    time.sleep(2)
    assert "Crop Recommendation" in page.inner_text("#sidebar nav")


def test_tc081_ui_switch_keeps_results(server, browser):
    """TC-081 | UI - Theme & language | Switching theme or language keeps results and inputs on screen
    pre: Signed in; a crop result is shown
    data: auto-filled crop sample
    steps: 1. Run Auto-fill on Crop Recommendation. 2. Switch to dark mode. 3. Switch the language to Tamil. 4. Switch back to English.
    expected: The same result and input values stay after every switch (no reload, no reset); dark mode uses neutral near-black surfaces; English text is restored exactly."""
    page, _ = signed_in_page(browser, server)
    page.goto(BASE + "/#/crop"); page.wait_for_selector("#cmode")
    page.click("#cmode [data-mode=auto]")
    page.wait_for_selector("text=Dataset sample row", timeout=15000)
    time.sleep(1)
    crop = page.inner_text("#cres .text-4xl")
    before = page.inner_text("#cres")
    n_value = page.input_value("#cf [name=N]")
    page.click("#theme-btn"); time.sleep(0.8)
    assert page.inner_text("#cres .text-4xl") == crop
    r, g, b = page.eval_on_selector("body", "(e) => getComputedStyle(e).backgroundColor.match(/\\d+/g).map(Number)")[:3]
    assert max(r, g, b) < 30 and abs(g - r) < 8          # near-black and neutral, not green-tinted
    shot(page, "TC-081a_dark_keeps_result")
    page.select_option("#lang-sel", "ta")
    page.wait_for_function("[...document.querySelector('#cres').innerText].some(ch => ch >= '\\u0b80' && ch <= '\\u0bff')", timeout=20000)
    assert page.input_value("#cf [name=N]") == n_value
    page.select_option("#lang-sel", "en"); time.sleep(1.5)
    assert page.inner_text("#cres") == before
    page.click("#theme-btn"); time.sleep(0.5)


def test_tc083_ui_chat_follows_language(server, browser):
    """TC-083 | UI - AI assistant | An open English conversation switches to the chosen language
    pre: Signed in; Mistral and Azure Translator configured
    data: an English answer, then language Tamil
    steps: 1. Ask a question in English. 2. Pick Tamil in the top bar. 3. Toggle Show original.
    expected: The earlier answer is shown in Tamil with a Show original button; the toggle brings the English back; nothing reloads."""
    page, _ = signed_in_page(browser, server)
    page.goto(BASE + "/#/assistant"); page.wait_for_selector("#cmsg")
    page.fill("#cmsg", "In one sentence, what is crop rotation?"); page.press("#cmsg", "Enter")
    page.wait_for_function("document.querySelectorAll('.bubble-bot').length > 0 && !document.body.innerText.includes('Thinking')", timeout=60000)
    english = page.inner_text(".prose-chat")
    page.select_option("#lang-sel", "ta")
    page.wait_for_selector("[data-orig]", timeout=30000)
    assert any("\u0b80" <= ch <= "\u0bff" for ch in page.inner_text(".prose-chat"))
    shot(page, "TC-083_chat_in_tamil")
    page.click("[data-orig]")
    assert page.inner_text(".prose-chat") == english
    page.select_option("#lang-sel", "en")


def test_tc067_ui_forgot_password(server, browser):
    """TC-067 | UI - Authentication | Forgot password screen
    pre: Account exists
    data: e-mail, new password Newpass123
    steps: 1. Sign in page -> Forgot password?. 2. Enter e-mail and new password. 3. Send code. 4. Type the code.
    expected: Code screen says "set your new password"; after the code the user is signed in."""
    page, email = signed_in_page(browser, server)
    page.click("#logout")
    page.wait_for_selector("#forgot")
    page.click("#forgot")
    page.fill("#ff2 [name=email]", email)
    page.fill("#ff2 [name=new_password]", "Newpass123")
    shot(page, "TC-067a_forgot_form")
    page.click("#fgo")
    page.wait_for_selector("#of")
    assert "set your new password" in page.inner_text("#of")
    time.sleep(0.5)
    lines = [json.loads(l) for l in server.read_text().splitlines() if json.loads(l)["to"] == email]
    page.fill("#of [name=code]", lines[-1]["code"])
    page.wait_for_selector("#view h1", timeout=15000)
    shot(page, "TC-067b_signed_in_after_reset")
