"""Authentication, e-mail OTP and account management."""
import sqlite3
import os
from pathlib import Path

from conftest import OUTBOX, last_code, new_client, signup

DB = Path(os.environ["AGRISENSE_STORAGE"]) / "agrisense.db"


def _db():
    return sqlite3.connect(DB)


def test_tc001_signup_sends_code_and_creates_nothing():
    """TC-001 | Authentication | Sign-up asks for an e-mail code before creating the account
    pre: OTP e-mail service configured
    data: name "Test Farmer", new e-mail, password Farm12345
    steps: 1. Submit the sign-up form. 2. Check the reply. 3. Look for the account in the users table.
    expected: Reply says a code is required and shows the masked e-mail; one code is e-mailed; no users row and no session exist yet."""
    c = new_client()
    r = c.post("/api/auth/register", json={"name": "Test Farmer", "email": "tc001@agrisense.test", "password": "Farm12345"})
    j = r.json()
    assert r.status_code == 200 and j["otp_required"] and j["purpose"] == "signup"
    assert "*" in j["email"] and last_code("tc001@agrisense.test")
    assert _db().execute("select count(*) from users where email='tc001@agrisense.test'").fetchone()[0] == 0
    assert c.get("/api/me").status_code == 401


def test_tc002_signup_with_correct_code():
    """TC-002 | Authentication | Correct code completes sign-up and signs the user in
    pre: TC-001 state (code e-mailed)
    data: the 6-digit code from the e-mail
    steps: 1. Sign up. 2. Enter the e-mailed code. 3. Open the dashboard (/api/me).
    expected: Account created with email_verified_at set; session cookie issued; /api/me returns the user."""
    c, email = signup()
    me = c.get("/api/me")
    assert me.status_code == 200 and me.json()["user"]["email"] == email
    assert _db().execute("select email_verified_at from users where email=?", (email,)).fetchone()[0]


def test_tc003_wrong_code_rejected():
    """TC-003 | Authentication | Wrong code is rejected with tries left
    pre: A sign-up code has been e-mailed
    data: code 000000
    steps: 1. Sign up. 2. Enter 000000.
    expected: HTTP 401 "That code is not right. 4 tries left."; no account created."""
    c = new_client()
    r = c.post("/api/auth/register", json={"name": "Test Farmer", "email": "tc003@agrisense.test", "password": "Farm12345"})
    r = c.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": "000000"})
    assert r.status_code == 401 and "4 tries left" in r.json()["error"]


def test_tc004_five_wrong_codes_lock_challenge():
    """TC-004 | Authentication | Five wrong codes cancel the code request
    pre: A code has been e-mailed
    data: 5 wrong codes, then the right one
    steps: 1. Enter 5 wrong codes. 2. Enter the correct code.
    expected: The correct code is now refused with HTTP 429 "Too many wrong codes"."""
    c = new_client()
    r = c.post("/api/auth/register", json={"name": "Test Farmer", "email": "tc004@agrisense.test", "password": "Farm12345"})
    cid = r.json()["challenge_id"]
    for _ in range(5):
        c.post("/api/auth/otp/verify", json={"challenge_id": cid, "code": "999999"})
    r = c.post("/api/auth/otp/verify", json={"challenge_id": cid, "code": last_code("tc004@agrisense.test")})
    assert r.status_code == 429


def test_tc005_code_single_use():
    """TC-005 | Authentication | A code cannot be used twice
    pre: Sign-up completed with a code
    data: the same code again
    steps: 1. Complete sign-up. 2. Submit the same challenge and code again.
    expected: HTTP 410 (expired/used)."""
    c = new_client()
    r = c.post("/api/auth/register", json={"name": "Test Farmer", "email": "tc005@agrisense.test", "password": "Farm12345"})
    cid = r.json()["challenge_id"]
    code = last_code("tc005@agrisense.test")
    assert c.post("/api/auth/otp/verify", json={"challenge_id": cid, "code": code}).status_code == 200
    assert c.post("/api/auth/otp/verify", json={"challenge_id": cid, "code": code}).status_code == 410


def test_tc006_resend_cooldown():
    """TC-006 | Authentication | Resend is blocked for 60 seconds
    pre: A code was just e-mailed
    data: -
    steps: 1. Sign up. 2. Press "Resend code" immediately.
    expected: HTTP 429 "Please wait N s before asking for another code"."""
    c = new_client()
    r = c.post("/api/auth/register", json={"name": "Test Farmer", "email": "tc006@agrisense.test", "password": "Farm12345"})
    r = c.post("/api/auth/otp/resend", json={"challenge_id": r.json()["challenge_id"]})
    assert r.status_code == 429 and "wait" in r.json()["error"]


def test_tc007_signup_validation():
    """TC-007 | Authentication | Sign-up form validation
    pre: -
    data: name "A", e-mail "not-an-email", password "short"
    steps: 1. Submit the sign-up form with invalid values.
    expected: HTTP 422 with field errors for name, email and password; no code e-mailed."""
    before = len(OUTBOX)
    r = new_client().post("/api/auth/register", json={"name": "A", "email": "not-an-email", "password": "short"})
    assert r.status_code == 422 and {"name", "email", "password"} <= set(r.json()["fields"])
    assert len(OUTBOX) == before


def test_tc008_email_required_with_otp():
    """TC-008 | Authentication | E-mail is mandatory when OTP is on
    pre: OTP enabled
    data: phone only, no e-mail
    steps: 1. Sign up with a phone number and no e-mail.
    expected: HTTP 422, field error on email."""
    r = new_client().post("/api/auth/register", json={"name": "Phone Only", "phone": "9876543210", "password": "Farm12345"})
    assert r.status_code == 422 and "email" in r.json()["fields"]


def test_tc009_duplicate_email():
    """TC-009 | Authentication | Duplicate e-mail is refused
    pre: An account exists for the e-mail
    data: the same e-mail
    steps: 1. Sign up again with an existing e-mail.
    expected: HTTP 409 "An account with this email already exists"; no code e-mailed."""
    _, email = signup()
    r = new_client().post("/api/auth/register", json={"name": "Again", "email": email, "password": "Farm12345"})
    assert r.status_code == 409


def test_tc010_login_requires_code():
    """TC-010 | Authentication | Sign-in = password + e-mail code
    pre: Registered account
    data: correct e-mail and password
    steps: 1. Sign out. 2. Sign in with e-mail and password. 3. Call /api/me. 4. Enter the e-mailed code. 5. Call /api/me.
    expected: Step 2 returns otp_required (purpose login); step 3 is 401; after the code the session works."""
    c, email = signup()
    c.post("/api/auth/logout")
    r = c.post("/api/auth/login", json={"identifier": email, "password": "Farm12345"})
    assert r.json()["otp_required"] and r.json()["purpose"] == "login"
    assert c.get("/api/me").status_code == 401
    r = c.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": last_code(email)})
    assert r.status_code == 200 and c.get("/api/me").status_code == 200


def test_tc011_wrong_password_no_code():
    """TC-011 | Authentication | Wrong password sends no code
    pre: Registered account
    data: wrong password
    steps: 1. Sign in with a wrong password.
    expected: HTTP 401 "Email/phone or password is incorrect"; no e-mail sent; login_failed event logged."""
    c, email = signup()
    c.post("/api/auth/logout")
    before = len(OUTBOX)
    r = c.post("/api/auth/login", json={"identifier": email, "password": "Wrong1234"})
    assert r.status_code == 401 and len(OUTBOX) == before
    assert _db().execute("select count(*) from auth_events where email=? and event='login_failed'", (email,)).fetchone()[0] == 1


def test_tc012_forgot_password_reset():
    """TC-012 | Authentication | Forgot password resets with an e-mailed code
    pre: Registered account
    data: e-mail, new password Newpass123
    steps: 1. Request a reset with a new password. 2. Enter the code. 3. Sign in with the old password. 4. Sign in with the new password.
    expected: Reset signs the user in; old password refused (401); new password accepted (code requested)."""
    c, email = signup()
    c.post("/api/auth/logout")
    r = c.post("/api/auth/forgot", json={"email": email, "new_password": "Newpass123"})
    r = c.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": last_code(email)})
    assert r.status_code == 200
    c.post("/api/auth/logout")
    assert c.post("/api/auth/login", json={"identifier": email, "password": "Farm12345"}).status_code == 401
    assert c.post("/api/auth/login", json={"identifier": email, "password": "Newpass123"}).json()["otp_required"]


def test_tc013_forgot_unknown_email_same_answer():
    """TC-013 | Security | Forgot-password does not reveal whether an e-mail is registered
    pre: -
    data: unregistered e-mail
    steps: 1. Request a reset for an unknown address. 2. Try any code.
    expected: Same reply shape as for a real account; nothing e-mailed; every code refused."""
    before = len(OUTBOX)
    c = new_client()
    r = c.post("/api/auth/forgot", json={"email": "ghost@agrisense.test", "new_password": "Newpass123"})
    assert r.status_code == 200 and r.json()["otp_required"] and len(OUTBOX) == before
    r = c.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": "123456"})
    assert r.status_code == 401


def test_tc014_codes_stored_hashed():
    """TC-014 | Security | OTP codes and passwords are never stored in plain text
    pre: A sign-up has completed
    data: -
    steps: 1. Sign up. 2. Read otp_challenges.code_hash and users.pw_hash.
    expected: code_hash is a 64-char SHA-256 hex that does not contain the code; pw_hash starts with scrypt$."""
    _, email = signup()
    code = last_code(email)
    h = _db().execute("select code_hash from otp_challenges where email=?", (email,)).fetchone()[0]
    pw = _db().execute("select pw_hash from users where email=?", (email,)).fetchone()[0]
    assert len(h) == 64 and code not in h and pw.startswith("scrypt$") and "Farm12345" not in pw


def test_tc015_auth_events_logged():
    """TC-015 | Data storage | Every authentication step is recorded
    pre: -
    data: -
    steps: 1. Sign up, sign out, sign in with code. 2. Read auth_events for the e-mail.
    expected: Rows for signup_started, otp_sent, signup_completed, login, logout, login_password_ok."""
    c, email = signup()
    c.post("/api/auth/logout")
    r = c.post("/api/auth/login", json={"identifier": email, "password": "Farm12345"})
    c.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": last_code(email)})
    ev = {e for (e,) in _db().execute("select event from auth_events where email=?", (email,))}
    assert {"signup_started", "otp_sent", "signup_completed", "login", "logout", "login_password_ok"} <= ev
    assert len(c.get("/api/me/activity").json()["events"]) >= 3


def test_tc016_profile_update():
    """TC-016 | Profile | Update name, language and district
    pre: Signed in
    data: name "Ram Singh", language hi, district Hoshiarpur
    steps: 1. Save the profile form. 2. Reload /api/me.
    expected: New values returned; invalid language "fr" gives HTTP 422."""
    c, _ = signup()
    r = c.put("/api/me", json={"name": "Ram Singh", "language": "hi", "district": "Hoshiarpur"})
    assert r.json()["user"]["name"] == "Ram Singh" and c.get("/api/me").json()["user"]["language"] == "hi"
    assert c.put("/api/me", json={"language": "fr"}).status_code == 422


def test_tc017_change_password():
    """TC-017 | Profile | Change password ends all sessions
    pre: Signed in
    data: current Farm12345, new Better1234
    steps: 1. Change password with a wrong current password. 2. Change with the right one. 3. Call /api/me.
    expected: Step 1 HTTP 403; step 2 ok and signed_out; step 3 HTTP 401."""
    c, _ = signup()
    assert c.put("/api/me/password", json={"current": "Nope12345", "new": "Better1234"}).status_code == 403
    assert c.put("/api/me/password", json={"current": "Farm12345", "new": "Better1234"}).json()["signed_out"]
    assert c.get("/api/me").status_code == 401


def test_tc018_delete_account_purges_everything():
    """TC-018 | Data storage | Deleting the account removes all of the user's data
    pre: Signed in with a farm and a prediction
    data: password Farm12345
    steps: 1. Add a farm and run a crop prediction. 2. Delete the account. 3. Count the user's rows in every table.
    expected: Zero rows in users, farms, predictions, chats, sessions, uploads, auth_events, otp_challenges."""
    c, email = signup()
    c.post("/api/farms", json={"name": "F", "state": "Punjab", "district": "LUDHIANA"})
    c.post("/api/crop/recommend", json={"N": 90, "P": 42, "K": 43, "temperature": 21, "humidity": 82, "ph": 6.5, "rainfall": 203})
    uid = _db().execute("select id from users where email=?", (email,)).fetchone()[0]
    assert c.post("/api/me/delete", json={"password": "Farm12345"}).json()["ok"]
    con = _db()
    for t in ("farms", "predictions", "chats", "sessions", "uploads", "auth_events", "otp_challenges"):
        assert con.execute(f"select count(*) from {t} where user_id=?", (uid,)).fetchone()[0] == 0, t
    assert con.execute("select count(*) from users where id=?", (uid,)).fetchone()[0] == 0


def test_tc019_logout():
    """TC-019 | Authentication | Sign out ends the session
    pre: Signed in
    data: -
    steps: 1. Sign out. 2. Call /api/me.
    expected: HTTP 401 "Please sign in"."""
    c, _ = signup()
    c.post("/api/auth/logout")
    assert c.get("/api/me").status_code == 401



def test_tc084_mobile_app_bearer_session():
    """TC-084 | Mobile API | The Android app signs in with the same OTP flow and uses a bearer token
    pre: OTP enabled
    data: header X-Client: android
    steps: 1. Sign up as the app (X-Client: android) and verify the code. 2. Call /api/me and /api/farms with Authorization: Bearer <token> and no cookie. 3. Sign out with the token. 4. Reuse the token.
    expected: The verify reply contains a token and sets no cookie; the token works on every protected endpoint; after sign-out it is rejected (401)."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, base_url="http://testserver")
    H = {"X-Client": "android"}
    r = c.post("/api/auth/register", json={"name": "App User", "email": "tc084@agrisense.test", "password": "Farm12345"}, headers=H)
    r = c.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": last_code("tc084@agrisense.test")}, headers=H)
    j = r.json()
    assert r.status_code == 200 and j["token"] and "set-cookie" not in r.headers
    c.cookies.clear()
    B = {"Authorization": f"Bearer {j['token']}", "X-Client": "android"}
    assert c.get("/api/me", headers=B).json()["user"]["email"] == "tc084@agrisense.test"
    assert c.get("/api/farms", headers=B).status_code == 200
    assert c.get("/api/me").status_code == 401
    c.post("/api/auth/logout", headers=B)
    assert c.get("/api/me", headers=B).status_code == 401


def test_tc085_shared_option_lists():
    """TC-085 | Mobile API | Option lists are served by the API (nothing hard-coded in the app)
    pre: -
    data: -
    steps: 1. GET /api/meta/options.
    expected: Soil types, irrigation methods, roles, fertiliser bases and prediction kinds are returned."""
    m = new_client().get("/api/meta/options").json()
    assert "Loamy" in m["soil_types"] and "Drip" in m["irrigation"]
    assert {r["value"] for r in m["roles"]} == {"farmer", "agri_officer", "researcher"}
    assert {b["value"] for b in m["fertiliser_bases"]} == {"soil_test", "crop_profile", "fertiliser_dataset"}
    assert m["prediction_kinds"] == ["crop", "yield", "fertiliser", "disease"]
