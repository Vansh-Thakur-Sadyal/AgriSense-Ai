"""Deployment guide: how AgriSense AI goes from the laptop to the Hostinger VPS, how updates are pushed,
how n8n sends the sign-in codes, and how local and server copies are kept apart. Every command and path
is the one actually used; secret values are never shown.
Usage: python build_deploy_guide.py <out.docx>"""
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
import content as C  # noqa: E402

OUT = Path(sys.argv[1])
DG = HERE / "out" / "deploy"
FIGS = ROOT / "docs" / "figs"
UML = ROOT / "docs" / "submission" / "figs"
INK, TEAL, GREY = RGBColor(0x14, 0x2A, 0x4C), RGBColor(0x00, 0x7A, 0x7E), RGBColor(0x60, 0x68, 0x70)
FONT, MONO = "Times New Roman", "Consolas"
VPS, HOST, KEY = "187.127.191.13", "ai.software.microeagle.online", "~/.ssh/nexus_vps"

doc = Document()
st = doc.styles["Normal"]
st.font.name = FONT; st.font.size = Pt(11.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(6); st.paragraph_format.line_spacing = 1.12
for name, size, color in (("Heading 1", 18, INK), ("Heading 2", 13.5, TEAL), ("Heading 3", 12, INK)):
    h = doc.styles[name]
    h.font.name = FONT; h.font.size = Pt(size); h.font.bold = True; h.font.color.rgb = color
    rf = h.element.rPr.rFonts
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), FONT)
    h.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 9)
    h.paragraph_format.space_after = Pt(5); h.paragraph_format.keep_with_next = True
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2); sec.top_margin = sec.bottom_margin = Cm(2.0)
WIDTH = 21.0 - 4.4
FIG, TAB = [0], [0]


def runs(p, text, size=None, bold=False, italic=False, color=None):
    """**bold** and `code` spans."""
    import re
    for tok in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not tok:
            continue
        r = p.add_run(tok.strip("*`") if tok[:1] in "*`" and len(tok) > 2 else tok)
        r.bold = bold or tok.startswith("**")
        r.italic = italic
        if tok.startswith("`"):
            r.font.name = MONO; r._element.rPr.rFonts.set(qn("w:hAnsi"), MONO); r.font.size = Pt((size or 11.5) - 1.5)
            r.font.color.rgb = RGBColor(0x9C, 0x27, 0x50)
        elif size:
            r.font.size = Pt(size)
        if color and not tok.startswith("`"):
            r.font.color.rgb = color
    return p


def para(text="", size=None, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=None, color=None, style=None):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if text:
        runs(p, text, size, bold, italic, color)
    return p


def h1(t, new_page=True):
    h = doc.add_heading(t, 1)
    h.paragraph_format.page_break_before = new_page
    return h


def h2(t):
    return doc.add_heading(t, 2)


def bullets(items):
    for t in items:
        runs(para(style="List Bullet", after=2), t)


def steps(items):
    for i, t in enumerate(items, 1):
        p = para(after=3)
        p.paragraph_format.left_indent = Cm(0.8); p.paragraph_format.first_line_indent = Cm(-0.65)
        runs(p, f"**{i}.**  " + t)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), fill)
    tcPr.append(sh)


def code(text, title=None):
    """Dark terminal-style block."""
    t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0); shade(c, "1E2430"); c.width = Cm(WIDTH)
    first = True
    if title:
        p = c.paragraphs[0]; first = False
        r = p.add_run(title); r.font.name = MONO; r.font.size = Pt(8.5); r.font.color.rgb = RGBColor(0x8F, 0xD3, 0xC8); r.bold = True
        p.paragraph_format.space_after = Pt(2)
    for ln in text.strip("\n").split("\n"):
        p = c.paragraphs[0] if first else c.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
        r = p.add_run(ln if ln else " ")
        r.font.name = MONO; r._element.rPr.rFonts.set(qn("w:hAnsi"), MONO); r.font.size = Pt(8.8)
        r.font.color.rgb = RGBColor(0x9A, 0xA5, 0xB1) if ln.lstrip().startswith("#") else RGBColor(0xE8, 0xEC, 0xF1)
    for p in c.paragraphs[:-1]:
        p.paragraph_format.keep_with_next = True
    para(after=4)


def caption(kind, text):
    n = FIG if kind == "Figure" else TAB
    n[0] += 1
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    r = p.add_run(f"{kind} {n[0]}. "); r.bold = True; r.font.size = Pt(10)
    r = p.add_run(text); r.italic = True; r.font.size = Pt(10)
    if kind == "Table":
        p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(3)


def table(rows, fracs, title=None, size=10):
    if title:
        caption("Table", title)
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j); c.width = Cm(WIDTH * fracs[j])
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            runs(p, str(v), size, bold=(i == 0), color=RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else None)
            if i == 0:
                shade(c, "142A4C")
            elif i % 2 == 0:
                shade(c, "EAF4F4")
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); t.rows[0]._tr.get_or_add_trPr().append(h)
    if len(rows) <= 12:
        for r in t.rows[:-1]:
            for c in r.cells:
                for p in c.paragraphs:
                    p.paragraph_format.keep_with_next = True
    para(after=4)


def figure(path, text, width=WIDTH):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=2); p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width))
    caption("Figure", text)


def note(title, lines, fill="EAF4F4", color=TEAL):
    t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0); shade(c, fill); c.width = Cm(WIDTH)
    p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(2); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    runs(p, title, 11, bold=True, color=color)
    for ln in lines:
        q = c.add_paragraph(); q.paragraph_format.space_after = Pt(1); q.paragraph_format.left_indent = Cm(0.4)
        q.alignment = WD_ALIGN_PARAGRAPH.LEFT
        runs(q, "\u2022  " + ln, 10.5)
    para(after=4)


def warn(title, lines):
    note(title, lines, fill="FFF4E0", color=RGBColor(0xA4, 0x5A, 0x00))


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


# ================================================================== cover
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=26)
p.add_run().add_picture(str(HERE / "niit_logo.png"), width=Cm(10.5))
para("DEPLOYMENT GUIDE", 14, True, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL, after=6)
para("AgriSense AI on a VPS", 28, True, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=4)
para("From the laptop to the live server: Docker, database, Traefik, HTTPS, n8n, updates and day-to-day handling",
     14, align=WD_ALIGN_PARAGRAPH.CENTER, color=INK, after=20)
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=20)
p.add_run().add_picture(str(DG / "big_picture.png"), width=Cm(15.5))
for n, e in C.TEAM:
    para(f"{n}  ({e})", 12, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
para(f"Live system: https://{HOST}", 11, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)

s2 = doc.add_section(WD_SECTION.NEW_PAGE)
s2.footer.is_linked_to_previous = False
fp = s2.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER; field(fp, "PAGE")
para("Contents", 18, True, color=INK, after=8)
field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')

# ================================================================== 1 big picture
h1("1. The Big Picture")
para("AgriSense AI is written and tested on a Windows laptop in VS Code, then copied to a rented Linux server (a "
     "**VPS**, virtual private server) where it runs inside a **Docker container**. A reverse proxy called "
     "**Traefik** receives every visitor on the internet, adds HTTPS, and passes the request to the container. The "
     "container keeps its database in a **Docker volume** so data survives every update. Sign-in codes are e-mailed "
     "by an **n8n** workflow that runs on the same server. The Android app talks to the same server address.")
figure(DG / "big_picture.png", "Everything in one view: laptop, upload, VPS, container, Traefik, database, n8n and users.")
table([["Piece", "What it is", "Where"],
       ["Laptop", "Windows 11, VS Code, Python venv, Git Bash, Android Studio", f"V:\\Niit University\\Ai and Software Engg"],
       ["VPS", "Hostinger, Ubuntu 24.04, 2 vCPU, 8 GB RAM, Docker 29, Compose v5", VPS],
       ["Domain", "Sub-domain of microeagle.online (Hostinger DNS)", HOST],
       ["Container", "Image agrisense:local, Python 3.12, 2 Uvicorn workers", "/opt/stacks/agrisense"],
       ["Database", "SQLite file agrisense.db inside a Docker volume", "agrisense_agrisense_data"],
       ["Proxy + HTTPS", "Traefik with Let's Encrypt certificates", "/opt/stacks/traefik/dynamic/agrisense.yml"],
       ["E-mail codes", "n8n workflow AgriSense_OTP_Delivery", "container n8n-kmar-n8n-1"],
       ["Secrets", "API keys and the n8n shared secret (values never shown)", "/opt/stacks/agrisense/config/api_keys.env"]],
      [0.17, 0.48, 0.35], "The parts and where they live", 9.5)
h2("1.1 Words used in this guide")
table([["Term", "Meaning"],
       ["VPS", "A rented virtual server on the internet that you control fully (root access)"],
       ["SSH", "Secure remote login to the VPS. We log in with a private key file, not a password"],
       ["scp", "Copies a file to the VPS over SSH"],
       ["Docker image", "A packaged app with its Python version and libraries, built from the Dockerfile"],
       ["Container", "A running copy of an image, isolated from the rest of the server"],
       ["Volume", "Storage owned by Docker that is kept when a container is rebuilt"],
       ["Docker Compose", "A YAML file that says how to build and run the container (ports, volumes, networks)"],
       ["Reverse proxy", "A program in front of all apps that routes each domain to the right app (Traefik here)"],
       ["DNS A record", "Tells the internet which IP address a domain name points to"],
       ["Webhook", "A URL that another program calls to trigger work (n8n's e-mail workflow)"]],
      [0.22, 0.78], "Glossary", 9.5)

# ================================================================== 2 local
h1("2. Working Locally: VS Code and the Laptop")
para("All changes start on the laptop. The project folder is opened in **VS Code**, which is used for editing, the "
     "terminal (Git Bash) and running tests. Nothing is ever edited directly on the server.")
code(r"""V:\Niit University\Ai and Software Engg
|-- app\                  # the web app: FastAPI server + web dashboard
|   |-- main.py           # all API routes
|   |-- ml.py, fertiliser.py, assistant.py, otp.py, db.py, external.py, translate.py
|   |-- models\           # trained models + model cards (JSON)
|   |-- static\           # index.html, app.js, styles.css, fonts, vendor libraries
|   `-- storage\          # LOCAL database only (never uploaded)
|-- ml\                   # training scripts
|-- tests\                # 88 pytest tests + load test
|-- config\api_keys.env   # secrets (never uploaded with the code, never committed)
|-- Dockerfile, docker-compose.yml, requirements.txt
`-- deploy\agrisense.yml  # the Traefik route file""", "Project folder on the laptop")
h2("2.1 Run the app locally")
code(r"""cd "V:\Niit University\Ai and Software Engg"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --port 8150 --reload
# open http://127.0.0.1:8150""", "VS Code terminal (first time)")
para("`--reload` restarts the server whenever a file is saved, so a change in VS Code shows up after a browser "
     "refresh. Locally `config/api_keys.env` has the Mistral and Azure keys but **no OTP keys**, so the app "
     "signs in with password only; that keeps local testing from sending real e-mails.")
h2("2.2 Test before every upload")
code(r"""python -m pytest tests -v        # 88 tests: API, models, live services, Edge UI
# all must pass before a release is packaged""", "Run the test suite")
h2("2.3 The Android app during development")
para("The Android project points at a server address set in `android/gradle.properties` (`agrisense.apiBase`). For "
     "phone testing it pointed at a local test server with a throwaway account; the live build points at "
     f"`https://{HOST}`. The app has no back end of its own, so a server update reaches the app immediately.")
figure(DG / "local_vs_vps.png", "What differs between the laptop and the VPS.", width=15)

# ================================================================== 3 preparing
h1("3. Preparing the App for the Server")
h2("3.1 The Dockerfile, line by line")
code("""FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \\
    AGRISENSE_STORAGE=/app/storage AGRISENSE_SECURE_COOKIE=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
RUN useradd -u 10001 -m agri && mkdir -p /app/storage /app/config && chown -R agri:agri /app/storage
USER agri
EXPOSE 8150
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8150/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8150", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]""",
     "Dockerfile")
table([["Line", "Why it is there"],
       ["FROM python:3.12-slim", "Small official Python image; the same Python version as on the laptop"],
       ["AGRISENSE_STORAGE=/app/storage", "The app writes its database here, which is where the volume is mounted"],
       ["AGRISENSE_SECURE_COOKIE=1", "Sign-in cookie is sent only over HTTPS on the server"],
       ["libgomp1", "System library LightGBM needs to run"],
       ["COPY requirements.txt, then pip install", "Libraries are installed in their own layer, so a code-only change rebuilds fast"],
       ["useradd -u 10001 ... USER agri", "The app runs as a normal user, not root, so a bug cannot take over the server"],
       ["HEALTHCHECK /healthz", "Docker asks the app every 30 s if it is alive and marks it healthy or unhealthy"],
       ["--host 0.0.0.0", "Listen on all container interfaces, otherwise the published port cannot reach it"],
       ["--workers 2", "Two processes, one per CPU core"],
       ["--proxy-headers", "Trust Traefik's headers so the app sees the visitor's real IP and HTTPS"]],
      [0.36, 0.64], "What each Dockerfile line does", 9.5)
h2("3.2 docker-compose.yml")
code("""services:
  agrisense:
    build: .
    image: agrisense:local
    container_name: agrisense
    restart: unless-stopped
    ports:
      - "127.0.0.1:8150:8150"
    volumes:
      - agrisense_data:/app/storage
      - ./config/api_keys.env:/app/config/api_keys.env:ro
    networks: [default, n8n]
    mem_limit: 1200m

networks:
  n8n:
    external: true
    name: n8n-kmar_default

volumes:
  agrisense_data:""", "docker-compose.yml (identical on laptop and VPS)")
bullets([
    "`restart: unless-stopped`: the container comes back by itself after a crash or a server reboot.",
    "`127.0.0.1:8150:8150`: the port is published **only on the server itself**. Nobody on the internet can reach "
    "port 8150 directly; they must go through Traefik and HTTPS.",
    "`agrisense_data:/app/storage`: the database lives in a named volume, so rebuilding the image never deletes it.",
    "`api_keys.env ... :ro`: secrets are mounted read-only from the server folder; they are **not** inside the image.",
    "`networks: [default, n8n]`: joins n8n's network so the app can call the n8n container by name.",
    "`mem_limit: 1200m`: the app can never use more than 1.2 GB, protecting the other projects on the same server.",
])
h2("3.3 What is never uploaded")
table([["Excluded", "Reason"], ["app/storage/", "Local test database; the server has its own"],
       ["config/api_keys.env (with code)", "Secrets are placed on the server once, separately, with tight permissions"],
       ["app/models/leaf_best.pt", "PyTorch training checkpoint; the server uses the ONNX export"],
       ["__pycache__, .venv, data/raw", "Generated files, the local environment and large training data"]],
      [0.36, 0.64], "Files kept off the server")

# ================================================================== 4 first deployment
h1("4. First Deployment, Step by Step")
para("This is the one-time set-up that put AgriSense on the server. The VPS already ran Traefik and n8n for other "
     "projects, so AgriSense was added **beside** them, never on top of them.")
figure(DG / "inside_vps.png", "Inside the VPS: Traefik, the AgriSense container and its networks, n8n.")
h2("Step 1: Point the domain at the VPS (DNS)")
para(f"In the Hostinger DNS panel for microeagle.online, an **A record** was added: name `ai.software`, value "
     f"`{VPS}`. Use the **Add record** button, not the pencil (the pencil renames an existing record). Check it:")
code(f"""nslookup {HOST}
# must answer {VPS} before Step 6, or the HTTPS certificate cannot be issued""", "Laptop")
h2("Step 2: Log in to the VPS")
code(f"""ssh -i {KEY} root@{VPS}""", "Laptop (Git Bash)")
para("The private key file stays on the laptop; the server only holds the matching public key, so no password is "
     "ever typed or sent.")
h2("Step 3: Create the project folder")
code("""mkdir -p /opt/stacks/agrisense/config
# every project on this server lives in /opt/stacks/<name>/ with its own docker-compose.yml""", "VPS")
h2("Step 4: Upload the code")
para("The first upload used the same method as every later update (Section 7), but packaged the whole project:")
code(f"""# on the laptop: package the project (tar works best with /tmp paths in Git Bash, not C:/...)
cd "/v/Niit University/Ai and Software Engg"
tar --exclude='app/storage' --exclude='app/models/leaf_best.pt' --exclude='__pycache__' \\
    -czf /tmp/rel1.tgz app ml Dockerfile docker-compose.yml requirements.txt deploy README.md
scp -i {KEY} /tmp/rel1.tgz root@{VPS}:/tmp/rel1.tgz

# on the VPS: unpack into the project folder
cd /opt/stacks/agrisense && tar -xzf /tmp/rel1.tgz && rm /tmp/rel1.tgz""", "Laptop, then VPS")
h2("Step 5: Put the secrets in place")
code("""# the key file is copied up separately (never inside the code package), then locked down:
chown 10001:10001 /opt/stacks/agrisense/config/api_keys.env    # owned by the container's user
chmod 600        /opt/stacks/agrisense/config/api_keys.env    # only that user can read it
# keys in it (values never shown): MISTRAL_API_KEY, MISTRAL_MODEL, MISTRAL_FALLBACK_MODEL,
# OTP_WEBHOOK_URL, OTP_SHARED_SECRET, AZURE_TRANSLATOR_KEY, AZURE_TRANSLATOR_REGION, AZURE_TRANSLATOR_ENDPOINT""", "VPS")
para("The server's key file has two more entries than the laptop's: `OTP_WEBHOOK_URL` and `OTP_SHARED_SECRET`, "
     "which switch on e-mailed sign-in codes through n8n (Section 6).")
h2("Step 6: Build and start the container")
code("""cd /opt/stacks/agrisense
docker compose up -d --build > build.log 2>&1
docker ps --filter name=agrisense
# agrisense | agrisense:local | Up ... (healthy) | 127.0.0.1:8150->8150/tcp""", "VPS")
para("`--build` builds the image from the Dockerfile, `-d` runs it in the background. The first build downloads "
     "Python libraries and takes a few minutes; the image is about 1 GB. Wait until the status says **(healthy)**.")
h2("Step 7: Add the Traefik route")
code(f"""# /opt/stacks/traefik/dynamic/agrisense.yml   (copied from deploy/agrisense.yml)
http:
  routers:
    agrisense:
      rule: Host(`{HOST}`)
      entryPoints: [websecure]
      service: agrisense
      tls:
        certResolver: letsencrypt
  services:
    agrisense:
      loadBalancer:
        passHostHeader: true
        servers:
          - url: http://127.0.0.1:8150""", "Traefik route file")
para("Traefik watches the `dynamic/` folder and loads the new file within seconds, with no restart. On the first "
     "visit it asks **Let's Encrypt** for a certificate for the domain (HTTP-01 challenge), which only works once "
     "DNS from Step 1 points at the server. Every other project has its own file in the same folder; we never edit "
     "theirs.")
h2("Step 8: Verify from outside")
code(f"""curl -s https://{HOST}/healthz                                  # {{"ok":true}}
curl -s -o /dev/null -w "%{{http_code}}" https://{HOST}/         # 200""", "Laptop")
figure(FIGS / "shot_02_overview.png", f"The live dashboard at https://{HOST}.", width=14)
h2("Step 9: Record it")
para("A line was added to `/opt/STRUCTURE.md`, the server's table of projects, so anyone on the box can see what "
     "runs where:")
code(f"""| agrisense | /opt/stacks/agrisense | 127.0.0.1:8150 | {HOST} | AgriSense AI (NIIT AI & Software Engg), FastAPI + ONNX, volume agrisense_agrisense_data |""",
     "/opt/STRUCTURE.md")
figure(DG / "request_flow.png", "What happens to every request once it is live.")

# ================================================================== 5 database
h1("5. The Database on the VPS")
para("AgriSense uses **SQLite**: the whole database is one file, `agrisense.db`. On the server that file is inside "
     "the Docker volume `agrisense_agrisense_data`, mounted at `/app/storage` in the container.")
code("""docker volume inspect agrisense_agrisense_data --format "{{.Mountpoint}}"
# /var/lib/docker/volumes/agrisense_agrisense_data/_data
docker exec agrisense ls -la /app/storage
# -rw-r--r-- 1 agri agri 851968 ... agrisense.db""", "VPS: where the data really is")
h2("5.1 How the tables get created")
para("Nobody runs SQL by hand. When the app starts, `db.init()` runs `CREATE TABLE IF NOT EXISTS` for all nine "
     "tables (users, sessions, farms, predictions, chats, uploads, otp_challenges, auth_events, cache/translations). "
     "When a release adds a column, `init()` checks `PRAGMA table_info` and runs `ALTER TABLE ... ADD COLUMN` once. "
     "This is a small, automatic **migration**: deploying the new code is enough.")
figure(UML / "er.png", "The tables that live in agrisense.db.", width=14)
h2("5.2 Why data survives every update")
bullets(["The image holds the code; the volume holds the data. `docker compose up -d --build` replaces the container "
         "but re-attaches the same volume.",
         "**Never** run `docker compose down -v`: the `-v` deletes volumes, which would wipe every account.",
         "Local and server databases are completely separate. Local test accounts never reach the server."])
h2("5.3 How to back up and test safely")
code("""# consistent copy of the live database while the app runs (SQLite online backup)
docker exec agrisense python -c "import sqlite3; s=sqlite3.connect('/app/storage/agrisense.db'); \\
d=sqlite3.connect('/app/storage/backup.db'); s.backup(d); d.close()"
docker cp agrisense:/app/storage/backup.db /root/agrisense_db_$(date +%F).db

# smoke-test new code inside the container WITHOUT touching the live database
docker exec -e AGRISENSE_STORAGE=/tmp/smoke agrisense python -c "..."   # uses a throwaway DB in /tmp""",
     "VPS")
note("Rules for the live database", [
    "Read it only through the app or a copy; never edit rows by hand.",
    "Tests, smoke checks and the load test always use a separate database (/tmp/smoke or a throwaway container).",
    "A full server dump (all volumes and databases) was also taken on 2026-10-03 before a planned server move.",
])

# ================================================================== 6 n8n
h1("6. n8n Integration: E-mailed Sign-in Codes")
para("Sign-up, sign-in and password reset need a 6-digit code sent by e-mail. Instead of putting mail-server "
     "settings inside AgriSense, the app hands the job to **n8n**, a workflow tool already running on the server for "
     "other projects. The workflow **AgriSense_OTP_Delivery** was made by cloning an existing OTP workflow (the "
     "original was not touched) and changing its path, sender text and secret.")
h2("6.1 The workflow")
figure(DG / "otp_n8n.png", "The six nodes of AgriSense_OTP_Delivery in n8n.", width=15)
table([["Node", "Type", "Job"],
       ["OTP request", "Webhook (POST)", "Listens at /webhook/agrisense-otp"],
       ["Shared secret matches?", "IF", "Compares the x-otp-secret header with the stored secret"],
       ["Send OTP email", "Send Email (SMTP)", "Writes the code into the e-mail and sends it"],
       ["200 delivered", "Respond to Webhook", "Answers {ok: true}"],
       ["401 rejected", "Respond to Webhook", "Wrong or missing secret: refuses"],
       ["Send failed", "Respond to Webhook", "Mail error: answers {ok: false, reason}"]],
      [0.28, 0.27, 0.45], "Workflow nodes (read from the live n8n)")
h2("6.2 How the app calls it")
code("""POST <OTP_WEBHOOK_URL>                 # value kept in api_keys.env
x-otp-secret: <OTP_SHARED_SECRET>     # value kept in api_keys.env
Content-Type: application/json

{"channel": "email", "to": "farmer@example.com", "code": "123456", "app": "AgriSense AI",
 "subject": "123456 is your AgriSense AI code", "purpose_line": "...", "expires_in_minutes": 10}

# reply:  {"ok": true}     or     {"ok": false, "reason": "..."}""", "Request sent by app/otp.py (example values)")
bullets(["The two containers share the Docker network `n8n-kmar_default`, so the app reaches n8n by its container "
         "name on the private network; the code never travels over the public internet.",
         "The **shared secret** proves the request came from AgriSense; anyone else calling the webhook gets 401.",
         "The app stores only a SHA-256 hash of each code, never the code itself.",
         "If n8n is down, the app shows 'delivery service unreachable' and no account is created."])
figure(DG / "seq_otp.png", "Sign-in with an e-mailed code, end to end.", width=15)
h2("6.3 Turning the workflow on")
warn("Gotcha found while setting it up", [
    "The workflow was imported and published with the n8n command line, but its webhook did not start answering.",
    "Toggling it in the n8n web page did not help either.",
    "What worked: `docker restart n8n-kmar-n8n-1` (about 30 seconds of n8n downtime, approved first because other projects use n8n).",
])
para("Locally, without `OTP_WEBHOOK_URL`, the app skips this step entirely and signs in with the password only.")

# ================================================================== 7 updates
h1("7. Pushing Updates to the VPS")
para("Every later change, from a bug fix to a new model, follows the same eight steps. Steps 1 to 4 run on the "
     "laptop; steps 5 to 8 run on the VPS in **one SSH command**, so a half-finished update cannot be left behind.")
figure(DG / "update_pipeline.png", "The update routine.")
h2("7.1 On the laptop")
code(f"""cd "/v/Niit University/Ai and Software Engg"
python -m pytest tests -q                         # 1-2: edit in VS Code, then all tests must pass

# 3: package only what changed (here the whole app/ folder plus one training script)
tar --exclude='app/storage' --exclude='app/models/leaf_best.pt' --exclude='__pycache__' \\
    -czf /tmp/rel8.tgz app ml/train_fertiliser.py

# 4: upload, retrying because SSH to this server sometimes drops
for i in 1 2 3 4 5 6; do
  timeout 150 scp -i {KEY} -o ConnectTimeout=25 -o ServerAliveInterval=10 \\
      /tmp/rel8.tgz root@{VPS}:/tmp/rel8.tgz && echo UPLOADED && break
  echo retry
done""", "Laptop (Git Bash) - the real commands used for release 8")
h2("7.2 On the VPS (one command)")
code(f"""ssh -i {KEY} root@{VPS} '
  cd /opt/stacks/agrisense &&
  test -f /tmp/rel8.tgz &&                                   # stop if the upload is missing
  cp -a app /root/agrisense_app_backup_$(date +%s) &&        # 5: back up the current code
  tar -xzf /tmp/rel8.tgz && rm /tmp/rel8.tgz &&              # 6: unpack the new code
  docker compose up -d --build > build.log 2>&1;             # 7: rebuild and restart
  for k in $(seq 1 30); do                                   # 8: wait up to 90 s for healthy
    docker ps --filter name=^agrisense --format "{{{{.Status}}}}" | grep -q healthy && break; sleep 3
  done;
  docker ps --filter name=^agrisense --format "{{{{.Names}}}} {{{{.Status}}}}"; tail -3 build.log'""",
     "Laptop -> VPS")
para("Each `&&` means 'only continue if the previous step worked'. Because the database is in the volume, the "
     "rebuild swaps the code and keeps every account and result. The old container keeps serving while the new image "
     "builds; only the swap itself interrupts the site, for a few seconds.")
h2("7.3 Check the release")
code(f"""curl -s https://{HOST}/api/status          # models loaded, versions, fertiliser model ready
curl -s https://{HOST}/healthz             # {{"ok":true}}
docker logs --tail 30 agrisense           # on the VPS: any error at start-up?""", "Verify")
h2("7.4 Roll back if something is wrong")
code("""cd /opt/stacks/agrisense
ls -d /root/agrisense_app_backup_*                       # pick the newest backup
rm -rf app && cp -a /root/agrisense_app_backup_<time> app
docker compose up -d --build""", "VPS")
table([["Release", "What it shipped"],
       ["rel8", "Fertiliser model (Logistic Regression), new fertiliser page and full analysis"],
       ["rel9", "Fewer 'Ask the assistant' buttons, kept only on fertiliser and disease results"]],
      [0.2, 0.8], "The last two releases pushed this way")

# ================================================================== 8 handling
h1("8. Handling Things on the VPS and Locally")
h2("8.1 Golden rules")
note("How the two copies are kept in step", [
    "The laptop is the **single source of truth**. Code is changed only in VS Code and only reaches the server by the update routine.",
    "The server is never edited by hand (no editing files in nano on the VPS); a hand edit would be lost at the next upload.",
    "Secrets are never in the code package, never printed, never committed. Each copy has its own api_keys.env.",
    "Each project on the server has its own folder, port, compose file and Traefik file. Never touch another project's files.",
    "Before anything that cannot be undone on the server (deleting, restarting shared services like n8n), take a backup and ask first.",
])
table([["Task", "Laptop", "VPS"],
       ["Change code", "Edit in VS Code", "Never; only deploy"],
       ["Run the app", "uvicorn --reload", "docker compose up -d --build"],
       ["See errors", "VS Code terminal", "docker logs agrisense"],
       ["Database", "app/storage/agrisense.db (test data)", "volume agrisense_agrisense_data (real users)"],
       ["Secrets", "config/api_keys.env", "config/api_keys.env, chmod 600, owner 10001"],
       ["Sign-in", "Password only", "Password + e-mailed code"],
       ["Tests", "pytest (88)", "Smoke test in a throwaway DB; load test on a throwaway container"],
       ["Restart", "Ctrl+C, run again", "docker compose restart (or up -d)"]],
      [0.18, 0.38, 0.44], "Who does what, where")
h2("8.2 Everyday commands on the VPS")
code("""docker ps --filter name=agrisense                 # running? healthy?
docker logs --tail 50 -f agrisense                # live log (Ctrl+C to stop)
docker stats --no-stream agrisense                # CPU and memory (about 315 MiB of 1.2 GiB at rest)
docker compose -f /opt/stacks/agrisense/docker-compose.yml restart
docker exec -it agrisense bash                    # look around inside the container
ls /opt/stacks/traefik/dynamic/                   # one route file per project
cat /opt/STRUCTURE.md                             # what runs where on this server""", "VPS")
h2("8.3 The load test without risk")
para("The capacity test (100 users at once within 2 s) ran against a **throwaway copy**: a second container "
     "`agrisense-loadtest` from the same image, with its own empty database, sign-in codes switched off and the same "
     "1.2 GB limit. The traffic generator ran in another container limited to half a CPU. Afterwards both were "
     "removed and `/tmp/lt` deleted, so the live app and its users were never touched.")

# ================================================================== 9 troubleshooting
h1("9. Problems We Hit and How They Were Solved")
table([["Problem", "Cause", "Fix"],
       ["`tar`/`scp` fail on C:/ paths", "Git Bash reads 'C:' as a remote host name", "Build the package in /tmp, upload from /tmp"],
       ["SSH or scp drops mid-upload", "Unstable connection to the VPS", "Retry loop with timeout, ConnectTimeout and ServerAliveInterval"],
       ["Webhook silent after import", "n8n did not register a CLI-published webhook", "Restart the n8n container (with approval)"],
       ["Icons showed as words", "Google Fonts blocked on the user's network", "Fonts and libraries served by the app itself"],
       ["Fonts served as text/plain", "python:3.12-slim has no mime.types", "App registers font/woff2 types itself"],
       ["No HTTPS certificate", "DNS did not yet point at the VPS", "Add the A record first, wait, then visit"],
       ["Container unreachable", "App bound to 127.0.0.1 inside the container", "Uvicorn --host 0.0.0.0"],
       ["Load-test results lost", "Generator runs as uid 10001, could not write", "chmod the results folder before the run"],
       ["Windows line endings in scripts", "Files written on Windows have CRLF", "Pipe through tr -d '\\r' when writing files to the VPS"],
       ["A $ in a secret broke Compose", "Compose reads $ in env files as a variable", "Escape as $$ (seen on another project on this server)"]],
      [0.25, 0.37, 0.38], "Troubleshooting table", 9.5)

# ================================================================== 10 checklist
h1("10. Release Checklist")
for item in ["All 88 tests pass on the laptop", "Package excludes app/storage, the .pt checkpoint, __pycache__ and secrets",
             "Upload succeeded (UPLOADED printed)", "Backup of the current app/ made on the VPS",
             "docker compose up -d --build finished; build.log has no error", "Container shows (healthy)",
             "https://ai.software.microeagle.online/healthz answers ok", "Key pages and a sign-in with an e-mailed code tested",
             "Android app opens and loads data", "Note in the project record what was released"]:
    p = para(after=3, align=WD_ALIGN_PARAGRAPH.LEFT)
    runs(p, "\u2610  " + item, 12)
para("")
figure(UML / "deployment.png", "Deployment diagram from the design document.", width=15)

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print("wrote", OUT, FIG[0], "figures", TAB[0], "tables")
