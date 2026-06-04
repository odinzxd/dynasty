"""Dynasty 8 - employee management endpoints regression."""
import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://dynasty-crm-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]
ANSATT_TOKEN = os.environ["ANSATT_TOKEN"]
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def H(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]


@pytest.fixture(scope="module")
def admin_id():
    r = requests.get(f"{API}/auth/me", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    return r.json()["user_id"]


@pytest.fixture(scope="module")
def ansatt_id():
    r = requests.get(f"{API}/auth/me", headers=H(ANSATT_TOKEN))
    assert r.status_code == 200
    return r.json()["user_id"]


@pytest.fixture()
def temp_user(db):
    """Create an isolated temp user + session for destructive tests; cleanup after."""
    uid = f"user_test_tmp_{uuid.uuid4().hex[:8]}"
    tok = f"test_session_tmp_{uuid.uuid4().hex[:8]}"
    from datetime import datetime, timezone, timedelta
    db.users.insert_one({
        "user_id": uid, "email": f"{uid}@dynasty8.no", "name": "Temp Bruker",
        "role": "ansatt", "employee_number": "T999", "picture": None,
        "is_active": True, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    db.user_sessions.insert_one({
        "user_id": uid, "session_token": tok,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    yield {"user_id": uid, "token": tok, "email": f"{uid}@dynasty8.no"}
    db.users.delete_one({"user_id": uid})
    db.user_sessions.delete_many({"user_id": uid})


# ---------- RBAC ----------
def test_ansatt_cannot_patch_user(ansatt_id):
    r = requests.patch(f"{API}/users/{ansatt_id}", json={"name": "X"}, headers=H(ANSATT_TOKEN))
    assert r.status_code == 403


def test_ansatt_cannot_revoke(ansatt_id):
    r = requests.post(f"{API}/users/{ansatt_id}/revoke-sessions", headers=H(ANSATT_TOKEN))
    assert r.status_code == 403


def test_ansatt_cannot_delete(ansatt_id):
    r = requests.delete(f"{API}/users/{ansatt_id}", headers=H(ANSATT_TOKEN))
    assert r.status_code == 403


# ---------- Self-targeted guards ----------
def test_admin_cannot_demote_self(admin_id):
    r = requests.patch(f"{API}/users/{admin_id}", json={"role": "ansatt"}, headers=H(ADMIN_TOKEN))
    assert r.status_code == 400


def test_admin_cannot_deactivate_self(admin_id):
    r = requests.patch(f"{API}/users/{admin_id}", json={"is_active": False}, headers=H(ADMIN_TOKEN))
    assert r.status_code == 400


def test_admin_cannot_revoke_self(admin_id):
    r = requests.post(f"{API}/users/{admin_id}/revoke-sessions", headers=H(ADMIN_TOKEN))
    assert r.status_code == 400


def test_admin_cannot_delete_self(admin_id):
    r = requests.delete(f"{API}/users/{admin_id}", headers=H(ADMIN_TOKEN))
    assert r.status_code == 400


# ---------- Update name + employee_number + role ----------
def test_patch_updates_name_empnum_role_and_propagates_to_sales(db, temp_user):
    uid = temp_user["user_id"]
    # seed a sale for this user
    sale_id = f"sale_test_{uuid.uuid4().hex[:8]}"
    db.sales.insert_one({
        "sale_id": sale_id, "customer_name": "TEST_Kunde", "phone": "+47 900",
        "address": "x", "zone": "Oslo Sentrum", "package": "MLO", "addons": [],
        "tenant_count": 0, "discount_type": None, "discount_percent": 0,
        "base_price": 26000, "total_price": 26000, "sale_date": "2026-02-01",
        "employee_id": uid, "employee_name": "Temp Bruker",
        "employee_email": temp_user["email"], "comment": "", "status": "aktiv",
        "created_at": "2026-02-01T00:00:00+00:00", "updated_at": "2026-02-01T00:00:00+00:00",
    })

    r = requests.patch(f"{API}/users/{uid}", headers=H(ADMIN_TOKEN), json={
        "name": "Renamed Person", "employee_number": "T123", "role": "admin"
    })
    assert r.status_code == 200, r.text

    # verify via /users
    r2 = requests.get(f"{API}/users", headers=H(ADMIN_TOKEN))
    assert r2.status_code == 200
    u = next(x for x in r2.json() if x["user_id"] == uid)
    assert u["name"] == "Renamed Person"
    assert u["employee_number"] == "T123"
    assert u["role"] == "admin"

    # sale's employee_name updated
    sale = db.sales.find_one({"sale_id": sale_id})
    assert sale["employee_name"] == "Renamed Person"
    db.sales.delete_one({"sale_id": sale_id})


def test_patch_invalid_role(temp_user):
    r = requests.patch(f"{API}/users/{temp_user['user_id']}",
                       headers=H(ADMIN_TOKEN), json={"role": "boss"})
    assert r.status_code == 400


def test_patch_no_fields(temp_user):
    r = requests.patch(f"{API}/users/{temp_user['user_id']}", headers=H(ADMIN_TOKEN), json={})
    assert r.status_code == 400


def test_patch_unknown_user():
    r = requests.patch(f"{API}/users/nope_xxx", headers=H(ADMIN_TOKEN), json={"name": "X"})
    assert r.status_code == 404


# ---------- Deactivation revokes sessions + blocks /auth/me ----------
def test_deactivate_revokes_sessions_and_blocks_me(db, temp_user):
    uid, tok = temp_user["user_id"], temp_user["token"]
    # baseline: token works
    r0 = requests.get(f"{API}/auth/me", headers=H(tok))
    assert r0.status_code == 200

    r = requests.patch(f"{API}/users/{uid}", headers=H(ADMIN_TOKEN),
                       json={"is_active": False})
    assert r.status_code == 200
    # all sessions should be deleted
    assert db.user_sessions.count_documents({"user_id": uid}) == 0

    # token is now invalid (session deleted) => 401
    r2 = requests.get(f"{API}/auth/me", headers=H(tok))
    assert r2.status_code == 401


def test_deactivated_user_with_session_gets_403_and_session_wiped(db, temp_user):
    """If somehow a session exists for an inactive user, /auth/me returns 403 AND wipes sessions."""
    uid, tok = temp_user["user_id"], temp_user["token"]
    # manually mark inactive WITHOUT going through PATCH (so sessions survive)
    db.users.update_one({"user_id": uid}, {"$set": {"is_active": False}})
    assert db.user_sessions.count_documents({"user_id": uid}) == 1

    r = requests.get(f"{API}/auth/me", headers=H(tok))
    assert r.status_code == 403
    # session also wiped by get_current_user
    assert db.user_sessions.count_documents({"user_id": uid}) == 0


# ---------- Revoke sessions endpoint ----------
def test_revoke_sessions(db, temp_user):
    uid, tok = temp_user["user_id"], temp_user["token"]
    assert db.user_sessions.count_documents({"user_id": uid}) == 1

    r = requests.post(f"{API}/users/{uid}/revoke-sessions", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["revoked"] == 1
    assert db.user_sessions.count_documents({"user_id": uid}) == 0

    # token is dead
    r2 = requests.get(f"{API}/auth/me", headers=H(tok))
    assert r2.status_code == 401


def test_revoke_unknown_user():
    r = requests.post(f"{API}/users/nope_xxx/revoke-sessions", headers=H(ADMIN_TOKEN))
    assert r.status_code == 404


# ---------- Delete user ----------
def test_delete_user(db, temp_user):
    uid = temp_user["user_id"]
    r = requests.delete(f"{API}/users/{uid}", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    assert db.users.count_documents({"user_id": uid}) == 0
    assert db.user_sessions.count_documents({"user_id": uid}) == 0


def test_delete_unknown_user():
    r = requests.delete(f"{API}/users/nope_xxx", headers=H(ADMIN_TOKEN))
    assert r.status_code == 404


# ---------- Activity log entries ----------
def test_activity_log_records_user_actions(db, temp_user):
    uid = temp_user["user_id"]
    # trigger 3 actions
    requests.patch(f"{API}/users/{uid}", headers=H(ADMIN_TOKEN), json={"name": "Aktivitet"})
    requests.post(f"{API}/users/{uid}/revoke-sessions", headers=H(ADMIN_TOKEN))
    requests.delete(f"{API}/users/{uid}", headers=H(ADMIN_TOKEN))
    time.sleep(0.2)

    r = requests.get(f"{API}/activity-log", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    actions = {x["action"] for x in r.json() if x.get("details", {}).get("user_id") == uid}
    assert {"user_updated", "user_kicked", "user_deleted"}.issubset(actions)
