"""Shared fixtures. Every test runs against a throwaway SQLite database, with e-mail OTP switched
ON and delivery captured in memory (no real e-mail is sent). External services (Open-Meteo,
NASA POWER, SoilGrids, Mistral) are called for real by the tests marked `live`."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AGRISENSE_STORAGE"] = tempfile.mkdtemp(prefix="agrisense_test_")
os.environ["OTP_WEBHOOK_URL"] = "http://otp.test/webhook/agrisense-otp"
os.environ["OTP_SHARED_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app import otp  # noqa: E402
from app.main import app  # noqa: E402

LEAF = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"
OUTBOX = []          # (email, code, purpose) captured instead of sending


def _fake_deliver(email, code, purpose):
    OUTBOX.append((email, code, purpose))
    return None


otp.deliver = _fake_deliver


def last_code(email):
    for e, c, _ in reversed(OUTBOX):
        if e == email:
            return c
    return None


def new_client():
    return TestClient(app, base_url="http://testserver")


_n = [0]


def signup(client=None, password="Farm12345", **extra):
    """Full sign-up through the OTP step. Returns (client, email)."""
    client = client or new_client()
    _n[0] += 1
    email = f"user{_n[0]}_{os.getpid()}@agrisense.test"
    body = {"name": "Test Farmer", "email": email, "password": password, "state": "Punjab", "district": "Ludhiana"}
    body.update(extra)
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 200, r.text
    r = client.post("/api/auth/otp/verify", json={"challenge_id": r.json()["challenge_id"], "code": last_code(email)})
    assert r.status_code == 200, r.text
    return client, email


@pytest.fixture
def user():
    return signup()


@pytest.fixture
def farm(user):
    c, _ = user
    r = c.post("/api/farms", json={"name": "North Field", "state": "Punjab", "district": "LUDHIANA",
                                   "lat": 30.90, "lon": 75.85, "area_ha": 3, "soil_type": "Loamy"})
    assert r.status_code == 200
    return c, r.json()["farm"]


def leaf_image(cls, index=0):
    files = sorted((LEAF / cls).iterdir())
    return files[index].read_bytes()
