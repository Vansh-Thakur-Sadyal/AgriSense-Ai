"""E-mail one-time codes for sign-up, sign-in and password reset.

Delivery goes through our own n8n workflow (AgriSense_OTP_Delivery, a clone of the Saarthi OTP
chain): POST {OTP_WEBHOOK_URL} with header x-otp-secret. n8n answers HTTP 200 even from some
failure paths, so success is read from the body ({"ok": true}), never from the status code.

Codes are 6 digits, stored only as SHA-256(challenge id + code), valid 10 minutes, 5 wrong tries
burn the challenge, a resend needs a 60 s gap, and one address gets at most 6 codes per hour.
OTP is ON when OTP_WEBHOOK_URL and OTP_SHARED_SECRET are set (production); without them the app
falls back to password-only sign-in, which is only meant for local development.
"""
import hashlib
import json
import os
import secrets
import time

import httpx

from . import db

TTL = 600
MAX_ATTEMPTS = 5
RESEND_GAP = 60
MAX_PER_HOUR = 6
PURPOSE_LINE = {
    "signup": "Use this code to finish creating your AgriSense AI account.",
    "login": "Use this code to finish signing in to AgriSense AI.",
    "reset": "Use this code to set a new password for your AgriSense AI account.",
}


class OTPError(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status, self.msg = status, msg


def enabled():
    return bool(os.environ.get("OTP_WEBHOOK_URL") and os.environ.get("OTP_SHARED_SECRET"))


def mask(email):
    name, _, dom = email.partition("@")
    return (name[:2] + "*" * max(1, len(name) - 2)) + "@" + dom


def _hash(cid, code):
    return hashlib.sha256(f"{cid}:{code}".encode()).hexdigest()


def deliver(email, code, purpose):
    """Returns None on success, else the reason text."""
    try:
        r = httpx.post(os.environ["OTP_WEBHOOK_URL"], timeout=25,
                       headers={"x-otp-secret": os.environ["OTP_SHARED_SECRET"]},
                       json={"channel": "email", "to": email, "code": code, "app": "AgriSense AI",
                             "subject": f"{code} is your AgriSense AI code",
                             "purpose_line": PURPOSE_LINE[purpose], "expires_in_minutes": TTL // 60})
        body = r.json() if r.content else {}
    except Exception as e:  # network, bad JSON, empty 200
        return f"delivery service unreachable ({type(e).__name__})"
    if body.get("ok") is True:
        return None
    return str(body.get("reason") or f"HTTP {r.status_code}")


def _recent_sends(email):
    r = db.one("SELECT COALESCE(SUM(sends),0) n FROM otp_challenges WHERE email=? AND created_at>?",
               (email, time.time() - 3600))
    return r["n"]


def start(email, purpose, user_id=None, payload=None, ip=None, send=True):
    if _recent_sends(email) >= MAX_PER_HOUR:
        raise OTPError(429, "Too many codes requested for this e-mail. Try again in an hour.")
    cid = secrets.token_urlsafe(18)
    code = f"{secrets.randbelow(10 ** 6):06d}"
    now = time.time()
    db.run("INSERT INTO otp_challenges(id,email,purpose,user_id,payload,code_hash,expires,last_sent,ip,created_at) "
           "VALUES(?,?,?,?,?,?,?,?,?,?)", (cid, email, purpose, user_id, json.dumps(payload or {}), _hash(cid, code),
                                          now + TTL, now, ip, now))
    if send:
        why = deliver(email, code, purpose)
        if why:
            db.run("UPDATE otp_challenges SET consumed_at=? WHERE id=?", (now, cid))
            db.log_event("otp_send_failed", user_id, email, f"{purpose}: {why}")
            raise OTPError(502, "We could not send the code e-mail right now. Please try again in a minute.")
        db.log_event("otp_sent", user_id, email, purpose)
    return {"otp_required": True, "challenge_id": cid, "email": mask(email), "purpose": purpose,
            "expires_in": TTL, "resend_in": RESEND_GAP}


def resend(cid):
    c = db.one("SELECT * FROM otp_challenges WHERE id=?", (cid,))
    if not c or c["consumed_at"] or c["expires"] < time.time():
        raise OTPError(410, "This code request has expired. Please start again.")
    wait = int(c["last_sent"] + RESEND_GAP - time.time())
    if wait > 0:
        raise OTPError(429, f"Please wait {wait} s before asking for another code.")
    if _recent_sends(c["email"]) >= MAX_PER_HOUR:
        raise OTPError(429, "Too many codes requested for this e-mail. Try again in an hour.")
    code = f"{secrets.randbelow(10 ** 6):06d}"
    now = time.time()
    if c["user_id"] is not None or c["purpose"] == "signup":
        why = deliver(c["email"], code, c["purpose"])
        if why:
            db.log_event("otp_send_failed", c["user_id"], c["email"], f"resend {c['purpose']}: {why}")
            raise OTPError(502, "We could not send the code e-mail right now. Please try again in a minute.")
    db.run("UPDATE otp_challenges SET code_hash=?, attempts=0, sends=sends+1, last_sent=?, expires=? WHERE id=?",
           (_hash(cid, code), now, now + TTL, cid))
    db.log_event("otp_resent", c["user_id"], c["email"], c["purpose"])
    return {"ok": True, "email": mask(c["email"]), "expires_in": TTL, "resend_in": RESEND_GAP}


def verify(cid, code):
    """Consumes the challenge on success and returns its row; raises OTPError otherwise."""
    c = db.one("SELECT * FROM otp_challenges WHERE id=?", (cid or "",))
    if not c or c["consumed_at"] or c["expires"] < time.time():
        raise OTPError(410, "This code has expired. Please ask for a new one.")
    if c["attempts"] >= MAX_ATTEMPTS:
        raise OTPError(429, "Too many wrong codes. Please start again.")
    code = "".join(ch for ch in str(code or "") if ch.isdigit())
    if c["user_id"] is None and c["purpose"] != "signup":   # decoy for an unknown address
        ok = False
    else:
        ok = secrets.compare_digest(_hash(cid, code), c["code_hash"])
    if not ok:
        db.run("UPDATE otp_challenges SET attempts=attempts+1 WHERE id=?", (cid,))
        db.log_event("otp_wrong", c["user_id"], c["email"], c["purpose"])
        left = MAX_ATTEMPTS - c["attempts"] - 1
        raise OTPError(401, "That code is not right." + (f" {left} tries left." if left > 0 else " Please start again."))
    db.run("UPDATE otp_challenges SET consumed_at=? WHERE id=?", (time.time(), cid))
    c["payload"] = json.loads(c["payload"] or "{}")
    return c
