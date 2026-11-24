"""Phone-size screenshots (375 x 812, light theme, English + one Hindi screen) of every main screen,
taken from the real app on a throwaway database with demo data. Writes PNGs to mobile/."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "mobile"
OUT.mkdir(exist_ok=True)
APP, HOOK = 8191, 8192
BASE = f"http://127.0.0.1:{APP}"
LEAF = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"


def main():
    tmp = Path(tempfile.mkdtemp(prefix="agrisense_mobile_"))
    log = tmp / "mail.jsonl"; log.write_text("")
    hook = subprocess.Popen([sys.executable, str(ROOT / "tests" / "fake_mailbox.py"), str(HOOK), str(log), "s"])
    env = {**os.environ, "AGRISENSE_STORAGE": str(tmp / "db"), "OTP_WEBHOOK_URL": f"http://127.0.0.1:{HOOK}/h", "OTP_SHARED_SECRET": "s"}
    app = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(APP)], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            if httpx.get(BASE + "/healthz").status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)
            ctx = b.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=3, is_mobile=True, has_touch=True,
                                user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36")
            ctx.add_init_script("try { localStorage.setItem('theme','light'); if (!localStorage.getItem('lang')) localStorage.setItem('lang','en'); } catch (e) {}")
            pg = ctx.new_page()

            def snap(name, wait=1.5, full=False):
                time.sleep(wait)
                pg.screenshot(path=str(OUT / f"{name}.png"), full_page=full)

            pg.goto(BASE + "/"); snap("01_sign_in", 2)
            pg.click("#swap"); snap("02_sign_up", 1)
            pg.fill("#af [name=name]", "Asha Devi"); pg.fill("#af [name=email]", "asha@agrisense.test"); pg.fill("#af [name=password]", "Farm12345")
            pg.click("#ago"); pg.wait_for_selector("#of"); snap("03_email_code", 1)
            code = json.loads(log.read_text().splitlines()[-1])["code"]
            pg.fill("#of [name=code]", code); pg.wait_for_selector("#view h1", timeout=15000)
            H = {"data": None}
            req = ctx.request
            req.post(BASE + "/api/farms", data={"name": "North Field", "state": "Punjab", "district": "LUDHIANA", "village": "Ayali Kalan",
                                                 "lat": 30.9, "lon": 75.85, "area_ha": 3, "soil_type": "Loamy", "current_crop": "Wheat", "irrigation": "Tube well"})
            req.post(BASE + "/api/yield/predict", data={"state": "Punjab", "district": "LUDHIANA", "crop": "Wheat", "season": "Rabi", "year": 2025, "area_ha": 3, "farm_id": 1})
            leaf = sorted((LEAF / "Tomato___Early_blight").iterdir())[5]
            pg.goto(BASE + "/#/overview"); pg.reload(); snap("04_home", 5)
            pg.click("#newpred"); snap("05_new_prediction_menu", 1)
            pg.click("#np-chain"); pg.wait_for_selector("text=Crop → fertiliser analysis", timeout=20000)
            pg.evaluate("document.querySelector('#fres').scrollIntoView()"); snap("06_auto_analysis_result", 1.5)
            pg.goto(BASE + "/#/crop"); time.sleep(2); snap("07_crop_form", 0.5)
            pg.click("#cmode [data-mode=auto]"); pg.wait_for_selector("text=Dataset sample row", timeout=15000)
            pg.evaluate("document.querySelector('#cres').scrollIntoView()"); snap("08_crop_result", 1.5)
            pg.goto(BASE + "/#/yield"); time.sleep(2)
            pg.select_option("#yf [name=state]", "Punjab"); time.sleep(1); pg.select_option("#yf [name=district]", "LUDHIANA")
            pg.select_option("#yf [name=crop]", label="Wheat"); pg.select_option("#yf [name=season]", label="Rabi"); pg.fill("#yf [name=year]", "2025"); pg.fill("#yf [name=area_ha]", "3")
            pg.click("#ygo"); time.sleep(4); pg.evaluate("document.querySelector('#yres').scrollIntoView()"); snap("09_yield_result", 1)
            pg.goto(BASE + "/#/fertiliser"); time.sleep(2)
            pg.select_option("#ff [name=crop]", "rice")
            for k, v in {"N": 210, "P": 18, "K": 95}.items():
                pg.fill(f"#ff [name={k}]", str(v))
            pg.click("#fgo"); time.sleep(3); pg.evaluate("document.querySelector('#fres').scrollIntoView()"); snap("10_fertiliser_result", 1)
            pg.goto(BASE + "/#/disease"); time.sleep(2); snap("11_disease_upload", 0.5)
            pg.set_input_files("#file", str(leaf)); pg.click("#dgo"); time.sleep(4)
            pg.evaluate("document.querySelector('#dres').scrollIntoView()"); snap("12_disease_result", 1)
            pg.goto(BASE + "/#/assistant"); snap("13_assistant_welcome", 3)
            pg.fill("#cmsg", "Which crop suits my North Field this rabi season?"); pg.press("#cmsg", "Enter")
            pg.wait_for_function("document.querySelectorAll('.bubble-bot').length > 0 && !document.body.innerText.includes('Thinking')", timeout=60000)
            snap("14_assistant_chat", 1.5)
            pg.goto(BASE + "/#/weather"); snap("15_weather", 6)
            pg.goto(BASE + "/#/soil"); snap("16_soil", 12)
            pg.goto(BASE + "/#/farms"); snap("17_farms", 4)
            pg.goto(BASE + "/#/history"); snap("18_history", 3)
            pg.goto(BASE + "/#/settings"); snap("19_settings", 2)
            pg.goto(BASE + "/#/overview"); time.sleep(3); pg.click("#menu"); snap("20_navigation_drawer", 1)
            pg.goto(BASE + "/#/overview"); pg.reload(); time.sleep(2)
            pg.select_option("#lang-sel", "hi"); snap("21_home_hindi", 6)
            pg.select_option("#lang-sel", "en"); time.sleep(1)
            b.close()
    finally:
        app.terminate(); hook.terminate()
    print("captured", len(list(OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
