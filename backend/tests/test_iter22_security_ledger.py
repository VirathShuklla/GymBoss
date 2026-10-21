# Iteration 22: security + money audit (billing verify/webhook, subscription restriction, permissions,
# auth hardening, member ledger, dates/freeze, attendance/QR/ADMS). Uses throwaway registered orgs only.
import os
import hmac
import json
import uuid
import hashlib
import concurrent.futures as cf
from datetime import datetime, timedelta, timezone, date

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FE["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"
db = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()
PWD = "TestPass@2026"


def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def uniq():
    return uuid.uuid4().hex[:8]


def rand_phone():
    return "9" + str(uuid.uuid4().int)[:9]


def register(phone=None):
    s = sess()
    tag = uniq()
    email = f"test_iter22_{tag}@example.com"
    r = s.post(f"{API}/auth/register", json={"full_name": "TEST Owner", "email": email, "phone": phone or rand_phone(),
                                              "password": PWD, "gym_name": f"TEST Gym {tag}", "outlet_name": "Main"})
    assert r.status_code == 200, r.text
    return s, email, r.json()["organisation"]["id"]


def login(identifier, password=PWD):
    s = sess()
    r = s.post(f"{API}/auth/login", json={"identifier": identifier, "password": password})
    return s, r


@pytest.fixture(scope="module")
def org():
    s, email, org_id = register()
    plan = s.post(f"{API}/plans", json={"name": "TEST Monthly", "price": 1000, "duration_type": "months", "duration": 1}).json()
    yield {"s": s, "email": email, "org_id": org_id, "plan": plan}
    # cleanup
    for c in ("members", "payments", "member_invoices", "plans", "staff", "outlets", "attendance", "staff_attendance",
              "biometric_devices", "subscription_payments", "batches"):
        db[c].delete_many({"organisation_id": org_id})
    db.users.delete_many({"organisation_id": org_id})
    db.organisations.delete_one({"id": org_id})


def mk_member(org, **kw):
    body = {"full_name": f"TEST M {uniq()}", "phone": rand_phone(), "plan_id": org["plan"]["id"], **kw}
    return org["s"].post(f"{API}/members", json=body)


# ---------------- Billing ----------------
class TestBilling:
    def _secrets(self):
        st = db.settings.find_one({"id": "platform"}) or {}
        return st.get("razorpay_key_secret") or BE.get("RAZORPAY_KEY_SECRET"), st.get("razorpay_webhook_secret") or BE.get("RAZORPAY_WEBHOOK_SECRET")

    def test_verify_bad_signature_400(self, org):
        r = org["s"].post(f"{API}/subscription/verify", json={"razorpay_order_id": "order_x", "razorpay_payment_id": "pay_x", "razorpay_signature": "bad"})
        assert r.status_code == 400, r.text

    def test_verify_unknown_order_404(self, org):
        ks, _ = self._secrets()
        sig = hmac.new(ks.encode(), b"order_TESTunknown|pay_TESTx", hashlib.sha256).hexdigest()
        r = org["s"].post(f"{API}/subscription/verify", json={"razorpay_order_id": "order_TESTunknown", "razorpay_payment_id": "pay_TESTx", "razorpay_signature": sig})
        assert r.status_code == 404, r.text

    def test_verify_known_order_fake_payment_not_activated(self, org):
        ks, _ = self._secrets()
        oid = f"order_TEST{uniq()}"
        db.subscription_payments.insert_one({"id": uniq(), "organisation_id": org["org_id"], "order_id": oid, "amount": 999, "currency": "INR", "status": "created", "plan_id": "monthly"})
        sig = hmac.new(ks.encode(), f"{oid}|pay_TESTfake".encode(), hashlib.sha256).hexdigest()
        r = org["s"].post(f"{API}/subscription/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": "pay_TESTfake", "razorpay_signature": sig})
        assert r.status_code in (400, 503), r.text  # Razorpay GET /payments fails or mismatch
        o = db.organisations.find_one({"id": org["org_id"]})
        assert o["subscription"]["status"] == "trial"

    def _hook(self, body, secret, event_id=None, sig=None):
        raw = json.dumps(body).encode()
        h = {"Content-Type": "application/json"}
        if sig is not False:
            h["X-Razorpay-Signature"] = sig or hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if event_id:
            h["X-Razorpay-Event-Id"] = event_id
        return requests.post(f"{API}/webhooks/razorpay", data=raw, headers=h)

    def test_webhook_signature_mismatch_duplicate(self, org):
        _, ws = self._secrets()
        oid = f"order_TEST{uniq()}"
        db.subscription_payments.insert_one({"id": uniq(), "organisation_id": org["org_id"], "order_id": oid, "amount": 999, "currency": "INR", "status": "created", "plan_id": "monthly"})
        ev = lambda amt, pid: {"event": "payment.captured", "payload": {"payment": {"entity": {"id": pid, "order_id": oid, "amount": amt, "currency": "INR", "status": "captured"}}}}
        assert self._hook(ev(99900, "pay_a"), ws, sig=False).status_code == 400
        assert self._hook(ev(99900, "pay_a"), ws, sig="deadbeef").status_code == 400
        r = self._hook(ev(100, f"pay_TEST{uniq()}"), ws, event_id=f"evt_TEST{uniq()}")
        assert r.status_code == 200 and r.json()["status"] == "mismatch", r.text
        assert db.organisations.find_one({"id": org["org_id"]})["subscription"]["status"] == "trial"
        pid, eid = f"pay_TEST{uniq()}", f"evt_TEST{uniq()}"
        r = self._hook(ev(99900, pid), ws, event_id=eid)
        assert r.json()["status"] == "processed", r.text
        sub1 = db.organisations.find_one({"id": org["org_id"]})["subscription"]
        assert sub1["status"] == "active"
        assert self._hook(ev(99900, pid), ws, event_id=eid).json()["status"] == "duplicate"
        # same payment with new event id must not extend again
        self._hook(ev(99900, pid), ws, event_id=f"evt_TEST{uniq()}")
        sub2 = db.organisations.find_one({"id": org["org_id"]})["subscription"]
        assert sub2["subscription_ends_at"] == sub1["subscription_ends_at"]


# ---------------- Subscription restriction ----------------
class TestRestriction:
    def test_payment_due_blocks_writes(self):
        s, email, org_id = register()
        try:
            db.organisations.update_one({"id": org_id}, {"$set": {"subscription.status": "active", "subscription.subscription_ends_at": datetime.now(timezone.utc) - timedelta(days=1)}})
            r = s.post(f"{API}/plans", json={"name": "TEST x", "price": 10})
            assert r.status_code == 402, r.text
            assert s.get(f"{API}/subscription").status_code == 200
            assert s.get(f"{API}/auth/me").status_code == 200
            r = s.post(f"{API}/auth/change-password", json={"current_password": "wrongwrong", "new_password": "Another@2026"})
            assert r.status_code != 402, r.text
        finally:
            db.plans.delete_many({"organisation_id": org_id}); db.users.delete_many({"organisation_id": org_id})
            db.outlets.delete_many({"organisation_id": org_id}); db.organisations.delete_one({"id": org_id})


# ---------------- Permissions ----------------
@pytest.fixture(scope="module")
def staff(org):
    s = org["s"]
    out = {}
    for key, role, perm, fin in (("view", "staff", "view", False), ("manage", "manager", "manage", False), ("full", "manager", "full", False), ("fin", "receptionist", "view", True)):
        email = f"test_iter22_{key}_{uniq()}@example.com"
        r = s.post(f"{API}/staff", json={"name": f"TEST {key}", "role": role, "email": email, "phone": rand_phone(), "password": PWD, "permission": perm, "enable_finance": fin, "salary": 12345})
        assert r.status_code == 200, r.text
        ls, lr = login(email)
        assert lr.status_code == 200, lr.text
        out[key] = {"s": ls, "doc": r.json(), "email": email}
    return out


class TestPermissions:
    def test_view_cannot_create_member(self, org, staff):
        r = staff["view"]["s"].post(f"{API}/members", json={"full_name": "TEST V", "phone": rand_phone(), "plan_id": org["plan"]["id"]})
        assert r.status_code == 403

    def test_manage_restrictions(self, org, staff):
        s = staff["manage"]["s"]
        m = mk_member(org, amount_paid=100).json()
        pay = org["s"].get(f"{API}/payments", params={"search": m["full_name"]}).json()["items"][0]
        outlet = db.outlets.find_one({"organisation_id": org["org_id"]})
        assert s.post(f"{API}/staff", json={"name": "TEST x", "role": "trainer", "phone": rand_phone()}).status_code == 403
        assert s.put(f"{API}/outlets/{outlet['id']}", json={"name": "Hack"}).status_code == 403
        assert s.put(f"{API}/gym/profile", json={"name": "Hacked"}).status_code == 403
        assert s.delete(f"{API}/members/{m['id']}").status_code == 403
        assert s.delete(f"{API}/payments/{pay['id']}").status_code == 403

    def test_manage_can_delete_expense(self, org, staff):
        """Matrix says delete needs 'full' - DELETE /expenses uses require_write."""
        e = org["s"].post(f"{API}/expenses", json={"name": "TEST expense", "category": "Rent", "amount": 10, "date": TODAY.isoformat()})
        if e.status_code != 200:
            pytest.skip(f"expense create failed {e.text}")
        r = staff["manage"]["s"].delete(f"{API}/expenses/{e.json()['id']}")
        assert r.status_code == 403, f"manage user deleted expense: {r.status_code}"

    def test_full_manager_limits(self, org, staff):
        s = staff["full"]["s"]
        ok = s.post(f"{API}/staff", json={"name": "TEST byfull", "role": "trainer", "phone": rand_phone(), "permission": "manage"})
        assert ok.status_code == 200, ok.text
        for bad in ({"role": "admin"}, {"password": "Abcdefgh1", "email": f"x{uniq()}@example.com"}, {"permission": "full"}, {"enable_finance": True}):
            r = s.post(f"{API}/staff", json={"name": "TEST bad", "role": "trainer", "phone": rand_phone(), **bad})
            assert r.status_code == 403, (bad, r.text)
        me = staff["full"]["doc"]
        base = {k: me[k] for k in ("name", "role", "email", "phone")}
        assert s.put(f"{API}/staff/{me['id']}", json={**base, "permission": "full", "enable_finance": True}).status_code == 403
        other = staff["view"]["doc"]
        ob = {k: other[k] for k in ("name", "role", "email", "phone")}
        assert s.put(f"{API}/staff/{other['id']}", json={**ob, "permission": "manage"}).status_code == 403
        assert s.put(f"{API}/staff/{other['id']}", json={**ob, "role": "trainer"}).status_code == 403
        assert s.put(f"{API}/staff/{other['id']}", json={**ob, "password": "NewPass@123"}).status_code == 403
        assert s.put(f"{API}/staff/{other['id']}", json={**ob, "email": f"n{uniq()}@example.com"}).status_code == 403

    def test_full_manager_edit_does_not_wipe_salary(self, org, staff):
        s = staff["full"]["s"]
        other = staff["view"]["doc"]
        listed = next(x for x in s.get(f"{API}/staff").json() if x["id"] == other["id"])
        assert "salary" not in listed
        r = s.put(f"{API}/staff/{other['id']}", json={**{k: listed[k] for k in ("name", "role", "email", "phone", "permission")}, "address": "TEST addr"})
        assert r.status_code == 200, r.text
        assert db.staff.find_one({"id": other["id"]}).get("salary") == 12345, "salary wiped by non-finance manager edit"

    def test_full_manager_cannot_disable_or_delete_admin(self, org, staff):
        email = f"test_iter22_adm_{uniq()}@example.com"
        adm = org["s"].post(f"{API}/staff", json={"name": "TEST admin", "role": "admin", "email": email, "phone": rand_phone(), "password": PWD, "permission": "full"}).json()
        r = staff["full"]["s"].post(f"{API}/staff/{adm['id']}/toggle")
        assert r.status_code == 403, f"manager could toggle admin: {r.status_code}"

    def test_salary_visibility_and_finance(self, org, staff):
        assert "salary" in org["s"].get(f"{API}/staff").json()[0]
        assert all("salary" not in x for x in staff["manage"]["s"].get(f"{API}/staff").json())
        assert any("salary" in x for x in staff["fin"]["s"].get(f"{API}/staff").json())
        assert staff["manage"]["s"].get(f"{API}/finance/summary").status_code == 403
        assert staff["fin"]["s"].get(f"{API}/finance/summary").status_code == 200
        assert org["s"].get(f"{API}/finance/summary").status_code == 200


# ---------------- Auth ----------------
class TestAuth:
    def test_long_identifier_422(self):
        assert login("a" * 255)[1].status_code == 422

    def test_refresh_disabled_user_403(self, org):
        email = f"test_iter22_dis_{uniq()}@example.com"
        st = org["s"].post(f"{API}/staff", json={"name": "TEST dis", "role": "staff", "email": email, "phone": rand_phone(), "password": PWD}).json()
        s, r = login(email)
        assert r.status_code == 200
        org["s"].post(f"{API}/staff/{st['id']}/toggle")
        assert s.post(f"{API}/auth/refresh").status_code == 403

    def test_phone_dup_login_409(self):
        ph = rand_phone()
        a = register(ph); b = register(ph)
        try:
            r = login(ph)[1]
            assert r.status_code == 409 and "email" in r.json()["detail"].lower(), r.text
            assert login(a[1])[1].status_code == 200
        finally:
            for x in (a, b):
                db.users.delete_many({"organisation_id": x[2]}); db.outlets.delete_many({"organisation_id": x[2]}); db.organisations.delete_one({"id": x[2]})

    def test_csrf_origin(self, org):
        s = org["s"]
        body = {"name": f"TEST csrf {uniq()}", "price": 1}
        assert s.post(f"{API}/plans", json=body, headers={"Origin": "https://evil.com"}).status_code == 403
        assert s.post(f"{API}/plans", json=body, headers={"Referer": "https://evil.com/x"}).status_code == 403
        assert s.post(f"{API}/plans", json=body, headers={"Origin": BASE_URL}).status_code == 200
        assert s.post(f"{API}/plans", json=body).status_code == 200

    def test_bcrypt_and_cookies(self, org):
        u = db.users.find_one({"email": org["email"]})
        assert u["password_hash"].startswith("$2b$")
        s, r = login(org["email"])
        sc = r.headers.get("set-cookie", "").lower()
        assert "httponly" in sc and "access_token" in sc


# ---------------- Ledger ----------------
class TestLedger:
    def test_full_cycle(self, org):
        s = org["s"]
        m = mk_member(org, amount_paid=500).json()
        assert m["due_amount"] == 500 and m["payment_status"] == "Partially Paid"
        r = s.post(f"{API}/members/{m['id']}/renew", json={"plan_id": org["plan"]["id"], "amount_paid": 1000}).json()
        assert r["due_amount"] == 500, r
        p = s.post(f"{API}/payments", json={"member_id": m["id"], "amount": 800}).json()
        assert p["member_due_remaining"] == 0 and p["member_credit"] == 300, p
        r = s.post(f"{API}/members/{m['id']}/renew", json={"plan_id": org["plan"]["id"], "amount_paid": 0}).json()
        assert r["due_amount"] == 700 and r.get("credit_balance") == 0, r
        e = s.put(f"{API}/payments/{p['id']}", json={"amount": 1000}).json()
        assert e["member_due_remaining"] == 500, e
        rv = s.delete(f"{API}/payments/{p['id']}")
        assert rv.status_code == 200 and rv.json()["member_due_remaining"] == 1500, rv.text
        assert db.payments.find_one({"id": p["id"]})["status"] == "reversed"
        rev = db.payments.find_one({"reversal_of": p["id"]})
        assert rev["type"] == "reversal" and rev["amount"] == -1000
        assert s.delete(f"{API}/payments/{p['id']}").status_code == 404
        assert s.put(f"{API}/payments/{p['id']}", json={"amount": 5}).status_code == 409
        assert s.put(f"{API}/payments/{rev['id']}", json={"amount": 5}).status_code == 409
        assert s.delete(f"{API}/payments/{rev['id']}").status_code == 404

    def test_validation(self, org):
        s = org["s"]
        assert mk_member(org, discount=-1).status_code == 422
        assert mk_member(org, admission_amount=-1).status_code == 422
        assert mk_member(org, amount_paid=-1).status_code == 422
        assert mk_member(org, discount=1001).status_code == 422
        assert mk_member(org, payment_method="Bitcoin").status_code == 422
        arch = s.post(f"{API}/plans", json={"name": "TEST arch", "price": 10, "status": "archived"}).json()
        assert mk_member(org, plan_id=arch["id"]).status_code == 422
        pt = s.post(f"{API}/plans", json={"name": "TEST pt", "price": 10, "type": "pt"}).json()
        assert mk_member(org, plan_id=pt["id"]).status_code == 422
        m = mk_member(org).json()
        assert s.post(f"{API}/payments", json={"member_id": m["id"], "amount": -5}).status_code == 422
        assert s.post(f"{API}/payments", json={"member_id": m["id"], "amount": 5, "method": "Gold"}).status_code == 422
        assert s.post(f"{API}/members/{m['id']}/renew", json={"plan_id": org["plan"]["id"], "discount": 5000}).status_code == 422

    def test_concurrent_payments(self, org):
        s = org["s"]
        m = mk_member(org, amount_paid=0).json()
        assert m["due_amount"] == 1000
        cookies = s.cookies.get_dict()

        def pay(_):
            return requests.post(f"{API}/payments", json={"member_id": m["id"], "amount": 100}, cookies=cookies).status_code
        with cf.ThreadPoolExecutor(5) as ex:
            codes = list(ex.map(pay, range(5)))
        ok = codes.count(200)
        got = s.get(f"{API}/members/{m['id']}").json()
        mm = got.get("member", got)
        assert mm["due_amount"] == 1000 - 100 * ok, (codes, mm["due_amount"])
        assert ok == 5, codes


# ---------------- Dates / freeze ----------------
class TestDates:
    def test_month_end(self, org):
        assert mk_member(org, membership_start="2026-01-31").json()["membership_expiry"] == "2026-02-28"
        assert mk_member(org, membership_start="2026-03-31").json()["membership_expiry"] == "2026-04-30"

    def test_freeze_flow(self, org):
        s = org["s"]
        m = mk_member(org, membership_start=TODAY.isoformat()).json()
        exp0 = m["membership_expiry"]
        f1 = s.post(f"{API}/members/{m['id']}/freeze", json={"freeze_from": (TODAY + timedelta(days=3)).isoformat(), "freeze_until": (TODAY + timedelta(days=7)).isoformat()})
        assert f1.status_code == 200 and f1.json()["status"] != "frozen", f1.text
        ov = s.post(f"{API}/members/{m['id']}/freeze", json={"freeze_from": (TODAY + timedelta(days=5)).isoformat(), "freeze_until": (TODAY + timedelta(days=9)).isoformat()})
        assert ov.status_code == 409
        un = s.post(f"{API}/members/{m['id']}/unfreeze").json()
        assert un["membership_expiry"] == exp0, un

    def test_current_freeze_plus_future_freeze_stays_frozen(self, org):
        s = org["s"]
        m = mk_member(org, membership_start=TODAY.isoformat()).json()
        assert s.post(f"{API}/members/{m['id']}/freeze", json={"freeze_from": TODAY.isoformat(), "freeze_until": (TODAY + timedelta(days=3)).isoformat()}).json()["status"] == "frozen"
        r = s.post(f"{API}/members/{m['id']}/freeze", json={"freeze_from": (TODAY + timedelta(days=10)).isoformat(), "freeze_until": (TODAY + timedelta(days=12)).isoformat()})
        assert r.status_code == 200
        assert r.json()["status"] == "frozen", "adding a future freeze un-froze the current freeze"


# ---------------- Attendance ----------------
class TestAttendance:
    def test_manual_checkin_rules(self, org):
        s = org["s"]
        exp = mk_member(org, membership_start="2025-01-01").json()
        assert s.post(f"{API}/attendance/check-in", json={"member_id": exp["id"]}).status_code == 403
        fr = mk_member(org).json()
        s.post(f"{API}/members/{fr['id']}/freeze", json={"freeze_from": TODAY.isoformat(), "freeze_until": (TODAY + timedelta(days=2)).isoformat()})
        assert s.post(f"{API}/attendance/check-in", json={"member_id": fr["id"]}).status_code == 403
        ok = mk_member(org).json()
        assert s.post(f"{API}/attendance/check-in", json={"member_id": ok["id"]}).status_code == 200
        assert s.post(f"{API}/attendance/check-in", json={"member_id": ok["id"]}).status_code == 409

    def test_qr_staff(self, org):
        s = org["s"]
        token = s.get(f"{API}/attendance/qr").json()["outlets"][0]["token"]
        ph = rand_phone()
        st = s.post(f"{API}/staff", json={"name": "TEST nologin", "role": "trainer", "phone": ph}).json()
        r = requests.post(f"{API}/public/checkin/{token}", json={"kind": "staff", "identifier": ph})
        assert r.status_code == 200 and r.json()["action"] == "in", r.text
        s.post(f"{API}/staff/{st['id']}/toggle")
        r = requests.post(f"{API}/public/checkin/{token}", json={"kind": "staff", "identifier": ph})
        assert r.status_code == 403, r.text

    def _device(self, org, **upd):
        sn = f"TST{uniq().upper()}"
        d = org["s"].post(f"{API}/attendance/devices", json={"device_type": "eSSL K30", "serial_number": sn, "name": "TEST dev"}).json()
        if upd:
            org["s"].put(f"{API}/attendance/devices/{d['id']}", json=upd)
        return d, sn

    def test_adms_allowed_ips(self, org):
        d, sn = self._device(org, allowed_ips=["203.0.113.9"])
        m = mk_member(org).json()
        pin = m["member_code"].split("-")[-1]
        assert requests.get(f"{API}/iclock/cdata", params={"SN": sn}).status_code == 200
        r = requests.post(f"{API}/iclock/cdata", params={"SN": sn, "table": "ATTLOG"}, data=f"{pin}\t{datetime.now(IST):%Y-%m-%d %H:%M:%S}\t0\t1")
        assert r.status_code == 200 and r.text.startswith("OK")
        assert db.attendance.count_documents({"member_id": m["id"]}) == 0

    def test_adms_commands_and_delayed_attlog(self, org):
        d, sn = self._device(org, auto_delete_on_expiry=True)
        exp = mk_member(org, membership_start="2025-01-01").json()
        r1 = requests.get(f"{API}/iclock/getrequest", params={"SN": sn}).text
        assert r1.startswith("C:") and "DATA DELETE USERINFO" in r1, r1
        assert requests.get(f"{API}/iclock/getrequest", params={"SN": sn}).text == "OK"
        db.device_commands.update_many({"device_id": d["id"]}, {"$set": {"sent_at": datetime.now(timezone.utc) - timedelta(minutes=6)}})
        r2 = requests.get(f"{API}/iclock/getrequest", params={"SN": sn}).text
        assert r2.startswith("C:"), r2
        acks = "\n".join(f"ID={ln.split(':')[1]}&Return=0&CMD=DATA" for ln in r2.splitlines())
        requests.post(f"{API}/iclock/devicecmd", params={"SN": sn}, data=acks)
        db.device_commands.update_many({"device_id": d["id"]}, {"$set": {"sent_at": datetime.now(timezone.utc) - timedelta(minutes=6)}})
        assert requests.get(f"{API}/iclock/getrequest", params={"SN": sn}).text == "OK"
        # delayed ATTLOG
        m = mk_member(org).json()
        pin = m["member_code"].split("-")[-1]
        y = datetime.now(IST) - timedelta(days=1)
        y1, y2 = y.replace(hour=7, minute=0, second=0), y.replace(hour=9, minute=0, second=0)
        now_t = datetime.now(IST).replace(microsecond=0)
        requests.post(f"{API}/iclock/cdata", params={"SN": sn, "table": "ATTLOG"}, data=f"{pin}\t{y1:%Y-%m-%d %H:%M:%S}\t0\t1")
        requests.post(f"{API}/iclock/cdata", params={"SN": sn, "table": "ATTLOG"}, data=f"{pin}\t{now_t:%Y-%m-%d %H:%M:%S}\t0\t1")
        requests.post(f"{API}/iclock/cdata", params={"SN": sn, "table": "ATTLOG"}, data=f"{pin}\t{y2:%Y-%m-%d %H:%M:%S}\t0\t1")
        rows = list(db.attendance.find({"member_id": m["id"]}).sort("check_in", 1))
        assert len(rows) == 2, rows
        assert rows[0]["check_out"] is not None and rows[0]["check_out"].replace(tzinfo=timezone.utc).astimezone(IST).date() == y.date()
        assert rows[1]["check_out"] is None


# ---------------- Auth playbook (lockout, forgot/reset) ----------------
class TestPlaybook:
    def test_lockout_forgot_reset(self):
        s, email, org_id = register()
        try:
            # NOTE: per-IP key uses ingress pod IP (TRUSTED_PROXIES unset) so 5-fail lock is inconsistent; 10/email cap must hold
            codes = [login(email, "WrongPass1!")[1].status_code for _ in range(10)]
            assert 429 in codes or codes == [401] * 10
            assert login(email)[1].status_code == 429
            g1 = requests.post(f"{API}/auth/forgot-password", json={"email": email})
            g2 = requests.post(f"{API}/auth/forgot-password", json={"email": f"nobody_{uniq()}@example.com"})
            assert g1.status_code == g2.status_code == 200 and g1.json() == g2.json()
            u = db.users.find_one({"email": email})
            tok = db.password_reset_tokens.find_one({"user_id": u["id"]})
            assert tok and len(tok["token_hash"]) == 64 and "token" not in tok
            raw = "TESTrawtoken" + uniq()
            db.password_reset_tokens.insert_one({"token_hash": hashlib.sha256(raw.encode()).hexdigest(), "user_id": u["id"], "email": email,
                                                 "expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "used": False})
            assert requests.post(f"{API}/auth/reset-password", json={"token": raw, "password": "NewPass@2026"}).status_code == 200
            assert login(email, "NewPass@2026")[1].status_code == 200
        finally:
            db.users.delete_many({"organisation_id": org_id}); db.outlets.delete_many({"organisation_id": org_id}); db.organisations.delete_one({"id": org_id})
            db.password_reset_tokens.delete_many({"email": email}); db.login_attempts.delete_many({"email": email})
