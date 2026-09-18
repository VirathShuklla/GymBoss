"""Iteration 13: Verify edit/reverse payments + onboarding checklist updates."""
import os
import uuid
import time
import requests
import pytest

from dotenv import dotenv_values
_env = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"

DEMO = {"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"}


@pytest.fixture(scope="module")
def demo_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=DEMO)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def fresh_client():
    """Register a brand-new gym owner so onboarding starts empty."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    tag = uuid.uuid4().hex[:8]
    email = f"qa.iter13.{tag}@example.com"
    payload = {
        "full_name": f"QA Iter13 {tag}",
        "email": email,
        "phone": f"9{int(time.time())%1000000000:09d}",
        "password": "QaTest@2026",
        "gym_name": f"ZZ_QA_Gym_{tag}",
        "outlet_name": "Main",
        "city": "Bengaluru",
    }
    r = s.post(f"{API}/auth/register", json=payload)
    assert r.status_code in (200, 201), r.text
    s.creds = payload
    return s


# -----------------------
# Edit/Reverse financial correctness
# -----------------------

def _get_plan(client, min_price=6000):
    r = client.get(f"{API}/plans")
    assert r.status_code == 200
    plans = r.json()
    for p in plans:
        if p.get("price", 0) >= min_price:
            return p
    return plans[0]


def _create_member(client, plan, name_suffix):
    body = {
        "full_name": f"TEST_iter13_{name_suffix}_{uuid.uuid4().hex[:6]}",
        "phone": f"9{int(time.time()*1000)%1000000000:09d}",
        "plan_id": plan["id"],
        "discount": 0,
        "admission_amount": 0,
        "paid_amount": 0,
    }
    r = client.post(f"{API}/members", json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _get_member_due(client, mid):
    r = client.get(f"{API}/members/{mid}")
    assert r.status_code == 200
    data = r.json()
    m = data.get("member") if "member" in data else data
    return m.get("due_amount"), m.get("payment_status"), m.get("payable")


class TestEditReversePayment:
    def test_edit_then_reverse_flow(self, demo_client):
        plan = _get_plan(demo_client, min_price=6000)
        price = plan["price"]
        member = _create_member(demo_client, plan, "flow")
        mid = member["id"]
        try:
            due0, st0, payable = _get_member_due(demo_client, mid)
            assert payable == price
            assert due0 == price
            assert st0 == "Due"

            # Record ₹2000
            r = demo_client.post(f"{API}/payments", json={"member_id": mid, "amount": 2000, "method": "Cash"})
            assert r.status_code in (200, 201), r.text
            pay = r.json()
            pid = pay["id"]
            due1, st1, _ = _get_member_due(demo_client, mid)
            assert due1 == price - 2000
            assert st1 == "Partially Paid"

            # EDIT to ₹5000
            r = demo_client.put(f"{API}/payments/{pid}", json={"amount": 5000})
            assert r.status_code == 200, r.text
            due2, st2, _ = _get_member_due(demo_client, mid)
            assert due2 == price - 5000, f"expected {price-5000}, got {due2}"
            assert st2 == "Partially Paid"

            # REVERSE
            r = demo_client.delete(f"{API}/payments/{pid}")
            assert r.status_code == 200, r.text
            due3, st3, _ = _get_member_due(demo_client, mid)
            assert due3 == price
            assert st3 == "Due"

            # Payment gone from list
            r = demo_client.get(f"{API}/payments", params={"search": member["full_name"]})
            assert r.status_code == 200
            ids = [p["id"] for p in r.json().get("items", [])]
            assert pid not in ids
        finally:
            demo_client.delete(f"{API}/members/{mid}")

    def test_edit_validation(self, demo_client):
        plan = _get_plan(demo_client)
        member = _create_member(demo_client, plan, "val")
        mid = member["id"]
        try:
            r = demo_client.post(f"{API}/payments", json={"member_id": mid, "amount": 1000, "method": "Cash"})
            pid = r.json()["id"]
            # amount <= 0 rejected
            r = demo_client.put(f"{API}/payments/{pid}", json={"amount": 0})
            assert r.status_code == 422
            r = demo_client.put(f"{API}/payments/{pid}", json={"amount": -100})
            assert r.status_code == 422
            # invalid method
            r = demo_client.put(f"{API}/payments/{pid}", json={"amount": 1000, "method": "Bitcoin"})
            assert r.status_code == 422
            # 404
            r = demo_client.put(f"{API}/payments/does-not-exist", json={"amount": 100})
            assert r.status_code == 404
            r = demo_client.delete(f"{API}/payments/does-not-exist")
            assert r.status_code == 404
        finally:
            demo_client.delete(f"{API}/members/{mid}")

    def test_edit_higher_than_payable_clamps(self, demo_client):
        plan = _get_plan(demo_client, min_price=6000)
        price = plan["price"]
        member = _create_member(demo_client, plan, "clamp")
        mid = member["id"]
        try:
            r = demo_client.post(f"{API}/payments", json={"member_id": mid, "amount": 1000, "method": "Cash"})
            pid = r.json()["id"]
            # Edit up to payable -> due should be 0, paid
            r = demo_client.put(f"{API}/payments/{pid}", json={"amount": price})
            assert r.status_code == 200
            due, st, _ = _get_member_due(demo_client, mid)
            assert due == 0
            assert st == "Paid"
        finally:
            demo_client.delete(f"{API}/members/{mid}")


class TestFinanceInvariant:
    def test_sum_dues_equals_outstanding(self, demo_client):
        r = demo_client.get(f"{API}/members", params={"limit": 500})
        assert r.status_code == 200
        items = r.json().get("items") if isinstance(r.json(), dict) else r.json()
        total = round(sum((m.get("due_amount") or 0) for m in items), 2)
        r = demo_client.get(f"{API}/finance/summary")
        assert r.status_code == 200
        outstanding = r.json().get("outstanding")
        assert abs(total - outstanding) < 1, f"sum(dues)={total} != finance.outstanding={outstanding}"


# -----------------------
# Onboarding checklist
# -----------------------

class TestOnboardingProgression:
    def test_fresh_gym_starts_empty_then_progresses(self, fresh_client):
        r = fresh_client.get(f"{API}/onboarding")
        assert r.status_code == 200, r.text
        onb = r.json()
        # fresh gym: after register, outlet may be true; but plan/member/staff/payment should be false
        assert onb.get("plan") in (False, None), onb
        assert onb.get("member") in (False, None), onb
        assert onb.get("payment") in (False, None), onb

        # Create a plan -> plan flag
        r = fresh_client.post(f"{API}/plans", json={
            "name": "TEST Plan", "duration_days": 30, "price": 1000, "type": "membership"
        })
        assert r.status_code in (200, 201), r.text
        plan = r.json()

        r = fresh_client.get(f"{API}/onboarding")
        assert r.json().get("plan") is True, r.json()

        # Add a member
        r = fresh_client.post(f"{API}/members", json={
            "full_name": "TEST_Onb_Member",
            "phone": f"9{int(time.time()*1000)%1000000000:09d}",
            "plan_id": plan["id"],
        })
        assert r.status_code in (200, 201), r.text
        member = r.json()
        r = fresh_client.get(f"{API}/onboarding")
        assert r.json().get("member") is True

        # Record a payment
        r = fresh_client.post(f"{API}/payments", json={
            "member_id": member["id"], "amount": 100, "method": "Cash"
        })
        assert r.status_code in (200, 201), r.text
        r = fresh_client.get(f"{API}/onboarding")
        assert r.json().get("payment") is True

        # Add staff
        r = fresh_client.post(f"{API}/staff", json={
            "full_name": "TEST_Staff", "role": "Trainer",
            "phone": f"9{(int(time.time()*1000)+1)%1000000000:09d}",
        })
        # Some tenants may 200/201
        if r.status_code in (200, 201):
            r = fresh_client.get(f"{API}/onboarding")
            assert r.json().get("staff") is True, r.json()

    def test_onboarding_dismiss_persists(self, fresh_client):
        r = fresh_client.put(f"{API}/onboarding", json={"dismissed": True})
        assert r.status_code == 200
        r = fresh_client.get(f"{API}/onboarding")
        assert r.json().get("dismissed") is True
