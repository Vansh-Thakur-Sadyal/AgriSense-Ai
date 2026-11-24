"""Diagrams for the deployment guide (matplotlib, PNG), drawn with the same helpers as the SE diagrams."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "submission"))
import diagrams as D  # noqa: E402

OUT = HERE / "out" / "deploy"
OUT.mkdir(parents=True, exist_ok=True)
NL = chr(10)
B = D.box
A = D.arrow


def save(f, name):
    f.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    D.plt.close(f)


def zone(ax, x, y, w, h, label, color):
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", fc="none", ec=color, lw=1.3, ls="--"))
    ax.text(x + 1, y + h - 1.2, label, fontsize=8.5, weight="bold", color=color, va="top")


def big_picture():
    f, ax = D._canvas(10, 5.6, 100, 56)
    zone(ax, 0.5, 24, 30, 30, "YOUR LAPTOP (Windows 11)", D.GREEN)
    B(ax, 3, 41, 25, 8, "VS Code", f"edit app/, ml/, tests/{NL}Python venv, Android Studio", fc=D.MINT)
    B(ax, 3, 28, 25, 9, "Test locally", f"uvicorn on 127.0.0.1:8150{NL}pytest: 88 tests", fc=D.MINT)
    A(ax, 15.5, 41, 15.5, 37.3)
    zone(ax, 38, 3, 61, 51, "HOSTINGER VPS  187.127.191.13  (Ubuntu 24.04, Docker)", D.BLUE)
    B(ax, 41, 41, 17, 8, "/tmp/relN.tgz", "uploaded package")
    B(ax, 62, 41, 34, 8, "/opt/stacks/agrisense", f"app/, Dockerfile, compose,{NL}config/api_keys.env (600)")
    A(ax, 58.3, 45, 61.7, 45, "untar")
    B(ax, 62, 26, 34, 10, "Container: agrisense", f"image agrisense:local{NL}uvicorn x2 on 127.0.0.1:8150", fc=D.MINT)
    A(ax, 79, 41, 79, 36.3, "docker compose up -d --build", off=(9, -0.5))
    B(ax, 41, 26, 17, 10, "Traefik", f":80 / :443{NL}Let's Encrypt TLS", ec=D.ORANGE)
    A(ax, 58.3, 31, 61.7, 31)
    B(ax, 62, 6, 15, 9, "Volume", f"agrisense.db{NL}(SQLite)", ec=D.DARK)
    B(ax, 81, 6, 15, 9, "n8n-kmar", f"OTP e-mail{NL}workflow", ec=D.ORANGE)
    A(ax, 70, 25.7, 70, 15.3)
    A(ax, 88, 25.7, 88, 15.3)
    B(ax, 41, 6, 17, 9, "/root backups", f"agrisense_app_{NL}backup_<time>")
    A(ax, 30.3, 32, 40.7, 44, "scp (SSH key)", off=(-2, 1.5))
    B(ax, 3, 6, 25, 12, "Users", f"browser and Android app{NL}https://ai.software.{NL}microeagle.online", ec=D.ORANGE)
    A(ax, 28.3, 13, 40.7, 29, "HTTPS", off=(-3, 0))
    save(f, "big_picture.png")


def inside_vps():
    f, ax = D._canvas(10, 5.2, 100, 52)
    B(ax, 2, 22, 14, 10, "Internet", f"browser,{NL}Android app", ec=D.ORANGE)
    zone(ax, 20, 2, 78, 48, "VPS", D.BLUE)
    B(ax, 23, 21, 18, 12, "Traefik", f"host network{NL}:80 -> :443 redirect{NL}TLS certificates", fc=D.MINT)
    A(ax, 16.3, 27, 22.7, 27, "443")
    B(ax, 23, 38, 18, 8, "dynamic/agrisense.yml", f"Host(ai.software...){NL}-> 127.0.0.1:8150", fs=7)
    A(ax, 32, 37.7, 32, 33.3, "watch")
    zone(ax, 45, 15, 30, 31, "network: agrisense_default", D.GREEN)
    B(ax, 48, 25, 24, 13, "agrisense container", f"FastAPI + models{NL}user 10001 (non-root){NL}healthcheck /healthz", fc=D.MINT)
    A(ax, 41.3, 27, 47.7, 30, "127.0.0.1:8150", off=(0, 0.8))
    B(ax, 48, 17, 11, 6, "volume", "/app/storage", fs=7)
    B(ax, 61, 17, 11, 6, "api_keys.env", "read-only", fs=7)
    zone(ax, 78, 15, 18, 31, "n8n-kmar_default", D.ORANGE)
    B(ax, 80, 27, 14, 11, "n8n", f"workflow{NL}AgriSense_OTP{NL}_Delivery", ec=D.ORANGE, fs=7.4)
    A(ax, 72.3, 32, 79.7, 32, "webhook", off=(0, 0.8))
    B(ax, 80, 17, 14, 7, "SMTP", "e-mail out", ec=D.ORANGE, fs=7.4)
    A(ax, 87, 26.7, 87, 24.3)
    B(ax, 48, 4, 48, 7, "Other projects on the same VPS", "each in /opt/stacks/<name>, own port, own Traefik file", ec=D.GREY, fs=7.4)
    save(f, "inside_vps.png")


def update_pipeline():
    f, ax = D._canvas(10, 3.0, 100, 30)
    steps = [("1 Edit", "VS Code"), ("2 Test", "pytest"), ("3 Package", "tar -czf"), ("4 Upload", "scp"),
             ("5 Back up", "cp -a app"), ("6 Unpack", "tar -xzf"), ("7 Rebuild", "compose up"), ("8 Verify", "healthy, curl")]
    w, gap = 10.6, 1.9
    for i, (t, s_) in enumerate(steps):
        x = 1 + i * (w + gap)
        local = i < 4
        B(ax, x, 12, w, 10, t, s_, fc=D.MINT if local else "white", ec=D.GREEN if local else D.BLUE, fs=7.6)
        if i:
            A(ax, x - gap + 0.2, 17, x - 0.2, 17)
    ax.text(24, 7.5, "on the laptop", ha="center", fontsize=8, color=D.GREEN, weight="bold")
    ax.text(74, 7.5, "on the VPS (one SSH command)", ha="center", fontsize=8, color=D.BLUE, weight="bold")
    save(f, "update_pipeline.png")


def otp_flow():
    f, ax = D._canvas(10, 3.4, 100, 34)
    nodes = [("OTP request", "Webhook POST", 2), ("Shared secret", "matches?  (IF)", 22), ("Send OTP email", "SMTP", 46),
             ("200 delivered", "{ok: true}", 72)]
    for t, s_, x in nodes:
        B(ax, x, 18, 18, 10, t, s_, fc=D.MINT if t.startswith("Send") else "white", ec=D.ORANGE, fs=7.8)
    A(ax, 20.3, 23, 21.7, 23)
    A(ax, 40.3, 23, 45.7, 23, "yes", off=(0, 0.6))
    A(ax, 64.3, 23, 71.7, 23, "sent", off=(0, 0.6))
    B(ax, 22, 2, 18, 9, "401 rejected", "{ok: false}", ec=D.ORANGE, fs=7.8)
    A(ax, 31, 17.7, 31, 11.3, "no", off=(2, 0))
    B(ax, 46, 2, 18, 9, "Send failed", "{ok: false, reason}", ec=D.ORANGE, fs=7.8)
    A(ax, 55, 17.7, 55, 11.3, "error", off=(3, 0))
    save(f, "otp_n8n.png")


def otp_sequence():
    D.sequence("deploy_seq_otp.png", ["User", "AgriSense app", "n8n workflow", "Mail server"], [
        (0, 1, "sign in: e-mail + password", "call"),
        (1, 1, "check password, make code, store its hash", "self"),
        (1, 2, "POST /webhook/agrisense-otp  (x-otp-secret)", "call"),
        (2, 2, "IF secret matches", "self"),
        (2, 3, "send e-mail with the code", "call"),
        (2, 1, "200 {ok: true}", "ret"),
        (1, 0, "enter the code we sent", "ret"),
        (0, 1, "POST /api/auth/otp/verify (code)", "call"),
        (1, 0, "session cookie or bearer token", "ret"),
    ])
    import shutil
    shutil.move(str(HERE.parents[0] / "submission" / "figs" / "deploy_seq_otp.png"), OUT / "seq_otp.png")


def request_flow():
    f, ax = D._canvas(10, 2.6, 100, 26)
    steps = [("Browser / app", "https://ai.software..."), ("DNS", "A record -> VPS IP"), ("Traefik", "TLS, Host rule"),
             ("agrisense:8150", "FastAPI route"), ("Model / SQLite", "predict, save"), ("Response", "JSON or page")]
    w, gap = 14.4, 2.3
    for i, (t, s_) in enumerate(steps):
        x = 1 + i * (w + gap)
        B(ax, x, 8, w, 11, t, s_, fc=D.MINT if i == 3 else "white", fs=7.8)
        if i:
            A(ax, x - gap + 0.2, 13.5, x - 0.2, 13.5)
    save(f, "request_flow.png")


def local_vs_vps():
    f, ax = D._canvas(10, 4.6, 100, 46)
    zone(ax, 1, 2, 47, 42, "LOCAL (development)", D.GREEN)
    zone(ax, 52, 2, 47, 42, "VPS (production)", D.BLUE)
    rows = [("Run", "python -m uvicorn app.main:app", "docker compose up -d --build"),
            ("Address", "http://127.0.0.1:8150", "https://ai.software.microeagle.online"),
            ("Database", "app/storage/agrisense.db", "volume agrisense_agrisense_data"),
            ("Secrets", "config/api_keys.env (no OTP keys)", "config/api_keys.env, 600, uid 10001"),
            ("Sign-in", "password only (OTP off)", "password + e-mailed code"),
            ("Changes", "edit in VS Code", "never edited by hand: only deployed")]
    for i, (k, a, b) in enumerate(rows):
        y = 34 - i * 5.8
        B(ax, 3, y, 43, 4.6, f"{k}: {a}", fs=7.2)
        B(ax, 54, y, 43, 4.6, f"{k}: {b}", fs=7.2)
    save(f, "local_vs_vps.png")


if __name__ == "__main__":
    for fn in (big_picture, inside_vps, update_pipeline, otp_flow, otp_sequence, request_flow, local_vs_vps):
        fn()
    print("ok")
