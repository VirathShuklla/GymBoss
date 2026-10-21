"""Iteration 12: Financial correctness end-to-end tests for GymBoss_VVO.

GET /api/members/{id} returns {"member": {...}, "payments": [...]}
Fields: payable, due_amount, plan_price, admission_amount, discount.
POST /api/members returns member_public (member fields flat).
"""
import os
import uuid
import pytest
import requests


def _get_base():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE = _get_base()
API = f"{BASE}/api"
CRED = {"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"}


def _login():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=CRED, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def s():
    return _login()


@pytest.fixture(scope="module")
def plan_6000(s):
    # Find a plan priced 6000 or create one
    r = s.get(f"{API}/plans", timeout=15)
    plans = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    for p in plans:
        if float(p.get("price", 0)) == 6000 and p.get("type", "membership") == "membership":
            return p
    body = {"name": f"TEST_Plan6k_{uuid.uuid4().hex[:6]}", "type": "membership",
            "duration_type": "months", "duration": 1, "price": 6000}
    r = s.post(f"{API}/plans", json=body, timeout=15)
    assert r.status_code in (200, 201), r.text
    return r.json()


# ---------- 1. All members financially consistent ----------
def test_all_members_consistent(s):
    r = s.get(f"{API}/members?limit=500", timeout=30)
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert len(items) > 0
    bad = []
    for m in items:
        r2 = s.get(f"{API}/members/{m['id']}", timeout=15)
        d = r2.json()
        mem = d["member"]
        payments = d.get("payments", [])
        total_paid = sum(float(p["amount"]) for p in payments)
        payable = float(mem.get("payable", 0))
        due = float(mem.get("due_amount", 0))
        price = float(mem.get("plan_price", 0))
        adm = float(mem.get("admission_amount", 0) or 0)
        disc = float(mem.get("discount", 0) or 0)
        expected_payable = max(0.0, round(price + adm - disc, 2))
        expected_due = max(0.0, round(payable - total_paid, 2))
        if abs(due - expected_due) > 0.01 or abs(payable - expected_payable) > 0.01:
            bad.append({
                "code": mem.get("member_code"), "price": price, "adm": adm, "disc": disc,
                "payable": payable, "exp_payable": expected_payable,
                "paid": total_paid, "due": due, "exp_due": expected_due,
            })
    assert not bad, f"{len(bad)} inconsistent, first 5: {bad[:5]}"


def test_sum_dues_equals_finance_outstanding(s):
    r = s.get(f"{API}/members?limit=500", timeout=30)
    items = r.json().get("items", [])
    total = sum(float(m.get("due_amount", 0)) for m in items)
    r2 = s.get(f"{API}/finance/summary", timeout=15)
    assert r2.status_code == 200
    outstanding = float(r2.json().get("outstanding", 0))
    assert abs(total - outstanding) < 1.0, f"sum(dues)={total} outstanding={outstanding}"


# ---------- 2. Create with examples ----------
def _mkbody(plan_id, **kw):
    b = {
        "full_name": f"TEST_Fin_{uuid.uuid4().hex[:6]}",
        "phone": f"+9199{uuid.uuid4().int % 100000000:08d}",
        "gender": "male",
        "plan_id": plan_id,
        "discount": 0,
        "admission_amount": 0,
        "amount_paid": 0,
        "payment_method": "Cash",
    }
    b.update(kw)
    return b


def test_examples_from_brief(s, plan_6000):
    pid = plan_6000["id"]
    cases = [
        # (discount, admission, amount_paid, expected_payable, expected_due)
        (0, 0, 0, 6000, 6000),
        (0, 0, 2000, 6000, 4000),
        (0, 0, 6000, 6000, 0),
        (1000, 0, 0, 5000, 5000),
        (0, 1000, 0, 7000, 7000),
    ]
    created = []
    try:
        for disc, adm, paid, exp_p, exp_d in cases:
            r = s.post(f"{API}/members", json=_mkbody(pid, discount=disc, admission_amount=adm, amount_paid=paid), timeout=20)
            assert r.status_code in (200, 201), r.text
            m = r.json()
            created.append(m["id"])
            assert abs(float(m["payable"]) - exp_p) < 0.01, (disc, adm, paid, m)
            assert abs(float(m["due_amount"]) - exp_d) < 0.01, (disc, adm, paid, m)
    finally:
        for mid in created:
            s.delete(f"{API}/members/{mid}", timeout=10)


# ---------- 3. Partial and full payment flow ----------
def test_partial_then_full_payment(s, plan_6000):
    r = s.post(f"{API}/members", json=_mkbody(plan_6000["id"]), timeout=20)
    assert r.status_code in (200, 201)
    mid = r.json()["id"]
    try:
        # partial 2000
        r = s.post(f"{API}/payments", json={"member_id": mid, "amount": 2000, "method": "Cash"}, timeout=15)
        assert r.status_code in (200, 201), r.text
        mem = s.get(f"{API}/members/{mid}").json()["member"]
        assert abs(float(mem["due_amount"]) - 4000) < 0.01
        assert mem["payment_status"] == "Partially Paid", mem["payment_status"]
        # remaining 4000
        r = s.post(f"{API}/payments", json={"member_id": mid, "amount": 4000, "method": "UPI"}, timeout=15)
        assert r.status_code in (200, 201), r.text
        mem = s.get(f"{API}/members/{mid}").json()["member"]
        assert abs(float(mem["due_amount"])) < 0.01
        assert mem["payment_status"] == "Paid", mem["payment_status"]
        # visible in /api/payments
        pays = s.get(f"{API}/payments?member_id={mid}").json()
        items = pays.get("items", pays if isinstance(pays, list) else [])
        assert sum(1 for p in items if p.get("member_id") == mid) >= 2
    finally:
        s.delete(f"{API}/members/{mid}", timeout=10)


# ---------- 4. Payment validation ----------
def test_payment_validation_rules(s, plan_6000):
    r = s.post(f"{API}/members", json=_mkbody(plan_6000["id"]), timeout=20)
    mid = r.json()["id"]
    try:
        # amount 0
        r = s.post(f"{API}/payments", json={"member_id": mid, "amount": 0, "method": "Cash"}, timeout=10)
        assert r.status_code == 422, r.status_code
        # amount negative
        r = s.post(f"{API}/payments", json={"member_id": mid, "amount": -100, "method": "Cash"}, timeout=10)
        assert r.status_code == 422
        # invalid method
        r = s.post(f"{API}/payments", json={"member_id": mid, "amount": 100, "method": "bitcoin"}, timeout=10)
        assert r.status_code == 422
        # missing member
        r = s.post(f"{API}/payments", json={"member_id": str(uuid.uuid4()), "amount": 100, "method": "Cash"}, timeout=10)
        assert r.status_code == 404
    finally:
        s.delete(f"{API}/members/{mid}", timeout=10)


# ---------- 5. Renew flow ----------
def test_renew_recalcs_and_extends(s, plan_6000):
    r = s.post(f"{API}/members", json=_mkbody(plan_6000["id"], amount_paid=6000), timeout=20)
    mid = r.json()["id"]
    orig_expiry = r.json()["membership_expiry"]
    try:
        r = s.post(f"{API}/members/{mid}/renew",
                   json={"plan_id": plan_6000["id"], "amount_paid": 3000, "discount": 0, "payment_method": "Cash"},
                   timeout=15)
        assert r.status_code in (200, 201), r.text
        mem = s.get(f"{API}/members/{mid}").json()["member"]
        # After renew: payable = 6000 - 0 = 6000, paid=3000 -> due=3000
        assert abs(float(mem["payable"]) - 6000) < 0.01, mem
        assert abs(float(mem["due_amount"]) - 3000) < 0.01, mem
        assert mem["membership_expiry"] > orig_expiry, (orig_expiry, mem["membership_expiry"])
    finally:
        s.delete(f"{API}/members/{mid}", timeout=10)


# ---------- 6. Filters ----------
def test_due_filter(s):
    r = s.get(f"{API}/members?due=true&limit=200", timeout=20)
    assert r.status_code == 200
    for m in r.json().get("items", []):
        assert float(m.get("due_amount", 0)) > 0


# ---------- 7. Persistence ----------
def test_persistence_after_relogin(s):
    o1 = float(s.get(f"{API}/finance/summary").json()["outstanding"])
    s2 = _login()
    o2 = float(s2.get(f"{API}/finance/summary").json()["outstanding"])
    assert abs(o1 - o2) < 1.0


# ---------- 8. Reports/dashboard endpoints ----------
def test_reports_and_dashboard(s):
    for path in [
        "/reports/revenue-trend?range=month",
        "/reports/outstanding-dues",
        "/reports/membership-expiry",
        "/reports/enquiry-conversion",
        "/reports/member-growth",
        "/finance/summary?range=today",
        "/finance/summary?range=week",
        "/finance/summary?range=month",
        "/finance/summary?range=year",
        "/dashboard/summary",
    ]:
        r = s.get(f"{API}{path}", timeout=20)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
