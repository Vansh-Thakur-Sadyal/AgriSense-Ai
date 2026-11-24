"""Capture screenshots of the running app for the report.

Starts nothing itself: run uvicorn on PORT with AGRISENSE_STORAGE pointing at a throwaway folder,
then run this. Uses the installed Microsoft Edge through Playwright (no browser download).
A demo account is created in that throwaway database only.
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8151
LEAF = sys.argv[2]
OUT = Path(__file__).resolve().parent / "screens"
OUT.mkdir(exist_ok=True)
BASE = f"http://127.0.0.1:{PORT}"


def shot(page, name, wait=2.5, full=False):
    time.sleep(wait)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("saved", name, flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
    page = ctx.new_page()
    page.goto(BASE + "/")
    shot(page, "01_login", 2)
    r = page.request.post(BASE + "/api/auth/register", data={
        "name": "Demo Farmer", "email": "demo@agrisense.test", "password": "DemoFarm123",
        "state": "Punjab", "district": "Ludhiana"})
    if not r.ok:
        r = page.request.post(BASE + "/api/auth/login", data={"identifier": "demo@agrisense.test", "password": "DemoFarm123"})
    assert r.ok, r.text()
    r = page.request.post(BASE + "/api/farms", data={
        "name": "North Field", "state": "Punjab", "district": "LUDHIANA", "village": "Ayali Kalan",
        "lat": 30.90, "lon": 75.85, "area_ha": 3, "soil_type": "Loamy", "current_crop": "Wheat",
        "irrigation": "Tube well"})
    assert r.ok, r.text()
    page.goto(BASE + "/#/overview"); page.reload(); time.sleep(3)
    page.goto(BASE + "/#/crop"); time.sleep(2.5)
    for k, v in {"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82, "ph": 6.5, "rainfall": 203}.items():
        page.fill(f"#cf [name={k}]", str(v))
    page.click("#cgo")
    shot(page, "03_crop", 4, full=True)
    page.goto(BASE + "/#/yield"); time.sleep(3)
    page.click("#yf button[type=submit], #yf button.btn-primary")
    shot(page, "04_yield", 5, full=True)
    page.goto(BASE + "/#/fertiliser"); time.sleep(2.5)
    page.click("#fchain")  # full auto analysis: dataset soil sample -> crop model -> fertiliser model
    page.wait_for_selector("text=Suggested fertiliser", timeout=30000)
    shot(page, "05_fertiliser", 3, full=True)
    page.goto(BASE + "/#/disease"); time.sleep(2.5)
    page.set_input_files("#file", LEAF)
    time.sleep(1)
    page.click("#dgo")
    shot(page, "06_disease", 5, full=True)
    page.goto(BASE + "/#/weather"); shot(page, "07_weather", 7, full=True)
    page.goto(BASE + "/#/soil"); shot(page, "08_soil", 12, full=True)
    page.goto(BASE + "/#/reports"); shot(page, "09_reports", 5, full=True)
    page.goto(BASE + "/#/history"); shot(page, "10_history", 3)
    page.goto(BASE + "/#/farms"); shot(page, "11_farms", 4)
    page.goto(BASE + "/#/overview"); shot(page, "02_overview", 6, full=True)
    page.goto(BASE + "/#/assistant"); time.sleep(2.5)
    box = page.locator("textarea, input[type=text]").last
    box.fill("My wheat leaves have yellow stripes of powder. What should I check first?")
    box.press("Enter")
    shot(page, "12_assistant", 15)
    b.close()
