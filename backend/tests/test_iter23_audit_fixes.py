# Iteration 23: retest of iteration-22 audit fixes (staff salary/guard, client_ip XFF, freeze history,
# delete permission matrix, verify unknown payment, reconcile expiry, ADMS devicecmd retries). Throwaway orgs only.
import uuid
import hmac
import hashlib
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
API = FE["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()
PWD = "TestPass@2026"
CRON = BE.get("CRON_SECRET") or "c4ccd2fc5f01b0403c339b6de9042097438609f5411d34bf"


def uniq():
    return uuid.uuid4().hex[:8]


def rand_phone():
    return "9" + str(uuid.uuid4().int)[:9]


def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def login(identifier, password=PWD, ip=None):
    s = sess()
    h = {"X-Forwarded-For": ip} if ip else {}
    return s, s.post(f"{API}/auth/login", json={"identifier": identifier, "password": password}, headers=h)


@pytest.fixture(scope="module")
def org():
    s = sess()
    tag = uniq()
    email = f"test_iter23_{tag}@example.com"
    r = s.post(f"{API}/auth/register", json={"full_name": "TEST Owner", "email": email, "phone": rand_phone(), "password": PWD,
                                              "gym_name": f"TEST Gym {tag}", "outlet_name": "Main"})
    assert r.status_code == 200, r.text
    org_id = r.json()["organisation"]["id"]
    plan = s.post(f"{API}/plans", json={"name": "TEST Monthly", "price": 1000, "duration_type": "months", "duration": 1}).json()
    staff = {}
    for key, role, perm, fin in (("manage", "manager", "manage", False), ("full", "manager", "full", False),
                                 ("fin", "manager", "full", True), ("admin", "admin", "full", False), ("admin2", "admin", "full", False)):
        em = f"test_iter23_{key}_{uniq()}@example.com"
        d = s.post(f"{API}/staff", json={"name": f"TEST {key}", "role": role, "email": em, "phone": rand_phone(), "password": PWD,
                                          "permission": perm, "enable_finance": fin, "salary": 12345})
        assert d.status_code == 200, d.text
        ls, lr = login(em)
        assert lr.status_code == 200, lr.text
        staff[key] = {"s": ls, "doc": d.json(), "email": em}
    yield {"s": s, "email": email, "org_id": org_id, "plan": plan, "staff": staff}
    for c in ("members", "payments", "member_invoices", "plans", "staff", "outlets", "attendance", "staff_attendance",
              "biometric_devices", "subscription_payments", "expenses", "device_commands"):
        db[c].delete_many({"organisation_id": org_id})
    db.users.delete_many({"organisation_id": org_id})
    db.organisations.delete_one({"id": org_id})


def mk_member(org, **kw):
    return org["s"].post(f"{API}/members", json={"full_name": f"TEST M {uniq()}", "phone": rand_phone(), "plan_id": org["plan"]["id"], **kw})


def new_trainer(org, salary=5000):
    r = org["s"].post(f"{API}/staff", json={"name": f"TEST tr {uniq()}", "role": "trainer", "phone": rand_phone(), "salary": salary})
    assert r.status_code == 200, r.text
    return r.json()


def base(doc):
    return {k: doc[k] for k in ("name", "role", "phone", "permission") if k in doc} | {"email": doc.get("email")}


# ---- Staff salary handling ----
class TestStaffSalary:
    def test_non_finance_manager_edit_keeps_salary(self, org):
        t = new_trainer(org)
        s = org["staff"]["full"]["s"]
        listed = next(x for x in s.get(f"{API}/staff").json() if x["id"] == t["id"])
        assert "salary" not in listed
        r = s.put(f"{API}/staff/{t['id']}", json={**base(listed), "address": "TEST addr"})
        assert r.status_code == 200, r.text
        assert db.staff.find_one({"id": t["id"]})["salary"] == 5000
        # explicit salary from non-finance manager is ignored too
        r = s.put(f"{API}/staff/{t['id']}", json={**base(listed), "salary": 1})
        assert r.status_code == 200 and db.staff.find_one({"id": t["id"]})["salary"] == 5000

    def test_owner_and_finance_can_change_salary(self, org):
        t = new_trainer(org)
        r = org["s"].put(f"{API}/staff/{t['id']}", json={**base(t), "salary": 7000})
        assert r.status_code == 200 and db.staff.find_one({"id": t["id"]})["salary"] == 7000, r.text
        r = org["staff"]["fin"]["s"].put(f"{API}/staff/{t['id']}", json={**base(t), "salary": 8000})
        assert r.status_code == 200 and db.staff.find_one({"id": t["id"]})["salary"] == 8000, r.text
        r = org["staff"]["admin"]["s"].put(f"{API}/staff/{t['id']}", json={**base(t), "salary": 9000})
        assert r.status_code == 200 and db.staff.find_one({"id": t["id"]})["salary"] == 9000, r.text
        # owner edit that omits salary keeps it
        r = org["s"].put(f"{API}/staff/{t['id']}", json={**base(t), "address": "x"})
        assert r.status_code == 200 and db.staff.find_one({"id": t["id"]})["salary"] == 9000


# ---- Staff toggle/delete guard ----
class TestStaffGuard:
    def test_full_manager_on_admin_403(self, org):
        adm = org["staff"]["admin2"]["doc"]
        s = org["staff"]["full"]["s"]
        assert s.post(f"{API}/staff/{adm['id']}/toggle").status_code == 403
        assert s.delete(f"{API}/staff/{adm['id']}").status_code == 403
        assert db.staff.find_one({"id": adm["id"]})["status"] == "active"

    def test_self_toggle_delete_403(self, org):
        for key in ("full", "admin"):
            me = org["staff"][key]
            assert me["s"].post(f"{API}/staff/{me['doc']['id']}/toggle").status_code == 403, key
            assert me["s"].delete(f"{API}/staff/{me['doc']['id']}").status_code == 403, key

    def test_full_manager_can_toggle_trainer(self, org):
        t = new_trainer(org)
        r = org["staff"]["full"]["s"].post(f"{API}/staff/{t['id']}/toggle")
        assert r.status_code == 200, r.text

    def test_admin_can_toggle_other_admin(self, org):
        adm = org["staff"]["admin2"]["doc"]
        s = org["staff"]["admin"]["s"]
        assert s.post(f"{API}/staff/{adm['id']}/toggle").status_code == 200
        assert s.post(f"{API}/staff/{adm['id']}/toggle").status_code == 200

    def test_owner_toggle_and_delete(self, org):
        em = f"test_iter23_del_{uniq()}@example.com"
        d = org["s"].post(f"{API}/staff", json={"name": "TEST delme", "role": "admin", "email": em, "phone": rand_phone(), "password": PWD, "permission": "full"}).json()
        r = org["s"].post(f"{API}/staff/{d['id']}/toggle")
        assert r.status_code == 200 and r.json()["status"] == "disabled", r.text
        assert login(em)[1].status_code == 403
        assert org["s"].delete(f"{API}/staff/{d['id']}").status_code == 200
        assert db.staff.find_one({"id": d["id"]}) is None or db.staff.find_one({"id": d["id"]}).get("deleted_at")


# ---- Delete permission matrix ----
class TestDeleteMatrix:
    def test_manage_403_full_200(self, org):
        s, mg, fl = org["s"], org["staff"]["manage"]["s"], org["staff"]["full"]["s"]
        e = s.post(f"{API}/expenses", json={"name": "TEST exp", "category": "Rent", "amount": 10, "date": TODAY.isoformat()}).json()
        p = s.post(f"{API}/plans", json={"name": f"TEST P {uniq()}", "price": 10, "duration_type": "months", "duration": 1}).json()
        d = s.post(f"{API}/attendance/devices", json={"device_type": "eSSL K30", "serial_number": f"TST{uniq().upper()}", "name": "TEST d"}).json()
        for url in (f"expenses/{e['id']}", f"plans/{p['id']}", f"attendance/devices/{d['id']}"):
            assert mg.delete(f"{API}/{url}").status_code == 403, url
        for url in (f"expenses/{e['id']}", f"plans/{p['id']}", f"attendance/devices/{d['id']}"):
            r = fl.delete(f"{API}/{url}")
            assert r.status_code == 200, (url, r.text)
        e2 = s.post(f"{API}/expenses", json={"name": "TEST exp2", "category": "Rent", "amount": 10, "date": TODAY.isoformat()}).json()
        assert s.delete(f"{API}/expenses/{e2['id']}").status_code == 200


# ---- client_ip / X-Forwarded-For ----
class TestClientIP:
    # iter24: client_ip ignores client-supplied XFF entries; spoof tests moved to test_iter24_client_ip.py
    def test_login_lockout_not_bypassed_by_xff(self, org):
        ident = f"test_iter23_lock_{uniq()}@example.com"
        try:
            codes = [login(ident, "bad", ip=f"198.51.100.{i + 1}")[1].status_code for i in range(6)]
            assert codes[:5] == [401] * 5 and codes[5] == 429, codes
            assert len({r["identifier"] for r in db.login_attempts.find({"email": ident})}) == 1
        finally:
            db.login_attempts.delete_many({"email": ident})

    def test_adms_allowed_ips_ignores_spoofed_xff(self, org):
        sn = f"TST{uniq().upper()}"
        d = org["s"].post(f"{API}/attendance/devices", json={"device_type": "eSSL K30", "serial_number": sn, "name": "TEST dev"}).json()
        org["s"].put(f"{API}/attendance/devices/{d['id']}", json={"allowed_ips": ["203.0.113.77"]})
        m = mk_member(org).json()
        pin = m["member_code"].split("-")[-1]
        line = f"{pin}\t{datetime.now(IST):%Y-%m-%d %H:%M:%S}\t0\t1"
        r = requests.post(f"{API}/iclock/cdata", params={"SN": sn, "table": "ATTLOG"}, data=line, headers={"X-Forwarded-For": "203.0.113.77"})
        assert r.status_code == 200
        assert db.attendance.count_documents({"member_id": m["id"]}) == 0


# ---- Freeze history ----
class TestFreeze:
    def test_current_plus_future_freeze_blocks_checkin(self, org):
        s = org["s"]
        m = mk_member(org, membership_start=TODAY.isoformat()).json()
        r1 = s.post(f"{API}/members/{m['id']}/freeze", json={"freeze_from": TODAY.isoformat(), "freeze_until": (TODAY + timedelta(days=3)).isoformat()})
        assert r1.status_code == 200 and r1.json()["status"] == "frozen", r1.text
        r2 = s.post(f"{API}/members/{m['id']}/freeze", json={"freeze_from": (TODAY + timedelta(days=10)).isoformat(), "freeze_until": (TODAY + timedelta(days=12)).isoformat()})
        assert r2.status_code == 200 and r2.json()["status"] == "frozen", r2.text
        g = s.get(f"{API}/members/{m['id']}").json()
        assert (g.get("member") or g)["status"] == "frozen"
        assert s.post(f"{API}/attendance/check-in", json={"member_id": m["id"]}).status_code == 403


# ---- Billing verify / reconcile ----
class TestBilling:
    def test_verify_unknown_payment_400(self, org):
        st = db.settings.find_one({"id": "platform"}) or {}
        ks = st.get("razorpay_key_secret") or BE.get("RAZORPAY_KEY_SECRET")
        oid = f"order_TEST{uniq()}"
        db.subscription_payments.insert_one({"id": uniq(), "organisation_id": org["org_id"], "order_id": oid, "amount": 999, "currency": "INR",
                                             "status": "created", "plan_id": "monthly", "created_at": datetime.now(timezone.utc)})
        pid = f"pay_TEST{uniq()}"
        sig = hmac.new(ks.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
        r = org["s"].post(f"{API}/subscription/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})
        assert r.status_code == 400, r.text
        assert db.organisations.find_one({"id": org["org_id"]})["subscription"]["status"] == "trial"

    def test_reconcile_expires_old_created(self, org):
        old_id, new_id = uniq(), uniq()
        db.subscription_payments.insert_many([
            {"id": old_id, "organisation_id": org["org_id"], "order_id": f"order_TESTold{uniq()}", "amount": 999, "status": "created",
             "created_at": datetime.now(timezone.utc) - timedelta(days=5)},
            {"id": new_id, "organisation_id": org["org_id"], "order_id": f"order_TESTnew{uniq()}", "amount": 999, "status": "created",
             "created_at": datetime.now(timezone.utc) - timedelta(days=1)}])
        t0 = time.time()
        r = requests.post(f"{API}/internal/billing/reconcile", headers={"X-Cron-Secret": CRON})
        el = time.time() - t0
        assert r.status_code == 200, r.text
        assert db.subscription_payments.find_one({"id": old_id})["status"] == "expired"
        assert db.subscription_payments.find_one({"id": new_id})["status"] == "created"
        assert el < 30, f"reconcile took {el:.1f}s"
        print("reconcile", r.json(), f"{el:.1f}s")


# ---- ADMS devicecmd retries ----
class TestADMSRetries:
    def test_failed_return_requeues_then_fails(self, org):
        sn = f"TST{uniq().upper()}"
        d = org["s"].post(f"{API}/attendance/devices", json={"device_type": "eSSL K30", "serial_number": sn, "name": "TEST dev"}).json()
        db.device_commands.insert_one({"id": uniq(), "device_id": d["id"], "organisation_id": org["org_id"], "cmd": "DATA DELETE USERINFO PIN=99999",
                                       "status": "queued", "created_at": datetime.now(timezone.utc)})
        for attempt in range(1, 4):
            txt = requests.get(f"{API}/iclock/getrequest", params={"SN": sn}).text
            assert txt.startswith("C:"), (attempt, txt)
            seq = txt.split(":")[1]
            requests.post(f"{API}/iclock/devicecmd", params={"SN": sn}, data=f"ID={seq}&Return=-1&CMD=DATA")
            c = db.device_commands.find_one({"device_id": d["id"]})
            assert c["attempts"] == attempt
            assert c["status"] == ("queued" if attempt < 3 else "failed"), c
        assert requests.get(f"{API}/iclock/getrequest", params={"SN": sn}).text == "OK"
