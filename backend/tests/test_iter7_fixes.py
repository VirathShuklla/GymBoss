"""Iteration 7 fix verification: admin settings partial save + validation,
require_write permission for manager/admin staff, payable==0 -> Paid,
DELETE /api/staff/{id} cascading to the linked login user."""
import re
from pathlib import Path

import pytest
import requests

from conftest import API, unique_email, unique_phone


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(identifier, password):
    s = _session()
    r = s.post(f"{API}/auth/login", json={"identifier": identifier, "password": password})
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:300]}"
    return s


def _creds():
    content = Path("/app/memory/test_credentials.md").read_text()
    emails = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    passwords = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    usernames = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Username(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    return {"demo": (emails[0], passwords[1]), "super": (usernames[0], passwords[0])}


@pytest.fixture(scope="module")
def demo():
    d = _creds()["demo"]
    s = _login(*d)
    yield s
    s.close()


@pytest.fixture(scope="module")
def superadmin():
    d = _creds()["super"]
    s = _login(*d)
    yield s
    s.close()


# --- admin.py PUT /api/admin/settings -----------------------------------------
class TestPlatformSettingsFixed:
    def test_zero_price_returns_422(self, superadmin):
        r = superadmin.put(f"{API}/admin/settings", json={"plan_price_inr": 0})
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"

    def test_negative_price_returns_422(self, superadmin):
        r = superadmin.put(f"{API}/admin/settings", json={"plan_price_inr": -5})
        assert r.status_code == 422

    def test_partial_save_preserves_other_keys(self, superadmin):
        # seed a razorpay key + support email
        seed = superadmin.put(f"{API}/admin/settings", json={
            "razorpay_key_id": "rzp_test_PRESERVE",
            "support_email": "test_qa_support@testgym.in",
        })
        assert seed.status_code == 200
        assert seed.json()["razorpay_key_id"] == "rzp_test_PRESERVE"

        # price-only save must not clobber them
        r = superadmin.put(f"{API}/admin/settings", json={"plan_price_inr": 777})
        assert r.status_code == 200
        body = r.json()
        assert body["plan_price_inr"] == 777
        assert body["razorpay_key_id"] == "rzp_test_PRESERVE", "razorpay key was clobbered"
        assert body["support_email"] == "test_qa_support@testgym.in"

        # GET verifies persistence
        g = superadmin.get(f"{API}/admin/settings")
        assert g.status_code == 200
        assert g.json()["plan_price_inr"] == 777
        assert g.json()["razorpay_key_id"] == "rzp_test_PRESERVE"

        # public config reflects new price
        pub = requests.get(f"{API}/public/config")
        assert pub.status_code == 200
        assert pub.json()["plan_price_inr"] == 777

        # restore
        rest = superadmin.put(f"{API}/admin/settings", json={
            "plan_price_inr": 999, "razorpay_key_id": "", "razorpay_key_secret": "",
            "razorpay_webhook_secret": "", "whatsapp_number": "",
        })
        assert rest.status_code == 200
        assert rest.json()["plan_price_inr"] == 999
        assert rest.json()["razorpay_key_id"] == ""


# --- deps.require_write + ops DELETE /staff -----------------------------------
class TestStaffPermissionAndDelete:
    @pytest.fixture(scope="class")
    def staff_pair(self, demo):
        """Create a Manager+view staff and a Manager+manage staff."""
        outlets = demo.get(f"{API}/outlets").json()
        outlet_id = outlets[0]["id"]
        made = []
        for label, perm in (("view", "view"), ("manage", "manage")):
            email = unique_email(f"test_qa_mgr_{label}")
            body = {
                "name": f"TEST_QA Mgr {label}", "phone": unique_phone(), "email": email,
                "role": "manager", "outlet_id": outlet_id, "permission": perm,
                "enable_finance": False, "password": "QaStaff@2026",
            }
            r = demo.post(f"{API}/staff", json=body)
            assert r.status_code in (200, 201), f"staff create failed {r.status_code}: {r.text[:300]}"
            made.append({"staff": r.json(), "email": email, "permission": perm})
        yield made
        for m in made:
            demo.delete(f"{API}/staff/{m['staff']['id']}")

    def test_manager_with_view_permission_cannot_write(self, staff_pair):
        v = [m for m in staff_pair if m["permission"] == "view"][0]
        s = _login(v["email"], "QaStaff@2026")
        me = s.get(f"{API}/auth/me").json()["user"]
        assert me["role"] == "manager"
        assert me.get("permission") == "view"
        plans = s.get(f"{API}/plans", params={"type": "membership"}).json()
        r = s.post(f"{API}/members", json={
            "full_name": "TEST_QA Blocked", "phone": unique_phone(), "plan_id": plans[0]["id"],
            "gender": "Male", "joining_date": "2026-07-01", "membership_start": "2026-07-01",
            "payment_date": "2026-07-01", "admission_amount": 0, "discount": 0,
            "amount_paid": 0, "payment_method": "Cash",
        })
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
        assert "view-only" in r.text
        # reads still work
        assert s.get(f"{API}/members").status_code == 200
        s.close()

    def test_manager_with_manage_permission_can_write(self, demo, staff_pair):
        m = [x for x in staff_pair if x["permission"] == "manage"][0]
        s = _login(m["email"], "QaStaff@2026")
        plans = s.get(f"{API}/plans", params={"type": "membership"}).json()
        r = s.post(f"{API}/members", json={
            "full_name": "TEST_QA Allowed", "phone": unique_phone(), "plan_id": plans[0]["id"],
            "gender": "Male", "joining_date": "2026-07-01", "membership_start": "2026-07-01",
            "payment_date": "2026-07-01", "admission_amount": 0, "discount": 0,
            "amount_paid": 0, "payment_method": "Cash",
        })
        assert r.status_code in (200, 201), f"manage staff blocked: {r.status_code} {r.text[:200]}"
        mid = r.json()["id"]
        s.close()
        assert demo.delete(f"{API}/members/{mid}").status_code in (200, 204)

    def test_delete_staff_removes_linked_login_user(self, demo):
        outlet_id = demo.get(f"{API}/outlets").json()[0]["id"]
        email = unique_email("test_qa_deleteme")
        r = demo.post(f"{API}/staff", json={
            "name": "TEST_QA DeleteMe", "phone": unique_phone(), "email": email,
            "role": "staff", "outlet_id": outlet_id, "permission": "manage",
            "enable_finance": False, "password": "QaStaff@2026",
        })
        assert r.status_code in (200, 201)
        staff_id = r.json()["id"]
        # login works before delete
        pre = _login(email, "QaStaff@2026")
        pre.close()

        d = demo.delete(f"{API}/staff/{staff_id}")
        assert d.status_code in (200, 204), f"delete failed {d.status_code}: {d.text[:200]}"

        # staff row gone
        ids = [s["id"] for s in demo.get(f"{API}/staff").json()]
        assert staff_id not in ids
        # second delete -> 404
        assert demo.delete(f"{API}/staff/{staff_id}").status_code == 404
        # linked user login now fails
        s = _session()
        post = s.post(f"{API}/auth/login", json={"identifier": email, "password": "QaStaff@2026"})
        assert post.status_code == 401, f"deleted staff can still log in ({post.status_code})"
        s.close()


# --- members.py payment_status ------------------------------------------------
class TestPayableZeroPaid:
    def test_full_discount_zero_paid_is_paid(self, demo):
        plans = demo.get(f"{API}/plans", params={"type": "membership"}).json()
        plan = plans[0]
        price = plan.get("price") or plan.get("amount") or 0
        assert price > 0
        r = demo.post(f"{API}/members", json={
            "full_name": "TEST_QA ZeroPayable", "phone": unique_phone(), "plan_id": plan["id"],
            "gender": "Female", "joining_date": "2026-07-01", "membership_start": "2026-07-01",
            "payment_date": "2026-07-01", "admission_amount": 500,
            "discount": price + 500, "amount_paid": 0, "payment_method": "Cash",
        })
        assert r.status_code in (200, 201), r.text[:300]
        m = r.json()
        mid = m["id"]
        try:
            assert m["payable"] == 0
            assert m["due_amount"] == 0
            assert m["payment_status"] == "Paid", f"got {m['payment_status']}"
            g = demo.get(f"{API}/members/{mid}")
            assert g.status_code == 200
            fetched = g.json()["member"]
            assert fetched["payment_status"] == "Paid"
            assert fetched["due_amount"] == 0
        finally:
            demo.delete(f"{API}/members/{mid}")

    def test_deleted_member_is_gone(self, demo):
        plans = demo.get(f"{API}/plans", params={"type": "membership"}).json()
        r = demo.post(f"{API}/members", json={
            "full_name": "TEST_QA TempDel", "phone": unique_phone(), "plan_id": plans[0]["id"],
            "gender": "Male", "joining_date": "2026-07-01", "membership_start": "2026-07-01",
            "payment_date": "2026-07-01", "admission_amount": 0, "discount": 0,
            "amount_paid": 0, "payment_method": "Cash",
        })
        mid = r.json()["id"]
        assert demo.delete(f"{API}/members/{mid}").status_code in (200, 204)
        assert demo.get(f"{API}/members/{mid}").status_code == 404


# --- batches dedup ------------------------------------------------------------
def test_demo_batches_deduplicated(demo):
    r = demo.get(f"{API}/batches")
    assert r.status_code == 200
    names = sorted(b["name"] for b in r.json() if not b["name"].startswith("TEST"))
    assert names == ["Afternoon (12–2 PM)", "Evening (5–8 PM)", "Morning (6–8 AM)"], names
