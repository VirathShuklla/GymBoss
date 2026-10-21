"""Iteration 6 change-set tests: 3-step member payload, batches, next-code,
member filters, simplified outlet, staff permission/finance enforcement,
plan category, dynamic plan price + razorpay settings, uploads."""
import io
import uuid

import pytest
import requests

from conftest import API, unique_email, unique_phone


def _login(identifier, password):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"identifier": identifier, "password": password})
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:300]}"
    return s


@pytest.fixture(scope="module")
def demo():
    import re
    from pathlib import Path
    content = Path("/app/memory/test_credentials.md").read_text()
    emails = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    passwords = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    usernames = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Username(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    s = _login(emails[0], passwords[1])
    yield s
    s.close()


@pytest.fixture(scope="module")
def superadmin():
    import re
    from pathlib import Path
    content = Path("/app/memory/test_credentials.md").read_text()
    usernames = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Username(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    passwords = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    s = _login(usernames[0], passwords[0])
    yield s
    s.close()


@pytest.fixture(scope="module")
def membership_plan(demo):
    r = demo.get(f"{API}/plans", params={"type": "membership"})
    assert r.status_code == 200
    plans = r.json()
    assert plans, "no membership plans in demo org"
    return plans[0]


@pytest.fixture(scope="module")
def created():
    ids = {"members": [], "staff": [], "outlets": [], "plans": []}
    yield ids


# ---------------- Member creation / payable maths ----------------

class TestMemberPayable:
    def _payload(self, plan, **over):
        p = {
            "full_name": "TEST_QA Member",
            "phone": unique_phone(),
            "plan_id": plan["id"],
            "gender": "Male",
            "batch": "TEST_QA Batch",
            "joining_date": "2026-07-01",
            "membership_start": "2026-07-01",
            "payment_date": "2026-07-01",
            "admission_amount": 500,
            "discount": 100,
            "amount_paid": 0,
            "payment_method": "Cash",
        }
        p.update(over)
        return p

    def test_next_code_does_not_consume(self, demo):
        a = demo.get(f"{API}/members/next-code")
        b = demo.get(f"{API}/members/next-code")
        assert a.status_code == 200 and b.status_code == 200
        assert a.json()["member_code"] == b.json()["member_code"]
        assert a.json()["member_code"].startswith("IPF-")

    def test_create_full_paid(self, demo, membership_plan, created):
        price = membership_plan["price"]
        payable = price + 500 - 100
        body = self._payload(membership_plan, amount_paid=payable)
        pre = demo.get(f"{API}/members/next-code").json()["member_code"]
        r = demo.post(f"{API}/members", json=body)
        assert r.status_code == 200, r.text[:400]
        m = r.json()
        created["members"].append(m["id"])
        assert m["member_code"] == pre, "next-code preview must match assigned code"
        assert m["payable"] == payable
        assert m["due_amount"] == 0
        assert m["payment_status"] == "Paid"
        assert m["phone"].startswith("+91")
        assert m["membership_start"] == "2026-07-01"
        assert m["membership_expiry"] > m["membership_start"]
        # persistence
        g = demo.get(f"{API}/members/{m['id']}")
        assert g.status_code == 200
        gm = g.json()["member"] if "member" in g.json() else g.json()
        assert gm["payment_status"] == "Paid"
        assert gm["admission_amount"] == 500 and gm["discount"] == 100

    def test_create_partial(self, demo, membership_plan, created):
        payable = membership_plan["price"] + 500 - 100
        r = demo.post(f"{API}/members", json=self._payload(membership_plan, amount_paid=200))
        assert r.status_code == 200, r.text[:300]
        m = r.json()
        created["members"].append(m["id"])
        assert m["payable"] == payable
        assert m["due_amount"] == payable - 200
        assert m["payment_status"] == "Partially Paid"

    def test_create_due(self, demo, membership_plan, created):
        r = demo.post(f"{API}/members", json=self._payload(membership_plan, amount_paid=0))
        assert r.status_code == 200, r.text[:300]
        m = r.json()
        created["members"].append(m["id"])
        assert m["payment_status"] == "Due"
        assert m["due_amount"] == m["payable"]

    def test_batch_auto_created(self, demo):
        r = demo.get(f"{API}/batches")
        assert r.status_code == 200
        names = [b["name"] for b in r.json()]
        assert "TEST_QA Batch" in names
        # iteration 7: demo org batches deduplicated -> exactly 3 canonical batches
        canonical = [n for n in names if n != "TEST_QA Batch"]
        assert sorted(canonical) == ["Afternoon (12–2 PM)", "Evening (5–8 PM)", "Morning (6–8 AM)"], canonical

    def test_optional_step2_fields_persist(self, demo, membership_plan, created):
        body = self._payload(
            membership_plan,
            email=unique_email("test_qa_member"),
            height="180", weight="75", address="TEST addr",
            notes="TEST note", dob="1995-05-05", amount_paid=100,
        )
        r = demo.post(f"{API}/members", json=body)
        assert r.status_code == 200, r.text[:300]
        m = r.json()
        created["members"].append(m["id"])
        g = demo.get(f"{API}/members/{m['id']}").json()
        gm = g.get("member", g)
        assert gm["height"] == "180" and gm["weight"] == "75"
        assert gm["notes"] == "TEST note" and gm["dob"] == "1995-05-05"

    def test_payment_row_created(self, demo, membership_plan, created):
        r = demo.post(f"{API}/members", json=self._payload(membership_plan, amount_paid=300))
        m = r.json()
        created["members"].append(m["id"])
        pays = demo.get(f"{API}/payments", params={"search": m["full_name"], "limit": 50})
        assert pays.status_code == 200
        rows = pays.json()["items"]
        mine = [p for p in rows if p.get("member_id") == m["id"]]
        assert mine, "no payment row created for amount_paid=300"
        assert mine[0]["amount"] == 300
        assert mine[0]["receipt_no"].startswith("RCPT-")


# ---------------- Filters ----------------

class TestMemberFilters:
    def test_gender_filter(self, demo):
        r = demo.get(f"{API}/members", params={"gender": "Male", "limit": 50})
        assert r.status_code == 200
        data = r.json()
        items = data.get("members", data.get("items", data))
        assert all(m.get("gender") == "Male" for m in items)

    def test_batch_filter(self, demo):
        r = demo.get(f"{API}/members", params={"batch": "TEST_QA Batch", "limit": 50})
        assert r.status_code == 200
        data = r.json()
        items = data.get("members", data.get("items", data))
        assert items, "batch filter returned nothing"
        assert all(m.get("batch") == "TEST_QA Batch" for m in items)

    def test_search_field_scoping(self, demo):
        code = demo.get(f"{API}/members", params={"limit": 1}).json()
        items = code.get("members", code.get("items", code))
        target = items[0]
        r = demo.get(f"{API}/members", params={"search": target["member_code"], "search_field": "code"})
        got = r.json()
        got_items = got.get("members", got.get("items", got))
        assert any(m["id"] == target["id"] for m in got_items)
        # name search must not match a member code
        r2 = demo.get(f"{API}/members", params={"search": target["member_code"], "search_field": "name"})
        it2 = r2.json()
        it2 = it2.get("members", it2.get("items", it2))
        assert not any(m["id"] == target["id"] for m in it2), "search_field=name matched member_code"


# ---------------- Outlets (simplified) ----------------

class TestOutlets:
    def test_create_outlet_name_address_only(self, demo, created):
        name = f"TEST_QA Outlet {uuid.uuid4().hex[:5]}"
        r = demo.post(f"{API}/outlets", json={"name": name, "address": "TEST 12 Main Rd"})
        assert r.status_code in (200, 201), r.text[:300]
        o = r.json()
        created["outlets"].append(o["id"])
        assert o["name"] == name and o["address"] == "TEST 12 Main Rd"
        lst = demo.get(f"{API}/outlets").json()
        lst = lst.get("outlets", lst) if isinstance(lst, dict) else lst
        assert any(x["id"] == o["id"] for x in lst)


# ---------------- Staff permissions & finance guard ----------------

class TestStaffPermissions:
    @pytest.fixture(scope="class")
    def view_staff(self, demo, created):
        email = unique_email("test_qa_view")
        body = {
            "name": "TEST_QA ViewStaff", "role": "staff", "email": email,
            "phone": unique_phone(), "password": "ViewStaff@2026",
            "permission": "view", "enable_finance": False,
        }
        r = demo.post(f"{API}/staff", json=body)
        assert r.status_code in (200, 201), r.text[:400]
        s = r.json()
        created["staff"].append(s["id"])
        return {"staff": s, "email": email, "password": "ViewStaff@2026"}

    def test_staff_created_with_permission_fields(self, view_staff):
        s = view_staff["staff"]
        assert s["permission"] == "view"
        assert s.get("enable_finance") is False

    def test_view_staff_can_read_members(self, view_staff):
        c = _login(view_staff["email"], view_staff["password"])
        r = c.get(f"{API}/members", params={"limit": 5})
        assert r.status_code == 200, r.text[:300]
        c.close()

    def test_view_staff_cannot_create_member(self, view_staff, membership_plan):
        c = _login(view_staff["email"], view_staff["password"])
        r = c.post(f"{API}/members", json={
            "full_name": "TEST_QA Blocked", "phone": unique_phone(), "plan_id": membership_plan["id"],
        })
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
        c.close()

    def test_view_staff_cannot_mutate_plan_expense_enquiry_payment(self, view_staff, membership_plan):
        c = _login(view_staff["email"], view_staff["password"])
        checks = [
            ("POST", f"{API}/plans", {"name": "TEST_QA Plan", "type": "membership", "price": 100}),
            ("POST", f"{API}/expenses", {"category": "Misc", "amount": 10, "expense_date": "2026-07-01"}),
            ("POST", f"{API}/enquiries", {"name": "TEST_QA Enq", "phone": unique_phone()}),
        ]
        for method, url, payload in checks:
            r = c.request(method, url, json=payload)
            assert r.status_code == 403, f"{url} expected 403 got {r.status_code}: {r.text[:200]}"
        c.close()

    def test_view_staff_no_finance_access(self, view_staff):
        c = _login(view_staff["email"], view_staff["password"])
        r = c.get(f"{API}/finance/summary")
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:200]}"
        me = c.get(f"{API}/auth/me").json()
        user = me.get("user", me)
        assert user.get("permission") == "view"
        assert user.get("finance_enabled") is False
        c.close()

    def test_enable_finance_grants_access(self, demo, view_staff):
        sid = view_staff["staff"]["id"]
        body = {
            "name": view_staff["staff"]["name"], "role": "staff",
            "email": view_staff["email"], "phone": view_staff["staff"]["phone"].replace("+91", ""),
            "permission": "view", "enable_finance": True,
        }
        r = demo.put(f"{API}/staff/{sid}", json=body)
        assert r.status_code == 200, r.text[:300]
        c = _login(view_staff["email"], view_staff["password"])
        fr = c.get(f"{API}/finance/summary")
        assert fr.status_code == 200, f"finance still blocked after enable: {fr.status_code} {fr.text[:200]}"
        # still view-only for writes
        wr = c.post(f"{API}/enquiries", json={"name": "TEST_QA Enq2", "phone": unique_phone()})
        assert wr.status_code == 403
        c.close()

    def test_invalid_permission_rejected(self, demo):
        r = demo.post(f"{API}/staff", json={
            "name": "TEST_QA Bad", "role": "staff", "phone": unique_phone(), "permission": "godmode",
        })
        assert r.status_code == 422, f"expected 422 got {r.status_code}"


# ---------------- Plan category ----------------

class TestPlanCategory:
    @pytest.mark.parametrize("ptype", ["membership", "pt", "service", "product"])
    def test_plan_type_tabs(self, demo, created, ptype):
        body = {"name": f"TEST_QA {ptype}", "type": ptype, "price": 1200}
        if ptype == "pt":
            body.update({"duration_type": "months", "duration": 2, "sessions": 12, "trainer": "TEST Trainer"})
        if ptype == "product":
            body.update({"inventory": 7})
        r = demo.post(f"{API}/plans", json=body)
        assert r.status_code in (200, 201), r.text[:300]
        p = r.json()
        created["plans"].append(p["id"])
        assert p["type"] == ptype
        lst = demo.get(f"{API}/plans", params={"type": ptype}).json()
        assert any(x["id"] == p["id"] for x in lst), f"plan not listed under {ptype} tab"
        if ptype == "product":
            assert next(x for x in lst if x["id"] == p["id"])["inventory"] == 7
        if ptype == "pt":
            row = next(x for x in lst if x["id"] == p["id"])
            assert row["sessions"] == 12 and row["trainer"] == "TEST Trainer"

    def test_invalid_type_rejected(self, demo):
        r = demo.post(f"{API}/plans", json={"name": "TEST_QA bad", "type": "nonsense", "price": 10})
        assert r.status_code == 422


# ---------------- Platform settings: dynamic price + razorpay ----------------

class TestPlatformSettings:
    def test_price_propagation_and_restore(self, superadmin, demo):
        orig = superadmin.get(f"{API}/admin/settings")
        assert orig.status_code == 200
        orig_price = orig.json().get("plan_price_inr") or 999
        try:
            r = superadmin.put(f"{API}/admin/settings", json={"plan_price_inr": 500})
            assert r.status_code == 200, r.text[:300]
            assert r.json()["plan_price_inr"] == 500
            pub = requests.get(f"{API}/public/config")
            assert pub.status_code == 200
            assert pub.json()["plan_price_inr"] == 500, pub.text[:200]
            sub = demo.get(f"{API}/subscription")
            assert sub.status_code == 200
            body = sub.json()
            price = body.get("plan_price_inr") or body.get("subscription", {}).get("plan_price_inr")
            assert price == 500, body
            ov = superadmin.get(f"{API}/admin/overview")
            assert ov.status_code == 200
            o = ov.json()
            paying = o.get("paying_gyms") or o.get("kpis", {}).get("paying_gyms")
            mrr = o.get("mrr") or o.get("kpis", {}).get("mrr")
            if paying is not None and mrr is not None:
                assert mrr == paying * 500, f"mrr {mrr} != {paying}*500"
        finally:
            back = superadmin.put(f"{API}/admin/settings", json={"plan_price_inr": int(orig_price)})
            assert back.status_code == 200
            assert requests.get(f"{API}/public/config").json()["plan_price_inr"] == int(orig_price)

    def test_invalid_price_rejected(self, superadmin):
        r = superadmin.put(f"{API}/admin/settings", json={"plan_price_inr": 0})
        assert r.status_code in (400, 422), f"expected rejection got {r.status_code}"
        assert requests.get(f"{API}/public/config").json()["plan_price_inr"] >= 1

    def test_razorpay_keys_roundtrip(self, superadmin, demo):
        orig = superadmin.get(f"{API}/admin/settings").json()
        try:
            r = superadmin.put(f"{API}/admin/settings", json={
                "razorpay_key_id": "rzp_test_QAKEY123",
                "razorpay_key_secret": "qa_secret",
                "razorpay_webhook_secret": "qa_hook",
                "plan_price_inr": int(orig.get("plan_price_inr") or 999),
            })
            assert r.status_code == 200, r.text[:300]
            s = r.json()
            assert s["razorpay_key_id"] == "rzp_test_QAKEY123"
            sub = demo.get(f"{API}/subscription").json()
            assert sub.get("razorpay_configured") is True, sub
        finally:
            superadmin.put(f"{API}/admin/settings", json={
                "razorpay_key_id": orig.get("razorpay_key_id") or "",
                "razorpay_key_secret": orig.get("razorpay_key_secret") or "",
                "razorpay_webhook_secret": orig.get("razorpay_webhook_secret") or "",
                "plan_price_inr": int(orig.get("plan_price_inr") or 999),
            })

    def test_price_only_update_preserves_other_settings(self, superadmin):
        orig = superadmin.get(f"{API}/admin/settings").json()
        try:
            superadmin.put(f"{API}/admin/settings", json={
                "razorpay_key_id": "rzp_test_PRESERVE",
                "razorpay_key_secret": "qa_secret",
                "plan_price_inr": int(orig.get("plan_price_inr") or 999),
            })
            # price-only update (partial payload) must not wipe stored keys
            superadmin.put(f"{API}/admin/settings", json={"plan_price_inr": 777})
            after = superadmin.get(f"{API}/admin/settings").json()
            assert after["plan_price_inr"] == 777
            assert after.get("razorpay_key_id") == "rzp_test_PRESERVE", \
                "partial settings update wiped razorpay_key_id"
        finally:
            superadmin.put(f"{API}/admin/settings", json={
                "razorpay_key_id": orig.get("razorpay_key_id") or "",
                "razorpay_key_secret": orig.get("razorpay_key_secret") or "",
                "razorpay_webhook_secret": orig.get("razorpay_webhook_secret") or "",
                "support_email": orig.get("support_email") or "",
                "plan_price_inr": int(orig.get("plan_price_inr") or 999),
            })

    def test_settings_require_super_admin(self, demo):
        r = demo.put(f"{API}/admin/settings", json={"plan_price_inr": 1})
        assert r.status_code == 403


# ---------------- Uploads ----------------

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00"
    b"\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestUploads:
    def test_photo_upload_and_fetch(self, demo):
        files = {"file": ("test_qa.png", io.BytesIO(PNG), "image/png")}
        r = demo.post(f"{API}/uploads", data={"kind": "photo"}, files=files,
                      headers={"Content-Type": None})
        assert r.status_code in (200, 201), f"upload failed {r.status_code}: {r.text[:300]}"
        d = r.json()
        assert d["url"].startswith("/api/files/")
        fid = d["id"]
        f = demo.get(f"{API}/files/{fid}")
        assert f.status_code == 200
        assert f.headers.get("Content-Type", "").startswith("image/")

    def test_photo_rejects_pdf(self, demo):
        files = {"file": ("test_qa.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}
        r = demo.post(f"{API}/uploads", data={"kind": "photo"}, files=files,
                      headers={"Content-Type": None})
        assert r.status_code in (400, 415, 422), f"pdf accepted as photo: {r.status_code}"

    def test_attachment_accepts_pdf(self, demo):
        files = {"file": ("test_qa.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}
        r = demo.post(f"{API}/uploads", data={"kind": "attachment"}, files=files,
                      headers={"Content-Type": None})
        assert r.status_code in (200, 201), f"attachment pdf rejected: {r.status_code} {r.text[:200]}"

    def test_files_requires_auth(self, demo):
        files = {"file": ("test_qa.png", io.BytesIO(PNG), "image/png")}
        d = demo.post(f"{API}/uploads", data={"kind": "photo"}, files=files,
                      headers={"Content-Type": None}).json()
        anon = requests.get(f"{API}/files/{d['id']}")
        assert anon.status_code in (401, 403), f"file served without auth: {anon.status_code}"


# ---------------- Announcements removal ----------------

class TestAnnouncementsRemoved:
    def test_announcements_endpoint_state(self, demo):
        r = demo.get(f"{API}/announcements")
        assert r.status_code in (200, 404, 405, 410), r.status_code


# ---------------- Cleanup ----------------

def test_zz_cleanup(demo, created):
    for mid in created["members"]:
        demo.delete(f"{API}/members/{mid}")
    # NOTE: no DELETE /api/staff endpoint exists (only /staff/{id}/toggle) —
    # staff rows created here are purged by tests/cleanup_test_data.py
    for pid in created["plans"]:
        demo.delete(f"{API}/plans/{pid}")
    for oid in created["outlets"]:
        demo.delete(f"{API}/outlets/{oid}")
