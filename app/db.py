"""SQLite storage: users, sessions, farms, predictions, chats, external-data cache."""
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

STORAGE = Path(os.environ.get("AGRISENSE_STORAGE", Path(__file__).resolve().parent / "storage"))
STORAGE.mkdir(parents=True, exist_ok=True)
DB_PATH = STORAGE / "agrisense.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE, phone TEXT UNIQUE,
  pw_hash TEXT NOT NULL, state TEXT, district TEXT, role TEXT DEFAULT 'farmer',
  language TEXT DEFAULT 'en', units TEXT DEFAULT 'metric', notify_weather INTEGER DEFAULT 1,
  share_farm_with_assistant INTEGER DEFAULT 1, created_at REAL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER, expires REAL);
CREATE TABLE IF NOT EXISTS farms(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL, state TEXT, district TEXT,
  village TEXT, lat REAL, lon REAL, area_ha REAL, soil_type TEXT, current_crop TEXT,
  irrigation TEXT, notes TEXT, crop_history TEXT DEFAULT '[]', updated_at REAL);
CREATE TABLE IF NOT EXISTS predictions(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, farm_id INTEGER, kind TEXT NOT NULL,
  inputs TEXT, result TEXT, summary TEXT, crop TEXT, confidence REAL, model_version TEXT,
  status TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS chats(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT, saved INTEGER DEFAULT 0,
  messages TEXT DEFAULT '[]', updated_at REAL);
CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, value TEXT, expires REAL);
CREATE TABLE IF NOT EXISTS otp_challenges(
  id TEXT PRIMARY KEY, email TEXT NOT NULL, purpose TEXT NOT NULL, user_id INTEGER, payload TEXT,
  code_hash TEXT NOT NULL, attempts INTEGER DEFAULT 0, sends INTEGER DEFAULT 1, expires REAL,
  last_sent REAL, consumed_at REAL, ip TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_otp_email ON otp_challenges(email, created_at);
CREATE TABLE IF NOT EXISTS auth_events(
  id INTEGER PRIMARY KEY, user_id INTEGER, email TEXT, event TEXT NOT NULL, detail TEXT, ip TEXT,
  user_agent TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_auth_user ON auth_events(user_id, created_at);
CREATE TABLE IF NOT EXISTS translations(
  lang TEXT NOT NULL, src TEXT NOT NULL, dst TEXT NOT NULL, created_at REAL,
  PRIMARY KEY(lang, src));
CREATE TABLE IF NOT EXISTS uploads(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, prediction_id INTEGER, chat_id INTEGER, filename TEXT,
  content_type TEXT, size INTEGER, sha256 TEXT, data BLOB, created_at REAL);
"""


def init():
    with connect() as c:
        c.executescript(SCHEMA)
        cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        if "email_verified_at" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN email_verified_at REAL")
        if "last_login_at" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN last_login_at REAL")


def log_event(event, user_id=None, email=None, detail=None, request=None):
    ip = ua = None
    if request is not None:
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()
        ua = (request.headers.get("user-agent") or "")[:300]
    run("INSERT INTO auth_events(user_id,email,event,detail,ip,user_agent,created_at) VALUES(?,?,?,?,?,?,?)",
        (user_id, email, event, detail, ip, ua, time.time()))


def save_upload(user_id, filename, content_type, data, prediction_id=None, chat_id=None):
    return run("INSERT INTO uploads(user_id,prediction_id,chat_id,filename,content_type,size,sha256,data,created_at) "
               "VALUES(?,?,?,?,?,?,?,?,?)", (user_id, prediction_id, chat_id, filename, content_type, len(data),
                                            hashlib.sha256(data).hexdigest(), data, time.time()))


@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def rows(sql, args=()):
    with connect() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def one(sql, args=()):
    r = rows(sql, args)
    return r[0] if r else None


def run(sql, args=()):
    with connect() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


# ---- passwords (scrypt) ----
def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def check_pw(pw: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32)
        return secrets.compare_digest(got.hex(), h)
    except Exception:
        return False


def new_session(user_id: int, days: int) -> str:
    tok = secrets.token_urlsafe(32)
    run("INSERT INTO sessions VALUES(?,?,?)",
        (hashlib.sha256(tok.encode()).hexdigest(), user_id, time.time() + days * 86400))
    return tok


def session_user(tok: str | None):
    if not tok:
        return None
    th = hashlib.sha256(tok.encode()).hexdigest()
    s = one("SELECT * FROM sessions WHERE token_hash=?", (th,))
    if not s or s["expires"] < time.time():
        return None
    return one("SELECT * FROM users WHERE id=?", (s["user_id"],))


def end_session(tok: str | None):
    if tok:
        run("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(tok.encode()).hexdigest(),))


# ---- cache for slow external APIs ----
def cache_get(key):
    r = one("SELECT value, expires FROM cache WHERE key=?", (key,))
    if r and r["expires"] > time.time():
        return json.loads(r["value"])
    return None


def cache_put(key, value, ttl):
    run("INSERT OR REPLACE INTO cache VALUES(?,?,?)", (key, json.dumps(value), time.time() + ttl))
