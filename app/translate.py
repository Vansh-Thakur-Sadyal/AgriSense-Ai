"""Interface translation through Azure AI Translator, with a permanent SQLite cache.

The browser sends the English strings it is showing; each (language, string) pair is translated by
Azure once and then served from the `translations` table forever, so the paid API is only touched
for strings nobody has seen before. A daily character budget caps the bill even if someone sends
junk, and a small per-IP rate limit protects the public endpoint (it is used on the sign-in page).

Config (config/api_keys.env): AZURE_TRANSLATOR_KEY, AZURE_TRANSLATOR_REGION, AZURE_TRANSLATOR_ENDPOINT,
optional TRANSLATE_DAILY_CHARS (default 300000).
"""
import os
import re
import time
from collections import defaultdict, deque

import httpx

from . import db

# English + 14 Indian languages. Values: (English name, native name, name used in the assistant prompt)
LANGS = {
    "en": ("English", "English", "English"),
    "hi": ("Hindi", "हिन्दी", "Hindi (Devanagari script)"),
    "bn": ("Bengali", "বাংলা", "Bengali (Bangla script)"),
    "mr": ("Marathi", "मराठी", "Marathi (Devanagari script)"),
    "te": ("Telugu", "తెలుగు", "Telugu (Telugu script)"),
    "ta": ("Tamil", "தமிழ்", "Tamil (Tamil script)"),
    "gu": ("Gujarati", "ગુજરાતી", "Gujarati (Gujarati script)"),
    "ur": ("Urdu", "اردو", "Urdu (Perso-Arabic script)"),
    "kn": ("Kannada", "ಕನ್ನಡ", "Kannada (Kannada script)"),
    "or": ("Odia", "ଓଡ଼ିଆ", "Odia (Odia script)"),
    "ml": ("Malayalam", "മലയാളം", "Malayalam (Malayalam script)"),
    "pa": ("Punjabi", "ਪੰਜਾਬੀ", "Punjabi (Gurmukhi script)"),
    "as": ("Assamese", "অসমীয়া", "Assamese (Bengali-Assamese script)"),
    "mai": ("Maithili", "मैथिली", "Maithili (Devanagari script)"),
    "gom": ("Konkani", "कोंकणी", "Konkani (Devanagari script)"),
}
MAX_ITEMS, MAX_LEN = 150, 400
WORD = re.compile(r"[A-Za-z]{2,}")
_hits = defaultdict(deque)


class TranslateError(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status, self.msg = status, msg


def configured():
    return bool(os.environ.get("AZURE_TRANSLATOR_KEY"))


def languages():
    return [{"code": c, "name": n, "native": nat} for c, (n, nat, _) in LANGS.items()]


def prompt_name(code):
    return LANGS.get(code, LANGS["en"])[2]


def _rate_ok(ip, limit=90, window=60):
    q, now = _hits[ip], time.time()
    while q and q[0] < now - window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def _spend(chars):
    """Daily budget of characters sent to Azure (cached strings are free)."""
    key = "tr_budget:" + time.strftime("%Y-%m-%d")
    used = (db.cache_get(key) or {"n": 0})["n"]
    cap = int(os.environ.get("TRANSLATE_DAILY_CHARS", "300000"))
    if used + chars > cap:
        raise TranslateError(429, "Today's translation budget is used up; showing English for new text.")
    db.cache_put(key, {"n": used + chars}, 2 * 86400)


def _azure(texts, lang):
    ep = os.environ.get("AZURE_TRANSLATOR_ENDPOINT", "https://api.cognitive.microsofttranslator.com").rstrip("/")
    headers = {"Ocp-Apim-Subscription-Key": os.environ["AZURE_TRANSLATOR_KEY"], "Content-Type": "application/json"}
    if os.environ.get("AZURE_TRANSLATOR_REGION"):
        headers["Ocp-Apim-Subscription-Region"] = os.environ["AZURE_TRANSLATOR_REGION"]
    out = []
    for i in range(0, len(texts), 100):          # Azure: up to 100 elements per request
        chunk = texts[i:i + 100]
        r = httpx.post(ep + "/translate", params={"api-version": "3.0", "from": "en", "to": lang, "textType": "plain"},
                       headers=headers, json=[{"Text": t} for t in chunk], timeout=25)
        if r.status_code != 200:
            raise TranslateError(502, f"Translation service error ({r.status_code})")
        out += [item["translations"][0]["text"] for item in r.json()]
    return out


def translate(texts, lang, ip=""):
    if lang not in LANGS or lang == "en":
        raise TranslateError(422, "Unsupported language")
    if not configured():
        raise TranslateError(503, "Translation is not configured on this server")
    if not _rate_ok(ip or "-"):
        raise TranslateError(429, "Too many translation requests; slow down")
    clean = []
    for t in texts[:MAX_ITEMS]:
        t = (t or "").strip()
        if t and len(t) <= MAX_LEN and WORD.search(t) and t not in clean:
            clean.append(t)
    if not clean:
        return {}
    found = {}
    marks = ",".join("?" * len(clean))
    for r in db.rows(f"SELECT src, dst FROM translations WHERE lang=? AND src IN ({marks})", (lang, *clean)):
        found[r["src"]] = r["dst"]
    missing = [t for t in clean if t not in found]
    if missing:
        _spend(sum(len(t) for t in missing))
        for src, dst in zip(missing, _azure(missing, lang)):
            found[src] = dst
            db.run("INSERT OR REPLACE INTO translations(lang, src, dst, created_at) VALUES(?,?,?,?)", (lang, src, dst, time.time()))
    return found


# Unicode blocks of each language's script, to check that a reply is really in the chosen language.
SCRIPT = {"hi": (0x0900, 0x097F), "mr": (0x0900, 0x097F), "mai": (0x0900, 0x097F), "gom": (0x0900, 0x097F),
          "bn": (0x0980, 0x09FF), "as": (0x0980, 0x09FF), "pa": (0x0A00, 0x0A7F), "gu": (0x0A80, 0x0AFF),
          "or": (0x0B00, 0x0B7F), "ta": (0x0B80, 0x0BFF), "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF),
          "ml": (0x0D00, 0x0D7F), "ur": (0x0600, 0x06FF)}


def in_language(text, lang):
    """True when most letters of `text` are in the script of `lang` (English: always True)."""
    if lang not in SCRIPT:
        return True
    lo, hi = SCRIPT[lang]
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return True
    return sum(lo <= ord(ch) <= hi for ch in letters) / len(letters) >= 0.5


def translate_long(text, lang):
    """Translate a whole message (assistant answers); cached like UI strings."""
    if lang not in LANGS or lang == "en" or not configured():
        raise TranslateError(422, "Unsupported language")
    text = text[:6000]
    hit = db.one("SELECT dst FROM translations WHERE lang=? AND src=?", (lang, text))
    if hit:
        return hit["dst"]
    _spend(len(text))
    dst = _azure([text], lang)[0]
    db.run("INSERT OR REPLACE INTO translations(lang, src, dst, created_at) VALUES(?,?,?,?)", (lang, text, dst, time.time()))
    return dst
