"""Low-fidelity wireframes of every screen, taken from the real layout: the app runs on a throwaway
database with demo data, a wireframe stylesheet is injected (greyscale, outlines, hatched charts,
image placeholders) and each region gets a numbered marker. Writes PNGs + regions.json to wf/."""
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
OUT = Path(__file__).resolve().parent / "wf"
OUT.mkdir(exist_ok=True)
APP, HOOK = 8171, 8172
BASE = f"http://127.0.0.1:{APP}"
LEAF = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"

CSS = """
*:not(.material-symbols-outlined){font-family:'Segoe Print','Comic Sans MS',cursive !important}
*{box-shadow:none !important;text-shadow:none !important;
  transition:none !important;animation:none !important}
html,body,#root,main,aside,header,section,div,form,nav,span,a,label,td,th,tr,table,p,h1,h2,h3,li,ul,details,summary{
  background:transparent !important;background-image:none !important;color:#555 !important}
body{background:#fff !important}
.card,aside#sidebar,header{border:1.6px solid #9a9a9a !important;border-radius:8px !important;background:#fff !important}
input,select,textarea{border:1.4px solid #9a9a9a !important;background:#fafafa !important;color:#777 !important;border-radius:4px !important}
.btn{border:1.4px solid #777 !important;background:#f1f1f1 !important;color:#444 !important;border-radius:5px !important}
.btn-primary{background:#d9d9d9 !important}
.badge,.nav-link.active{background:#eee !important;border:1px dashed #999 !important}
img,svg:not(.keep){filter:grayscale(1) opacity(.35) !important}
canvas{opacity:0 !important}
.wf-ph{position:absolute;pointer-events:none;border:1.4px dashed #999;border-radius:6px;
  background:repeating-linear-gradient(45deg,#f3f3f3 0 8px,#fff 8px 16px);z-index:5}
.material-symbols-outlined{color:#aaa !important}
.wf-n{position:absolute;z-index:99;width:26px;height:26px;border-radius:50%;background:#eb6834 !important;color:#fff !important;
  font:700 13px/26px Arial !important;text-align:center;box-shadow:0 0 0 3px #fff !important}
"""

ANNOTATE = """
() => {
  document.querySelectorAll('.wf-ph,.wf-n').forEach(e => e.remove());
  document.querySelectorAll('canvas').forEach(c => { const r = c.getBoundingClientRect(); if (r.width < 20) return;
    const d = document.createElement('div'); d.className = 'wf-ph';
    Object.assign(d.style, {left: (r.left + scrollX) + 'px', top: (r.top + scrollY) + 'px', width: r.width + 'px', height: r.height + 'px'});
    document.body.appendChild(d); });
  const regions = []; const done = [];
  const add = (el, label) => { if (!el) return; const r = el.getBoundingClientRect(); if (r.width < 40 || r.height < 20) return; if (done.some(d => d.contains(el) || el.contains(d))) return; done.push(el);
    const n = regions.length + 1; const b = document.createElement('div'); b.className = 'wf-n'; b.textContent = n;
    Object.assign(b.style, {left: (r.left + scrollX - 8) + 'px', top: (r.top + scrollY - 8) + 'px'}); document.body.appendChild(b);
    regions.push({n, label: (label || '').replace(/\\s+/g, ' ').trim().slice(0, 90)}); };
  const view = document.querySelector('#view');
  if (!view) { document.querySelectorAll('form .field, form button, form h2').forEach(e => add(e, e.innerText.split('\\n')[0])); return regions; }
  add(document.querySelector('#sidebar'), 'Sidebar navigation');
  add(document.querySelector('header') || document.querySelector('#crumb')?.parentElement, 'Top bar');
  
  const cards = [...view.querySelectorAll('.card')].filter(c => !c.parentElement.closest('.card') && c.getBoundingClientRect().width > 150 && c.getBoundingClientRect().height > 60);
  cards.slice(0, 9).forEach(c => { const t = c.querySelector('h2,h3,label,.font-semibold'); add(c, t ? t.innerText.split('\\n')[0] : 'Panel'); });
  return regions;
}
"""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="agrisense_wf_"))
    log = tmp / "mail.jsonl"; log.write_text("")
    hook = subprocess.Popen([sys.executable, str(ROOT / "tests" / "fake_mailbox.py"), str(HOOK), str(log), "s"])
    env = {**os.environ, "AGRISENSE_STORAGE": str(tmp / "db"), "OTP_WEBHOOK_URL": f"http://127.0.0.1:{HOOK}/h",
           "OTP_SHARED_SECRET": "s"}
    app = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(APP)], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            if httpx.get(BASE + "/healthz").status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    regions = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)

            def snap(page, name, full=False):
                time.sleep(1.2)
                page.add_style_tag(content=CSS)
                time.sleep(0.3)
                regions[name] = page.evaluate(ANNOTATE)
                page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)

            ctx = b.new_context(viewport={"width": 1366, "height": 860}, device_scale_factor=1.4)
            pg = ctx.new_page()
            pg.goto(BASE + "/"); time.sleep(1.5); snap(pg, "01_sign_in")
            pg.goto(BASE + "/"); time.sleep(1.2); pg.click("#swap"); snap(pg, "02_sign_up")
            pg.goto(BASE + "/"); time.sleep(1.2); pg.click("#swap")
            email = "wireframe@agrisense.test"
            pg.fill("#af [name=name]", "Demo Farmer"); pg.fill("#af [name=email]", email); pg.fill("#af [name=password]", "Farm12345")
            pg.click("#ago"); pg.wait_for_selector("#of"); snap(pg, "03_email_code")
            code = json.loads(log.read_text().splitlines()[-1])["code"]
            pg.goto(BASE + "/"); time.sleep(0.5)
            # finish sign-up through the API in the same browser context, then seed demo data
            r = ctx.request.post(BASE + "/api/auth/register", data={"name": "Demo Farmer", "email": "demo@agrisense.test",
                                                                   "password": "Farm12345", "state": "Punjab", "district": "Ludhiana"})
            time.sleep(0.4)
            code = json.loads(log.read_text().splitlines()[-1])["code"]
            ctx.request.post(BASE + "/api/auth/otp/verify", data={"challenge_id": r.json()["challenge_id"], "code": code})
            ctx.request.post(BASE + "/api/farms", data={"name": "North Field", "state": "Punjab", "district": "LUDHIANA",
                                                         "village": "Ayali Kalan", "lat": 30.9, "lon": 75.85, "area_ha": 3,
                                                         "soil_type": "Loamy", "current_crop": "Wheat", "irrigation": "Tube well"})
            ctx.request.post(BASE + "/api/crop/recommend", data={"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82,
                                                                  "ph": 6.5, "rainfall": 203, "farm_id": 1})
            ctx.request.post(BASE + "/api/yield/predict", data={"state": "Punjab", "district": "LUDHIANA", "crop": "Wheat",
                                                                 "season": "Rabi", "year": 2025, "area_ha": 3, "farm_id": 1})
            ctx.request.post(BASE + "/api/fertiliser", data={"basis": "soil_test", "crop": "rice", "N": 210, "P": 18, "K": 95})
            leaf = sorted((LEAF / "Tomato___Early_blight").iterdir())[5]
            ctx.request.post(BASE + "/api/disease", multipart={"image": {"name": "leaf.jpg", "mimeType": "image/jpeg",
                                                                          "buffer": leaf.read_bytes()}})
            ctx.request.post(BASE + "/api/chat", multipart={"message": "Which crop suits my North Field this rabi season?", "lang": "en"})
            pg.goto(BASE + "/#/overview"); pg.reload(); time.sleep(4); snap(pg, "04_overview", True)
            pg.goto(BASE + "/#/crop"); time.sleep(2)
            for k, v in {"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82, "ph": 6.5, "rainfall": 203}.items():
                pg.fill(f"#cf [name={k}]", str(v))
            pg.click("#cgo"); time.sleep(3); snap(pg, "05_crop", True)
            pg.goto(BASE + "/#/yield"); time.sleep(2.5)
            pg.select_option("#yf [name=crop]", label="Wheat"); time.sleep(0.5)
            pg.select_option("#yf [name=season]", label="Rabi"); pg.fill("#yf [name=year]", "2025"); pg.fill("#yf [name=area_ha]", "3")
            pg.click("#yf button.btn-primary"); time.sleep(4); snap(pg, "06_yield", True)
            pg.goto(BASE + "/#/fertiliser"); time.sleep(2.5)
            pg.select_option("#ff [name=crop]", "rice")
            for k, v in {"N": 210, "P": 18, "K": 95}.items():
                pg.fill(f"#ff [name={k}]", str(v))
            pg.click("#ff button.btn-primary"); time.sleep(3); snap(pg, "07_fertiliser", True)
            pg.goto(BASE + "/#/disease"); time.sleep(2)
            pg.set_input_files("#file", str(leaf)); pg.click("#dgo"); time.sleep(4); snap(pg, "08_disease", True)
            pg.goto(BASE + "/#/assistant"); time.sleep(3)
            first = pg.query_selector("#view [data-chat], #view .chat-item, #view aside a, #view li")
            snap(pg, "09_assistant")
            for name, route, wait in [("10_weather", "weather", 6), ("11_soil", "soil", 12), ("12_farms", "farms", 4),
                                      ("13_history", "history", 3), ("14_reports", "reports", 4), ("15_settings", "settings", 3)]:
                pg.goto(BASE + f"/#/{route}"); time.sleep(wait); snap(pg, name, True)
            m = b.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2,
                              storage_state=ctx.storage_state())
            mp = m.new_page()
            for name, route in [("m1_overview", "overview"), ("m2_crop", "crop"), ("m3_disease", "disease")]:
                mp.goto(BASE + f"/#/{route}"); mp.reload(); time.sleep(4); snap(mp, name)
            b.close()
    finally:
        app.terminate(); hook.terminate()
    (OUT / "regions.json").write_text(json.dumps(regions, indent=1, ensure_ascii=False))
    print("captured", len(regions))


if __name__ == "__main__":
    main()
