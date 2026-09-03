"""Milestone 2-5 backend coverage: members, plans, attendance, payments, enquiries,
expenses, outlets, staff, announcements, finance, reports, export, billing, super admin,
tenant isolation."""
import os
import re
import uuid
from datetime import date, timedelta

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
_base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not _base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = _base.rstrip("/") + "/api"

TODAY = date.today()


def uid(p="TEST"):
    return f"{p}_{uuid.uuid4().hex[:8]}"


def uphone():
    return "9" + str(uuid.uuid4().int % 1000000000).zfill(9)


# ---------------- session-scoped authenticated clients ----------------

@pytest.fixture(scope="module")
def demo():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
    if r.status_code != 200:
        pytest.fail(f"demo login failed {r.status_code}: {r.text[:300]}")
    yield s
    s.close()


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"identifier": "GymBoss", "password": "GymBoss@2026"})
    if r.status_code != 200:
        pytest.fail(f"super admin login failed {r.status_code}: {r.text[:300]}")
    yield s
    s.close()


@pytest.fixture(scope="module")
def demo_ctx(demo):
    outlets = demo.get(f"{API}/outlets").json()
    plans = demo.get(f"{API}/plans").json()
    me = demo.get(f"{API}/auth/me").json()
    return {"outlets": outlets, "plans": plans, "me": me}


# ================= Plans & Catalogue =================

class TestPlans:
    created = []

    def test_list_plans(self, demo):
        r = demo.get(f"{API}/plans")
        assert r.status_code == 200
        items = r.json()
        items = items["items"] if isinstance(items, dict) else items
        assert isinstance(items, list) and len(items) > 0
        assert "_id" not in items[0]

    def test_membership_plan_crud(self, demo):
        name = uid("TEST_Plan")
        r = demo.post(f"{API}/plans", json={"name": name, "type": "membership", "duration_type": "months",
                                            "duration": 3, "price": 4500})
        assert r.status_code in (200, 201), r.text
        plan = r.json()
        pid = plan.get("id") or plan.get("plan", {}).get("id")
        assert pid
        TestPlans.created.append(pid)

        # verify persisted
        lst = demo.get(f"{API}/plans?type=membership").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        match = [p for p in lst if p["id"] == pid]
        assert match, "created plan not in list"
        assert match[0]["price"] == 4500
        assert match[0]["duration"] == 3

        # edit price
        r = demo.put(f"{API}/plans/{pid}", json={"name": name, "type": "membership", "duration_type": "months",
                                                 "duration": 3, "price": 5200})
        assert r.status_code == 200, r.text
        lst = demo.get(f"{API}/plans?type=membership").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        assert [p for p in lst if p["id"] == pid][0]["price"] == 5200

        # delete
        r = demo.delete(f"{API}/plans/{pid}")
        assert r.status_code in (200, 204), r.text
        TestPlans.created.remove(pid)
        lst = demo.get(f"{API}/plans?type=membership").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        assert not [p for p in lst if p["id"] == pid]

    @pytest.mark.parametrize("ptype,extra", [
        ("pt", {"sessions": 12, "trainer": "Rahul"}),
        ("service", {"category": "Sauna"}),
        ("product", {"inventory": 25}),
    ])
    def test_other_catalogue_types(self, demo, ptype, extra):
        body = {"name": uid(f"TEST_{ptype}"), "type": ptype, "price": 1500}
        body.update(extra)
        r = demo.post(f"{API}/plans", json=body)
        assert r.status_code in (200, 201), r.text
        pid = r.json().get("id")
        lst = demo.get(f"{API}/plans?type={ptype}").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        got = [p for p in lst if p["id"] == pid]
        assert got, f"{ptype} plan not returned by type filter"
        for k, v in extra.items():
            assert got[0].get(k) == v, f"{ptype}.{k} not persisted: {got[0].get(k)}"
        demo.delete(f"{API}/plans/{pid}")

    def test_plan_validation(self, demo):
        r = demo.post(f"{API}/plans", json={"name": "x", "price": -5})
        assert r.status_code == 422


# ================= Members =================

class TestMembers:
    member_id = None

    def test_seeded_list(self, demo):
        r = demo.get(f"{API}/members?limit=100")
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 26, f"expected >=26 seeded members, got {d['total']}"
        m = d["items"][0]
        for k in ("id", "full_name", "phone", "status", "member_code"):
            assert k in m
        assert m["status"] in ("active", "expired", "expiring_soon", "frozen")
        assert "_id" not in m

    def test_pagination(self, demo):
        p1 = demo.get(f"{API}/members?page=1&limit=10").json()
        p2 = demo.get(f"{API}/members?page=2&limit=10").json()
        assert len(p1["items"]) == 10
        assert len(p2["items"]) > 0
        assert {i["id"] for i in p1["items"]}.isdisjoint({i["id"] for i in p2["items"]})

    def test_search(self, demo):
        r = demo.get(f"{API}/members?search=Aarav")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0, "search 'Aarav' returned nothing"
        assert all("aarav" in i["full_name"].lower() for i in items)

    def test_status_filter(self, demo):
        r = demo.get(f"{API}/members?status=expired&limit=100")
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(i["status"] == "expired" for i in items)

    def test_create_member_expiry_and_due(self, demo, demo_ctx):
        plans = demo_ctx["plans"]
        plans = plans["items"] if isinstance(plans, dict) else plans
        quarterly = next((p for p in plans if p.get("type", "membership") == "membership"
                          and p.get("duration_type") == "months" and p.get("duration") == 3), None)
        if not quarterly:
            quarterly = [p for p in plans if p.get("type", "membership") == "membership"][0]
        start = TODAY.isoformat()
        body = {"full_name": uid("TEST_Member"), "phone": uphone(), "plan_id": quarterly["id"],
                "membership_start": start, "amount_paid": 2000, "payment_method": "UPI",
                "gender": "male", "batch": "Morning"}
        r = demo.post(f"{API}/members", json=body)
        assert r.status_code in (200, 201), r.text
        created = r.json()
        mid = created.get("id") or created.get("member", {}).get("id")
        assert mid
        TestMembers.member_id = mid

        g = demo.get(f"{API}/members/{mid}")
        assert g.status_code == 200
        m = g.json()["member"]
        assert m["full_name"] == body["full_name"]
        assert m["batch"] == "Morning"
        # expiry
        exp = date.fromisoformat(m["membership_expiry"][:10])
        months = quarterly.get("duration") or 1
        assert abs((exp - TODAY).days - months * 30) <= 5, f"expiry {exp} not ~{months} months out"
        # due
        expected_due = max(0, quarterly["price"] - 2000)
        assert abs(m["due_amount"] - expected_due) < 0.01, f"due {m['due_amount']} != {expected_due}"
        # payment recorded
        pays = g.json()["payments"]
        assert any(abs(p["amount"] - 2000) < 0.01 for p in pays), "initial payment not recorded"

    def test_update_member(self, demo):
        mid = TestMembers.member_id
        assert mid
        r = demo.put(f"{API}/members/{mid}", json={"batch": "Evening", "notes": "TEST note"})
        assert r.status_code == 200, r.text
        m = demo.get(f"{API}/members/{mid}").json()["member"]
        assert m["batch"] == "Evening"
        assert m["notes"] == "TEST note"

    def test_freeze_unfreeze(self, demo):
        mid = TestMembers.member_id
        before = demo.get(f"{API}/members/{mid}").json()["member"]
        exp_before = date.fromisoformat(before["membership_expiry"][:10])
        until = (TODAY + timedelta(days=5)).isoformat()
        r = demo.post(f"{API}/members/{mid}/freeze",
                      json={"freeze_from": TODAY.isoformat(), "freeze_until": until, "extend_expiry": True})
        assert r.status_code == 200, r.text
        m = demo.get(f"{API}/members/{mid}").json()["member"]
        assert m["status"] == "frozen", f"status={m['status']}"
        exp_after = date.fromisoformat(m["membership_expiry"][:10])
        assert exp_after > exp_before, "expiry not extended on freeze"

        r = demo.post(f"{API}/members/{mid}/unfreeze")
        assert r.status_code == 200, r.text
        m = demo.get(f"{API}/members/{mid}").json()["member"]
        assert m["status"] != "frozen"

    def test_record_payment_reduces_due(self, demo):
        mid = TestMembers.member_id
        due_before = demo.get(f"{API}/members/{mid}").json()["member"]["due_amount"]
        r = demo.post(f"{API}/payments", json={"member_id": mid, "amount": 500, "method": "Cash"})
        assert r.status_code in (200, 201), r.text
        pay = r.json()
        pid = pay.get("id") or pay.get("payment", {}).get("id")
        assert pid
        due_after = demo.get(f"{API}/members/{mid}").json()["member"]["due_amount"]
        assert abs((due_before - due_after) - 500) < 0.01, f"due {due_before}->{due_after}"

        rec = demo.get(f"{API}/payments/{pid}/receipt")
        assert rec.status_code == 200, rec.text
        rj = rec.json()
        assert "receipt_no" in str(rj)
        assert "_id" not in (rj.get("payment") or rj)

    def test_renew(self, demo, demo_ctx):
        mid = TestMembers.member_id
        plans = demo_ctx["plans"]
        plans = plans["items"] if isinstance(plans, dict) else plans
        plan = [p for p in plans if p.get("type", "membership") == "membership"][0]
        before = date.fromisoformat(demo.get(f"{API}/members/{mid}").json()["member"]["membership_expiry"][:10])
        r = demo.post(f"{API}/members/{mid}/renew",
                      json={"plan_id": plan["id"], "amount_paid": 1000, "payment_method": "Card"})
        assert r.status_code == 200, r.text
        after = date.fromisoformat(demo.get(f"{API}/members/{mid}").json()["member"]["membership_expiry"][:10])
        assert after > before, "renew did not extend expiry"

    def test_transaction_history(self, demo):
        mid = TestMembers.member_id
        pays = demo.get(f"{API}/members/{mid}").json()["payments"]
        assert len(pays) >= 3, f"expected initial+500+renew payments, got {len(pays)}"

    def test_attendance_history_for_member(self, demo):
        mid = TestMembers.member_id
        r = demo.post(f"{API}/attendance/check-in", json={"member_id": mid})
        assert r.status_code in (200, 201), r.text
        att = demo.get(f"{API}/members/{mid}").json()["attendance"]
        assert len(att) >= 1

    def test_duplicate_checkin_blocked(self, demo):
        mid = TestMembers.member_id
        r = demo.post(f"{API}/attendance/check-in", json={"member_id": mid})
        assert r.status_code in (400, 409), f"duplicate check-in allowed: {r.status_code}"
        assert "already" in r.text.lower() or "checked" in r.text.lower()

    def test_checkout(self, demo):
        mid = TestMembers.member_id
        today_list = demo.get(f"{API}/attendance").json()
        rows = today_list["items"] if isinstance(today_list, dict) else today_list
        row = next((a for a in rows if a["member_id"] == mid), None)
        assert row, "member not in today's attendance list"
        r = demo.post(f"{API}/attendance/{row['id']}/check-out")
        assert r.status_code == 200, r.text
        rows = demo.get(f"{API}/attendance").json()
        rows = rows["items"] if isinstance(rows, dict) else rows
        row = next((a for a in rows if a["member_id"] == mid), None)
        assert row.get("check_out"), "check_out not persisted"

    def test_attendance_history_endpoint(self, demo):
        r = demo.get(f"{API}/attendance/history?month={TODAY.month}&year={TODAY.year}")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (dict, list))

    def test_delete_member(self, demo):
        mid = TestMembers.member_id
        r = demo.delete(f"{API}/members/{mid}")
        assert r.status_code in (200, 204), r.text
        assert demo.get(f"{API}/members/{mid}").status_code == 404
        items = demo.get(f"{API}/members?limit=200").json()["items"]
        assert mid not in [i["id"] for i in items]


# ================= Payments =================

class TestPayments:
    def test_list_seeded(self, demo):
        r = demo.get(f"{API}/payments")
        assert r.status_code == 200
        d = r.json()
        items = d["items"] if isinstance(d, dict) else d
        assert len(items) > 0, "no seeded payments"
        assert "_id" not in items[0]

    def test_method_filter(self, demo):
        d = demo.get(f"{API}/payments?method=Cash").json()
        items = d["items"] if isinstance(d, dict) else d
        assert all(i["method"] == "Cash" for i in items), "method filter not applied"


# ================= Enquiries =================

class TestEnquiries:
    eid = None

    def test_create_and_list(self, demo):
        name = uid("TEST_Enq")
        r = demo.post(f"{API}/enquiries", json={"name": name, "phone": uphone(), "source": "Walk-In",
                                                "status": "New", "category": "Membership"})
        assert r.status_code in (200, 201), r.text
        TestEnquiries.eid = r.json().get("id")
        assert TestEnquiries.eid
        d = demo.get(f"{API}/enquiries?search={name}").json()
        items = d["items"] if isinstance(d, dict) else d
        assert [i for i in items if i["id"] == TestEnquiries.eid]

    def test_follow_up(self, demo):
        r = demo.post(f"{API}/enquiries/{TestEnquiries.eid}/follow-ups",
                      json={"date": TODAY.isoformat(), "note": "TEST called"})
        assert r.status_code in (200, 201), r.text
        d = demo.get(f"{API}/enquiries").json()
        items = d["items"] if isinstance(d, dict) else d
        enq = [i for i in items if i["id"] == TestEnquiries.eid][0]
        assert enq.get("follow_ups") and enq["follow_ups"][-1]["note"] == "TEST called"

    def test_convert_to_member(self, demo, demo_ctx):
        plans = demo_ctx["plans"]
        plans = plans["items"] if isinstance(plans, dict) else plans
        plan = [p for p in plans if p.get("type", "membership") == "membership"][0]
        r = demo.post(f"{API}/members?enquiry_id={TestEnquiries.eid}",
                      json={"full_name": uid("TEST_Conv"), "phone": uphone(), "plan_id": plan["id"],
                            "amount_paid": 100, "payment_method": "Cash"})
        assert r.status_code in (200, 201), r.text
        mid = r.json().get("id")
        d = demo.get(f"{API}/enquiries").json()
        items = d["items"] if isinstance(d, dict) else d
        enq = [i for i in items if i["id"] == TestEnquiries.eid][0]
        assert enq["status"].lower() == "converted", f"enquiry status={enq['status']}"
        demo.delete(f"{API}/members/{mid}")


# ================= Expenses =================

class TestExpenses:
    def test_crud(self, demo):
        name = uid("TEST_Exp")
        r = demo.post(f"{API}/expenses", json={"name": name, "category": "Utilities",
                                               "date": TODAY.isoformat(), "amount": 750, "method": "Cash"})
        assert r.status_code in (200, 201), r.text
        eid = r.json().get("id")
        d = demo.get(f"{API}/expenses?month={TODAY.month}&year={TODAY.year}").json()
        items = d["items"] if isinstance(d, dict) else d
        got = [i for i in items if i["id"] == eid]
        assert got and got[0]["amount"] == 750

        r = demo.put(f"{API}/expenses/{eid}", json={"name": name, "category": "Utilities",
                                                    "date": TODAY.isoformat(), "amount": 900, "method": "UPI"})
        assert r.status_code == 200, r.text
        d = demo.get(f"{API}/expenses?category=Utilities").json()
        items = d["items"] if isinstance(d, dict) else d
        assert [i for i in items if i["id"] == eid][0]["amount"] == 900

        assert demo.delete(f"{API}/expenses/{eid}").status_code in (200, 204)
        d = demo.get(f"{API}/expenses").json()
        items = d["items"] if isinstance(d, dict) else d
        assert not [i for i in items if i["id"] == eid]

    def test_validation(self, demo):
        r = demo.post(f"{API}/expenses", json={"name": "TEST_x", "date": TODAY.isoformat(), "amount": 0})
        assert r.status_code == 422


# ================= Outlets =================

class TestOutlets:
    def test_crud_and_toggle(self, demo):
        name = uid("TEST_Outlet")
        r = demo.post(f"{API}/outlets", json={"name": name, "city": "Bengaluru"})
        assert r.status_code in (200, 201), r.text
        oid = r.json().get("id")
        lst = demo.get(f"{API}/outlets").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        assert [o for o in lst if o["id"] == oid]

        r = demo.put(f"{API}/outlets/{oid}", json={"name": name + "_upd", "city": "Mysuru"})
        assert r.status_code == 200, r.text
        lst = demo.get(f"{API}/outlets").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        assert [o for o in lst if o["id"] == oid][0]["name"] == name + "_upd"

        r = demo.post(f"{API}/outlets/{oid}/toggle")
        assert r.status_code == 200, r.text
        lst = demo.get(f"{API}/outlets").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        o = [o for o in lst if o["id"] == oid][0]
        assert o.get("status") == "disabled" or o.get("disabled") is True, f"toggle no-op: {o}"
        demo.post(f"{API}/outlets/{oid}/toggle")

    def test_primary_outlet_cannot_be_disabled(self, demo):
        lst = demo.get(f"{API}/outlets").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        primary = next((o for o in lst if o.get("is_primary") or o.get("primary")), None)
        if not primary:
            pytest.skip("no is_primary flag on outlets")
        r = demo.post(f"{API}/outlets/{primary['id']}/toggle")
        # business-rule conflict -> 409 (fixed in iteration 4); 400 also acceptable
        assert r.status_code in (400, 409), f"primary outlet disable allowed: {r.status_code}"
        assert r.status_code == 409, f"expected 409 conflict semantics, got {r.status_code}"


# ================= Staff + login account =================

class TestStaff:
    def test_crud_login_and_disable(self, demo):
        email = f"test_staff_{uuid.uuid4().hex[:8]}@testgym.in"
        pwd = "StaffQA@2026"
        r = demo.post(f"{API}/staff", json={"name": uid("TEST_Staff"), "role": "manager", "phone": uphone(),
                                            "email": email, "password": pwd, "salary": 20000})
        assert r.status_code in (200, 201), r.text
        sid = r.json().get("id")
        lst = demo.get(f"{API}/staff").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        assert [s for s in lst if s["id"] == sid]

        # staff login works
        s2 = requests.Session()
        lr = s2.post(f"{API}/auth/login", json={"identifier": email, "password": pwd})
        assert lr.status_code == 200, f"staff login failed: {lr.status_code} {lr.text[:200]}"
        assert s2.get(f"{API}/auth/me").status_code == 200

        # disable blocks login
        tr = demo.post(f"{API}/staff/{sid}/toggle")
        assert tr.status_code == 200, tr.text
        s3 = requests.Session()
        lr = s3.post(f"{API}/auth/login", json={"identifier": email, "password": pwd})
        assert lr.status_code in (401, 403), f"disabled staff could log in: {lr.status_code}"
        # existing session should also be rejected
        assert s2.get(f"{API}/auth/me").status_code in (401, 403), "disabled staff session still valid"
        s2.close(); s3.close()

        # update
        r = demo.put(f"{API}/staff/{sid}", json={"name": "TEST_Staff_Upd", "role": "trainer", "phone": uphone()})
        assert r.status_code == 200, r.text
        lst = demo.get(f"{API}/staff").json()
        lst = lst["items"] if isinstance(lst, dict) else lst
        assert [s for s in lst if s["id"] == sid][0]["role"].lower() == "trainer"

    def test_invalid_role(self, demo):
        r = demo.post(f"{API}/staff", json={"name": "TEST_bad", "role": "ceo", "phone": uphone()})
        assert r.status_code in (400, 422)


# ================= Announcements =================

class TestAnnouncements:
    aid = None

    def test_audience_count(self, demo):
        r = demo.post(f"{API}/announcements/audience-count", json={"audience": "all_active"})
        assert r.status_code == 200, r.text
        assert r.json()["count"] > 0
        assert demo.post(f"{API}/announcements/audience-count", json={"audience": "bogus"}).status_code == 422

    def test_send_now_is_honest(self, demo):
        r = demo.post(f"{API}/announcements", json={"title": uid("TEST_Ann"),
                                                    "message": "Hello {name}, gym closed today.",
                                                    "audience": "all_active"})
        assert r.status_code in (200, 201), r.text
        d = r.json()["announcement"]
        assert r.json()["integration_configured"] is False
        TestAnnouncements.aid = d.get("id")
        status = str(d.get("status", "")).lower()
        assert "integration" in status or status in ("integration_required",), f"status={status} (should be honest)"

        det = demo.get(f"{API}/announcements/{TestAnnouncements.aid}")
        assert det.status_code == 200
        dj = det.json()
        recips = dj.get("recipients") or dj.get("announcement", {}).get("recipients")
        assert recips and len(recips) > 0
        assert all(r_.get("phone") for r_ in recips)

    def test_scheduled(self, demo):
        future = "2026-12-31T10:00:00"
        r = demo.post(f"{API}/announcements", json={"title": uid("TEST_Sched"), "message": "Later msg",
                                                    "audience": "all_active", "scheduled_at": future})
        assert r.status_code in (200, 201), r.text
        a = r.json()["announcement"]
        assert str(a.get("status", "")).lower() == "scheduled", a.get("status")
        sid = a.get("id")
        c = demo.delete(f"{API}/announcements/{sid}")
        assert c.status_code in (200, 204), c.text
        lst = demo.get(f"{API}/announcements").json()
        items = lst["items"] if isinstance(lst, dict) else lst
        row = [a for a in items if a["id"] == sid]
        assert not row or str(row[0]["status"]).lower() == "cancelled"

    def test_history_list(self, demo):
        lst = demo.get(f"{API}/announcements").json()
        items = lst["items"] if isinstance(lst, dict) else lst
        assert [a for a in items if a["id"] == TestAnnouncements.aid]

    def test_cleanup(self, demo):
        if TestAnnouncements.aid:
            demo.delete(f"{API}/announcements/{TestAnnouncements.aid}")


# ================= Finance & Reports =================

class TestFinance:
    @pytest.mark.parametrize("rng", ["today", "week", "month", "year"])
    def test_summary_ranges(self, demo, rng):
        r = demo.get(f"{API}/finance/summary?range={rng}")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("revenue", "expenses", "net", "outstanding"):
            assert k in d, f"missing {k} in {list(d.keys())}"
            assert isinstance(d[k], (int, float))
        assert abs(d["net"] - (d["revenue"] - d["expenses"])) < 0.01
        assert "by_method" in d and "expense_by_category" in d

    def test_transactions(self, demo):
        r = demo.get(f"{API}/finance/transactions?range=year")
        assert r.status_code == 200
        d = r.json()
        items = d["items"] if isinstance(d, dict) else d
        assert isinstance(items, list)
        assert all("_id" not in i for i in items[:5])

    def test_outlet_filter(self, demo, demo_ctx):
        outlets = demo_ctx["outlets"]
        outlets = outlets["items"] if isinstance(outlets, dict) else outlets
        r = demo.get(f"{API}/finance/summary?range=year&outlet_id={outlets[0]['id']}")
        assert r.status_code == 200

    def test_custom_range(self, demo):
        r = demo.get(f"{API}/finance/summary?range=custom&date_from={(TODAY - timedelta(days=30)).isoformat()}&date_to={TODAY.isoformat()}")
        assert r.status_code == 200, r.text


class TestReports:
    def test_revenue_trend(self, demo):
        r = demo.get(f"{API}/reports/revenue-trend?months=6")
        assert r.status_code == 200
        pts = r.json()["points"]
        assert len(pts) == 6 and "month" in pts[0]

    def test_member_growth(self, demo):
        r = demo.get(f"{API}/reports/member-growth?months=6")
        assert r.status_code == 200
        pts = r.json()["points"]
        assert len(pts) == 6
        assert all("joined" in p and "total" in p for p in pts)

    def test_outstanding_dues(self, demo):
        r = demo.get(f"{API}/reports/outstanding-dues")
        assert r.status_code == 200
        d = r.json()
        items = d["items"] if isinstance(d, dict) else d
        assert isinstance(items, list)

    def test_membership_expiry(self, demo):
        r = demo.get(f"{API}/reports/membership-expiry?days=30")
        assert r.status_code == 200

    def test_enquiry_conversion(self, demo):
        r = demo.get(f"{API}/reports/enquiry-conversion")
        assert r.status_code == 200
        d = r.json()
        assert any("conver" in k.lower() or "total" in k.lower() for k in d.keys()), d.keys()


# ================= Export center =================

class TestExport:
    @pytest.mark.parametrize("ds", ["members", "payments", "attendance", "expenses", "enquiries", "staff", "plans"])
    def test_csv(self, demo, ds):
        r = demo.get(f"{API}/export/{ds}")
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert len(r.text.strip().splitlines()) >= 1

    def test_members_csv_rows(self, demo):
        r = demo.get(f"{API}/export/members")
        lines = r.text.strip().splitlines()
        assert len(lines) >= 27, f"expected header + 26 members, got {len(lines)}"
        assert "full_name" in lines[0]

    def test_unknown_dataset(self, demo):
        assert demo.get(f"{API}/export/bogus").status_code == 404


# ================= Subscription / billing =================

class TestSubscription:
    def test_get_subscription(self, demo):
        r = demo.get(f"{API}/subscription")
        assert r.status_code == 200
        d = r.json()
        assert d["subscription"]["plan_price_inr"] == 999
        assert d["razorpay_configured"] is False
        assert isinstance(d["payments"], list)

    def test_create_order_honest_503(self, demo):
        r = demo.post(f"{API}/subscription/create-order")
        assert r.status_code == 503, f"expected honest 503, got {r.status_code}"
        assert "configur" in r.text.lower()

    def test_verify_rejects(self, demo):
        r = demo.post(f"{API}/subscription/verify", json={"razorpay_order_id": "order_x",
                                                          "razorpay_payment_id": "pay_x",
                                                          "razorpay_signature": "sig_x"})
        assert r.status_code >= 400, f"fake signature accepted: {r.status_code}"


# ================= Support / profile =================

class TestMisc:
    def test_support_request(self, demo):
        r = demo.post(f"{API}/support/requests", json={"subject": "TEST_subject", "message": "TEST message body"})
        assert r.status_code in (200, 201), r.text

    def test_gym_profile_and_user_profile(self, demo, demo_ctx):
        org = demo_ctx["me"].get("organisation") or {}
        orig_name = org.get("name", "Iron Paradise Fitness")
        orig_city = org.get("city", "Bengaluru")
        r = demo.put(f"{API}/gym/profile", json={"name": orig_name, "city": orig_city})
        assert r.status_code == 200, r.text
        u = demo_ctx["me"].get("user") or demo_ctx["me"]
        r = demo.put(f"{API}/profile", json={"full_name": u.get("full_name") or "Demo Owner"})
        assert r.status_code == 200, r.text


# ================= Super admin =================

class TestSuperAdmin:
    def test_overview(self, admin):
        r = admin.get(f"{API}/admin/overview")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("total_gyms", "trial", "paying", "expired", "mrr"):
            assert k in d, f"missing {k}: {list(d.keys())}"
        assert d["total_gyms"] >= 1

    def test_gyms_list_and_detail(self, admin):
        r = admin.get(f"{API}/admin/gyms")
        assert r.status_code == 200
        d = r.json()
        items = d["items"] if isinstance(d, dict) else d
        assert len(items) >= 1
        assert "_id" not in items[0]
        gid = items[0]["id"]
        det = admin.get(f"{API}/admin/gyms/{gid}")
        assert det.status_code == 200, det.text
        assert "_id" not in det.json()

    def test_disable_reactivate_demo_gym(self, admin, demo_ctx):
        org = demo_ctx["me"].get("organisation") or {}
        gid = org.get("id")
        assert gid, f"could not resolve demo org id from /auth/me: {demo_ctx['me']}"
        try:
            r = admin.post(f"{API}/admin/gyms/{gid}/toggle")
            assert r.status_code == 200, r.text
            s = requests.Session()
            lr = s.post(f"{API}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
            blocked = lr.status_code in (401, 403) or s.get(f"{API}/members").status_code == 403
            s.close()
            assert blocked, "demo owner not blocked while gym disabled"
        finally:
            admin.post(f"{API}/admin/gyms/{gid}/toggle")
        s = requests.Session()
        lr = s.post(f"{API}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
        assert lr.status_code == 200, "demo login broken after reactivation"
        assert s.get(f"{API}/members").status_code == 200
        s.close()

    def test_platform_settings(self, admin):
        cur = admin.get(f"{API}/admin/settings")
        assert cur.status_code == 200
        base = cur.json()
        base = base.get("settings", base)
        payload = {k: base.get(k) for k in base if k not in ("_id",)}
        payload["whatsapp_number"] = "919876543210"
        r = admin.put(f"{API}/admin/settings", json=payload)
        assert r.status_code == 200, r.text
        again = admin.get(f"{API}/admin/settings").json()
        again = again.get("settings", again)
        assert again["whatsapp_number"] == "919876543210"

    def test_audit_logs(self, admin):
        r = admin.get(f"{API}/admin/audit-logs?limit=50")
        assert r.status_code == 200
        d = r.json()
        items = d["items"] if isinstance(d, dict) else d
        assert len(items) > 0
        assert "action" in items[0]
        assert "_id" not in items[0]

    def test_org_routes_forbidden_for_super_admin(self, admin):
        assert admin.get(f"{API}/members").status_code == 403

    def test_admin_routes_forbidden_for_org_user(self, demo):
        for ep in ("/admin/overview", "/admin/gyms", "/admin/settings", "/admin/audit-logs"):
            assert demo.get(f"{API}{ep}").status_code == 403, f"{ep} not protected"


# ================= Tenant isolation =================

class TestTenantIsolation:
    def test_fresh_org_is_empty_and_isolated(self, demo):
        demo_member_id = demo.get(f"{API}/members?limit=1").json()["items"][0]["id"]
        email = f"test_iso_{uuid.uuid4().hex[:8]}@testgym.in"
        fresh = requests.Session()
        fresh.headers.update({"Content-Type": "application/json"})
        r = fresh.post(f"{API}/auth/register", json={
            "full_name": "TEST Iso Owner", "email": email, "phone": uphone(),
            "password": "IsoQA@2026", "gym_name": "TEST Iso Gym", "outlet_name": "Main", "city": "Pune"})
        assert r.status_code in (200, 201), r.text

        assert fresh.get(f"{API}/members").json()["total"] == 0
        for ep in ("/payments", "/enquiries", "/expenses", "/staff", "/announcements"):
            d = fresh.get(f"{API}{ep}").json()
            items = d["items"] if isinstance(d, dict) else d
            assert items == [] or len(items) == 0, f"{ep} leaked data: {str(items)[:200]}"

        assert fresh.get(f"{API}/members/{demo_member_id}").status_code == 404, "cross-tenant member read allowed"
        assert fresh.delete(f"{API}/members/{demo_member_id}").status_code == 404, "cross-tenant member delete allowed"
        assert fresh.put(f"{API}/members/{demo_member_id}", json={"batch": "hack"}).status_code == 404

        csv_txt = fresh.get(f"{API}/export/members").text
        assert "Aarav" not in csv_txt, "export leaked other tenant data"
        fresh.close()
        TestTenantIsolation.iso_email = email

    def test_cleanup_iso_org(self):
        email = getattr(TestTenantIsolation, "iso_email", None)
        if not email:
            pytest.skip("nothing to clean")
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import dotenv_values as dv
        be = dv("/app/backend/.env")

        async def _clean():
            c = AsyncIOMotorClient(be["MONGO_URL"])
            db = c[be["DB_NAME"]]
            u = await db.users.find_one({"email": email})
            if u:
                oid = u.get("organisation_id")
                for coll in ("users", "organisations", "outlets", "plans", "members", "payments",
                             "enquiries", "expenses", "staff", "announcements", "subscriptions",
                             "subscription_payments", "audit_logs", "attendance"):
                    if coll == "organisations":
                        await db[coll].delete_many({"id": oid})
                    else:
                        await db[coll].delete_many({"organisation_id": oid})
                await db.users.delete_many({"email": email})
            c.close()

        asyncio.run(_clean())
