"""Dynasty 8 backend API tests."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://dynasty-crm-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
ANSATT_TOKEN = os.environ.get("ANSATT_TOKEN")


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Health & public ----------
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_price_matrix():
    r = requests.get(f"{API}/price-matrix")
    assert r.status_code == 200
    d = r.json()
    assert "Oslo Sentrum" in d["zones"]
    assert "MLO" in d["packages"]
    assert d["matrix"]["Oslo Sentrum"]["MLO"] == 26000
    assert "garasje" in d["addons"]
    assert any(x["value"] == "ansatt" for x in d["discounts"])


def test_price_calculator_27810():
    r = requests.post(f"{API}/price-calculator", json={
        "zone": "Oslo Sentrum", "package": "MLO",
        "addons": ["garasje", "hage"], "tenant_count": 2, "discount_type": "10"
    })
    assert r.status_code == 200
    d = r.json()
    assert d["base_price"] == 26000
    assert d["total_price"] == 27810
    assert d["discount_percent"] == 10


# ---------- Auth ----------
def test_auth_login_required():
    r = requests.post(f"{API}/auth/login", json={})
    assert r.status_code == 400


def test_auth_me_requires_token():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


def test_auth_me_admin():
    r = requests.get(f"{API}/auth/me", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert r.json()["email"] == "admin@dynasty8.no"


def test_auth_me_ansatt():
    r = requests.get(f"{API}/auth/me", headers=H(ANSATT_TOKEN))
    assert r.status_code == 200
    assert r.json()["role"] == "ansatt"


# ---------- Sales CRUD + RBAC ----------
created_sale_id = None


def test_create_sale_as_ansatt():
    global created_sale_id
    payload = {
        "customer_name": "TEST_Ola", "phone": "+47 900 12 345",
        "address": "Karl Johans gate 1", "zone": "Oslo Sentrum",
        "package": "MLO", "addons": ["garasje", "hage"],
        "tenant_count": 2, "discount_type": "10",
        "sale_date": "2026-02-15", "comment": "regression",
        "status": "aktiv",
    }
    r = requests.post(f"{API}/sales", json=payload, headers=H(ANSATT_TOKEN))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total_price"] == 27810
    assert d["base_price"] == 26000
    assert d["discount_percent"] == 10
    assert d["employee_email"] == "sara@dynasty8.no"
    created_sale_id = d["sale_id"]


def test_ansatt_cannot_update():
    assert created_sale_id
    r = requests.patch(f"{API}/sales/{created_sale_id}",
                       json={"status": "betalt"}, headers=H(ANSATT_TOKEN))
    assert r.status_code == 403


def test_ansatt_cannot_delete():
    assert created_sale_id
    r = requests.delete(f"{API}/sales/{created_sale_id}", headers=H(ANSATT_TOKEN))
    assert r.status_code == 403


def test_admin_can_update_recalculates():
    assert created_sale_id
    r = requests.patch(f"{API}/sales/{created_sale_id}",
                       json={"discount_type": "15"}, headers=H(ADMIN_TOKEN))
    assert r.status_code == 200, r.text
    d = r.json()
    # subtotal 30900 * 0.85 = 26265
    assert d["total_price"] == 26265
    assert d["discount_percent"] == 15


def test_list_sales_mine_ansatt():
    r = requests.get(f"{API}/sales?mine=true", headers=H(ANSATT_TOKEN))
    assert r.status_code == 200
    sales = r.json()
    assert all(s["employee_email"] == "sara@dynasty8.no" for s in sales)
    assert any(s["sale_id"] == created_sale_id for s in sales)


def test_list_sales_admin_all_and_filter():
    r = requests.get(f"{API}/sales", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    all_sales = r.json()
    assert len(all_sales) >= 1
    r2 = requests.get(f"{API}/sales?zone=Oslo Sentrum&package=MLO", headers=H(ADMIN_TOKEN))
    assert r2.status_code == 200
    assert all(s["zone"] == "Oslo Sentrum" and s["package"] == "MLO" for s in r2.json())


def test_stats_dashboard_ansatt():
    r = requests.get(f"{API}/stats/dashboard", headers=H(ANSATT_TOKEN))
    assert r.status_code == 200
    d = r.json()
    assert "month_revenue" in d and "month_count" in d and "recent_sales" in d


def test_stats_admin():
    r = requests.get(f"{API}/stats/admin", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    d = r.json()
    for k in ("total_revenue", "per_employee", "per_zone", "per_month"):
        assert k in d


def test_stats_admin_forbidden_for_ansatt():
    r = requests.get(f"{API}/stats/admin", headers=H(ANSATT_TOKEN))
    assert r.status_code == 403


def test_users_admin_only():
    r = requests.get(f"{API}/users", headers=H(ANSATT_TOKEN))
    assert r.status_code == 403
    r2 = requests.get(f"{API}/users", headers=H(ADMIN_TOKEN))
    assert r2.status_code == 200
    assert len(r2.json()) >= 2


def test_activity_log_admin():
    r = requests.get(f"{API}/activity-log", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    actions = {x["action"] for x in r.json()}
    assert "sale_created" in actions
    assert "sale_updated" in actions


def test_export_csv():
    r = requests.get(f"{API}/export/csv", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert b"Kunde" in r.content


def test_export_xlsx():
    r = requests.get(f"{API}/export/xlsx", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    assert "spreadsheet" in r.headers.get("content-type", "")


def test_export_forbidden_for_ansatt():
    r = requests.get(f"{API}/export/csv", headers=H(ANSATT_TOKEN))
    assert r.status_code == 403


def test_admin_delete():
    assert created_sale_id
    r = requests.delete(f"{API}/sales/{created_sale_id}", headers=H(ADMIN_TOKEN))
    assert r.status_code == 200
    r2 = requests.get(f"{API}/sales/{created_sale_id}", headers=H(ADMIN_TOKEN))
    assert r2.status_code == 404
