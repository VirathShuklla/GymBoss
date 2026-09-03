"""Iteration-4 targeted verification of iteration-3 fixes (run with pytest)."""
import os
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"


@pytest.fixture(scope="module")
def demo():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
    assert r.status_code == 200, r.text[:300]
    return s


# FIX 1: seed_demo startup migration -> membership plans present
def test_membership_plans_present(demo):
    r = demo.get(f"{API}/plans", params={"type": "membership"})
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    items = data["items"] if isinstance(data, dict) else data
    assert len(items) >= 4, f"expected >=4 membership plans, got {len(items)}: {items}"
    for p in items:
        assert p.get("type") == "membership"
        assert "_id" not in p
        assert p.get("name")


def test_all_plan_types_queryable(demo):
    for t in ("membership", "pt", "service", "product"):
        r = demo.get(f"{API}/plans", params={"type": t})
        assert r.status_code == 200, f"{t}: {r.status_code}"
        d = r.json()
        items = d["items"] if isinstance(d, dict) else d
        assert isinstance(items, list)


def test_no_plan_missing_type(demo):
    r = demo.get(f"{API}/plans")
    d = r.json()
    items = d["items"] if isinstance(d, dict) else d
    missing = [p.get("name") for p in items if not p.get("type")]
    assert not missing, f"plans without type after migration: {missing}"


# FIX 2: staff role casing normalized to lowercase
def test_staff_roles_lowercase(demo):
    r = demo.get(f"{API}/staff")
    assert r.status_code == 200
    d = r.json()
    items = d["items"] if isinstance(d, dict) else d
    assert items, "no seeded staff"
    for s in items:
        role = s.get("role")
        assert role == role.lower(), f"staff role not lowercase: {role}"
        assert role in ("trainer", "receptionist", "manager", "owner"), role
        assert "_id" not in s


def test_staff_create_normalizes_role(demo):
    body = {"name": "TEST_RoleCase", "phone": "9000011122", "role": "Trainer",
            "email": "test_rolecase_it4@testgym.in"}
    r = demo.post(f"{API}/staff", json=body)
    assert r.status_code in (200, 201), r.text[:300]
    sid = r.json().get("id")
    try:
        assert r.json().get("role") == "trainer", r.json().get("role")
        g = demo.get(f"{API}/staff").json()
        items = g["items"] if isinstance(g, dict) else g
        got = next((x for x in items if x["id"] == sid), None)
        assert got and got["role"] == "trainer", got
    finally:
        # no DELETE /staff endpoint; cleanup_test_data.py removes TEST_ staff docs
        pass


# FIX 3: primary outlet disable -> 409
def test_primary_outlet_toggle_409(demo):
    d = demo.get(f"{API}/outlets").json()
    items = d["items"] if isinstance(d, dict) else d
    primary = next((o for o in items if o.get("is_primary") or o.get("primary")), None)
    assert primary, "no primary outlet"
    r = demo.post(f"{API}/outlets/{primary['id']}/toggle")
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text[:200]}"
    assert r.json().get("detail")


# REGRESSION: finance summary + announcements preview count + dashboard
def test_finance_summary(demo):
    r = demo.get(f"{API}/finance/summary", params={"range": "this_month"})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert "revenue" in d and "expenses" in d
    assert round(d["revenue"] - d["expenses"], 2) == round(d.get("net", d["revenue"] - d["expenses"]), 2)


def test_announcement_audience_count(demo):
    for aud in ("all", "all_active"):
        r = demo.post(f"{API}/announcements/audience-count", json={"audience": aud})
        assert r.status_code == 200, f"{aud}: {r.text[:300]}"
        assert r.json().get("count", 0) > 0, f"{aud} count = 0"


# REGRESSION: super admin console
def test_super_admin_overview():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": "GymBoss", "password": "GymBoss@2026"})
    assert r.status_code == 200, r.text[:300]
    o = s.get(f"{API}/admin/overview")
    assert o.status_code == 200, o.text[:300]
    g = s.get(f"{API}/admin/gyms")
    assert g.status_code == 200
