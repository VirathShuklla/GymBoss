# Iteration 24: client_ip spoofing fix — XFF left-most entries must be ignored (login lock, forgot-password, ADMS allowed_ips).
import uuid
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
PWD = "TestPass@2026"


def uniq():
    return uuid.uuid4().hex[:8]


def rand_phone():
    return "9" + str(uuid.uuid4().int)[:9]


def bad_login(ident, xff=None):
    h = {"X-Forwarded-For": xff} if xff else {}
    return requests.post(f"{API}/auth/login", json={"identifier": ident, "password": "bad"}, headers=h)


@pytest.fixture(scope="module")
def org():
    s = requests.Session()
    tag = uniq()
    r = s.post(f"{API}/auth/register", json={"full_name": "TEST Owner", "email": f"test_iter24_{tag}@example.com", "phone": rand_phone(),
                                              "password": PWD, "gym_name": f"TEST Gym {tag}", "outlet_name": "Main"})
    assert r.status_code == 200, r.text
    org_id = r.json()["organisation"]["id"]
    plan = s.post(f"{API}/plans", json={"name": "TEST Monthly", "price": 1000, "duration_type": "months", "duration": 1}).json()
    yield {"s": s, "org_id": org_id, "plan": plan}
    for c in ("members", "payments", "member_invoices", "plans", "staff", "outlets", "attendance", "biometric_devices", "device_commands"):
        db[c].delete_many({"organisation_id": org_id})
    db.users.delete_many({"organisation_id": org_id})
    db.organisations.delete_one({"id": org_id})


class TestLoginIP:
    def test_spoofed_xff_not_stored(self):
        ident = f"test_iter24_sp_{uniq()}@example.com"
        try:
            assert bad_login(ident, "1.2.3.4").status_code == 401
            row = db.login_attempts.find_one({"email": ident})
            ip = row["identifier"].rsplit(":", 1)[0] if row["identifier"].endswith(ident) else row["identifier"]
            ip = row["identifier"][: -len(ident) - 1]
            assert ip != "1.2.3.4", row
            assert not ip.startswith(("10.", "127.", "192.168.")), f"internal hop stored: {ip}"
        finally:
            db.login_attempts.delete_many({"email": ident})

    def test_rotating_xff_cannot_bypass_lock(self):
        ident = f"test_iter24_rot_{uniq()}@example.com"
        try:
            codes = [bad_login(ident, f"198.51.100.{i + 10}").status_code for i in range(6)]
            assert codes[:5] == [401] * 5 and codes[5] == 429, codes
            ids = {r["identifier"] for r in db.login_attempts.find({"email": ident})}
            assert len(ids) == 1, ids
            # Header with multiple entries (attacker prepends) also locked
            assert bad_login(ident, "8.8.8.8, 9.9.9.9").status_code == 429
        finally:
            db.login_attempts.delete_many({"email": ident})


class TestForgotIP:
    def test_spoofed_xff_not_used(self):
        e = f"test_iter24_fp_{uniq()}@example.com"
        try:
            assert requests.post(f"{API}/auth/forgot-password", json={"email": e}, headers={"X-Forwarded-For": "192.0.2.99"}).status_code == 200
            row = db.password_reset_requests.find_one({"email": e})
            assert row and row["ip"] != "192.0.2.99", row
        finally:
            db.password_reset_requests.delete_many({"email": e})


class TestADMS:
    def _setup(self, org, allowed):
        sn = f"TST{uniq().upper()}"
        d = org["s"].post(f"{API}/attendance/devices", json={"device_type": "eSSL K30", "serial_number": sn, "name": "TEST dev"}).json()
        r = org["s"].put(f"{API}/attendance/devices/{d['id']}", json={"allowed_ips": allowed})
        assert r.status_code == 200, r.text
        m = org["s"].post(f"{API}/members", json={"full_name": f"TEST M {uniq()}", "phone": rand_phone(), "plan_id": org["plan"]["id"]}).json()
        line = f"{m['member_code'].split('-')[-1]}\t{datetime.now(IST):%Y-%m-%d %H:%M:%S}\t0\t1"
        return sn, m, line

    def test_spoofed_xff_rejected(self, org):
        sn, m, line = self._setup(org, ["203.0.113.77"])
        r = requests.post(f"{API}/iclock/cdata", params={"SN": sn, "table": "ATTLOG"}, data=line, headers={"X-Forwarded-For": "203.0.113.77"})
        assert r.status_code == 200
        assert db.attendance.count_documents({"member_id": m["id"]}) == 0

    def test_real_ip_accepted(self, org):
        # learn our real IP as seen by the server
        ident = f"test_iter24_ip_{uniq()}@example.com"
        bad_login(ident)
        row = db.login_attempts.find_one({"email": ident})
        db.login_attempts.delete_many({"email": ident})
        real = row["identifier"][: -len(ident) - 1]
        sn, m, line = self._setup(org, [real])
        r = requests.post(f"{API}/iclock/cdata", params={"SN": sn, "table": "ATTLOG"}, data=line, headers={"X-Forwarded-For": "6.6.6.6"})
        assert r.status_code == 200
        assert db.attendance.count_documents({"member_id": m["id"]}) == 1, f"real ip {real}"
