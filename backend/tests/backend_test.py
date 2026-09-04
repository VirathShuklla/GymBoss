"""GYMBOSS_VVO Milestone 1 backend API tests."""
import os
import re
import time
import uuid
import hashlib

import pytest
import requests
from pymongo import MongoClient
from dotenv import dotenv_values

from conftest import API, unique_email, unique_phone

LOCAL_API = "http://localhost:8001/api"  # app-level checks that the edge proxy masks

be_env = dotenv_values("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL") or be_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or be_env.get("DB_NAME")


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


# ---------------- module: public config ----------------
class TestPublicConfig:
    def test_public_config(self, client):
        r = client.get(f"{API}/public/config")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["trial_days"] == 10
        assert d["plan_price_inr"] == 999
        for k in ("whatsapp_number", "support_email", "play_store_url", "app_store_url"):
            assert k in d


# ---------------- module: auth / login ----------------
class TestLogin:
    def test_login_demo_by_email(self, client, creds):
        r = client.post(f"{API}/auth/login", json=creds["demo"])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"] == creds["demo"]["identifier"]
        assert d["user"]["role"] == "owner"
        assert d["user"]["organisation_id"]
        assert "password_hash" not in d["user"]
        assert "_id" not in d["user"]
        # httpOnly cookies set
        cookies = {c.name: c for c in client.cookies}
        assert "access_token" in cookies and "refresh_token" in cookies
        assert client.cookies.get_dict().get("access_token")

    def test_login_httponly_flag_present(self, client, creds):
        r = client.post(f"{API}/auth/login", json=creds["demo"])
        assert r.status_code == 200
        raw = r.headers.get("set-cookie", "") + str(r.raw.headers.getlist("Set-Cookie"))
        assert "HttpOnly" in raw, f"access/refresh cookies must be HttpOnly: {raw}"

    def test_login_demo_by_mobile(self, client):
        r = client.post(f"{API}/auth/login", json={"identifier": "9876500001", "password": "Demo@2026"})
        assert r.status_code == 200, r.text
        assert r.json()["user"]["phone"] == "+919876500001"

    def test_login_super_admin(self, client, creds):
        r = client.post(f"{API}/auth/login", json=creds["super_admin"])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["role"] == "super_admin"
        assert d["user"]["organisation_id"] is None

    def test_login_wrong_password(self, client, creds):
        r = client.post(f"{API}/auth/login", json={"identifier": creds["demo"]["identifier"], "password": "WrongPass@999"})
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_login_unknown_user(self, client):
        r = client.post(f"{API}/auth/login", json={"identifier": "nobody_qa@nowhere.in", "password": "Whatever@123"})
        assert r.status_code == 401


# ---------------- module: auth / me + protected routes ----------------
class TestMeAndProtection:
    def test_me_requires_auth(self, client):
        r = client.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_returns_org_outlets_subscription(self, demo_client):
        r = demo_client.get(f"{API}/auth/me")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["organisation"]["name"] == "Iron Paradise Fitness"
        names = sorted(o["name"] for o in d["outlets"])
        assert names == ["HSR Layout", "Indiranagar"], names
        assert all("_id" not in o for o in d["outlets"])
        sub = d["subscription"]
        assert sub["status"] == "trial"
        assert sub["plan_price_inr"] == 999
        assert 0 < sub["trial_days_left"] <= 10

    def test_dashboard_requires_auth(self, client):
        assert client.get(f"{API}/dashboard/summary").status_code == 401
        assert client.get(f"{API}/dashboard/recent-transactions").status_code == 401
        assert client.get(f"{API}/outlets").status_code == 401

    def test_super_admin_blocked_from_org_endpoints(self, client, creds):
        r = client.post(f"{API}/auth/login", json=creds["super_admin"])
        assert r.status_code == 200
        assert client.get(f"{API}/dashboard/summary").status_code == 403
        assert client.get(f"{API}/outlets").status_code == 403

    def test_refresh_and_logout(self, demo_client):
        r = demo_client.post(f"{API}/auth/refresh")
        assert r.status_code == 200, r.text
        assert demo_client.get(f"{API}/auth/me").status_code == 200
        r = demo_client.post(f"{API}/auth/logout")
        assert r.status_code == 200
        s = requests.Session()
        assert s.post(f"{API}/auth/refresh").status_code == 401

    def test_invalid_token_rejected(self, client):
        r = client.get(f"{API}/auth/me", headers={"Authorization": "Bearer not.a.token"})
        assert r.status_code == 401


# ---------------- module: dashboard ----------------
class TestDashboard:
    def test_summary_shape_and_values(self, demo_client):
        r = demo_client.get(f"{API}/dashboard/summary")
        assert r.status_code == 200, r.text
        d = r.json()
        expected = ["today_collection", "today_online", "today_cash", "today_admissions", "today_renewals",
                    "due_paid_today", "today_enquiries", "active_members", "total_members", "due_members",
                    "expiring_today", "expiring_1_3_days", "birthdays_today", "attendance_today"]
        for k in expected:
            assert k in d, f"missing {k}"
            assert isinstance(d[k], (int, float)), k
        assert d["total_members"] == 26, d["total_members"]
        # attendance_today depends on seed date (seed inserts 12 check-ins for the seed day only),
        # so assert a stable invariant instead of the stale hardcoded 12.
        assert 0 <= d["attendance_today"] <= d["total_members"], d["attendance_today"]
        assert d["today_collection"] == d["today_cash"] + d["today_online"]
        assert d["active_members"] <= d["total_members"]

    def test_summary_outlet_filter(self, demo_client):
        outlets = demo_client.get(f"{API}/outlets").json()
        total = demo_client.get(f"{API}/dashboard/summary").json()["total_members"]
        per = {}
        for o in outlets:
            r = demo_client.get(f"{API}/dashboard/summary", params={"outlet_id": o["id"]})
            assert r.status_code == 200, r.text
            per[o["name"]] = r.json()["total_members"]
        assert sum(per.values()) == total, per
        assert all(v > 0 for v in per.values()), per

    def test_summary_bogus_outlet_returns_zeros(self, demo_client):
        r = demo_client.get(f"{API}/dashboard/summary", params={"outlet_id": str(uuid.uuid4())})
        assert r.status_code == 200, r.text
        assert r.json()["total_members"] == 0

    def test_recent_transactions(self, demo_client):
        r = demo_client.get(f"{API}/dashboard/recent-transactions")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list) and len(rows) > 0
        assert len(rows) <= 10
        row = rows[0]
        for k in ("member_name", "amount", "method", "type", "receipt_no", "created_at"):
            assert k in row, f"missing {k}"
        assert "_id" not in row


# ---------------- module: onboarding ----------------
class TestOnboarding:
    def test_get_onboarding(self, demo_client):
        r = demo_client.get(f"{API}/onboarding")
        assert r.status_code == 200, r.text
        assert set(["plan", "member", "staff", "payment", "dismissed"]).issubset(r.json().keys())

    def test_dismiss_persists_and_restore(self, demo_client):
        r = demo_client.put(f"{API}/onboarding", json={"dismissed": True})
        assert r.status_code == 200, r.text
        assert r.json()["dismissed"] is True
        assert demo_client.get(f"{API}/onboarding").json()["dismissed"] is True
        # restore seeded state
        r = demo_client.put(f"{API}/onboarding", json={"dismissed": False})
        assert r.json()["dismissed"] is False

    def test_unknown_keys_ignored(self, demo_client):
        r = demo_client.put(f"{API}/onboarding", json={"hacker": True})
        assert r.status_code == 200, r.text
        assert "hacker" not in r.json()


# ---------------- module: registration + tenant isolation ----------------
class TestRegistrationAndIsolation:
    created = []

    def test_register_creates_isolated_tenant(self, client, mongo):
        email = unique_email()
        payload = {
            "full_name": "TEST QA Owner",
            "email": email,
            "phone": unique_phone(),
            "password": "Test@12345",
            "gym_name": "TEST_QA Gym",
            "outlet_name": "TEST_QA Outlet",
            "city": "Pune",
        }
        r = client.post(f"{API}/auth/register", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"] == email
        assert d["user"]["role"] == "owner"
        assert d["organisation"]["name"] == "TEST_QA Gym"
        TestRegistrationAndIsolation.created.append(d["organisation"]["id"])

        # cookies set → session usable immediately
        me = client.get(f"{API}/auth/me")
        assert me.status_code == 200, me.text
        m = me.json()
        assert m["subscription"]["status"] == "trial"
        assert m["subscription"]["trial_days_left"] == 10
        assert len(m["outlets"]) == 1 and m["outlets"][0]["name"] == "TEST_QA Outlet"
        ob = m["organisation"]["onboarding"]
        assert ob == {"plan": False, "member": False, "staff": False, "payment": False, "dismissed": False}

        # tenant isolation: fresh gym sees zeros
        s = client.get(f"{API}/dashboard/summary")
        assert s.status_code == 200, s.text
        sd = s.json()
        assert sd["total_members"] == 0 and sd["today_collection"] == 0 and sd["active_members"] == 0
        assert client.get(f"{API}/dashboard/recent-transactions").json() == []

        # bcrypt hash format
        u = mongo.users.find_one({"email": email})
        assert u["password_hash"].startswith("$2b$"), u["password_hash"][:10]
        assert u["phone"] == "+91" + payload["phone"]

    def test_register_duplicate_email(self, client):
        email = unique_email()
        base = {
            "full_name": "TEST Dup", "email": email, "phone": unique_phone(),
            "password": "Test@12345", "gym_name": "TEST_Dup Gym", "outlet_name": "Main",
        }
        r1 = client.post(f"{API}/auth/register", json=base)
        assert r1.status_code == 200, r1.text
        TestRegistrationAndIsolation.created.append(r1.json()["organisation"]["id"])
        base["phone"] = unique_phone()
        r2 = requests.post(f"{API}/auth/register", json=base)
        assert r2.status_code == 409, r2.text

    @pytest.mark.parametrize("field,value,label", [
        ("email", "not-an-email", "bad email"),
        ("password", "short", "short password"),
        ("phone", "12345", "short phone"),
        ("full_name", "A", "short name"),
    ])
    def test_register_validation(self, client, field, value, label):
        payload = {
            "full_name": "TEST Valid", "email": unique_email(), "phone": unique_phone(),
            "password": "Test@12345", "gym_name": "TEST_V Gym", "outlet_name": "Main",
        }
        payload[field] = value
        r = client.post(f"{API}/auth/register", json=payload)
        assert r.status_code == 422, f"{label} should 422, got {r.status_code}"

    def test_register_11_digit_phone_normalised(self, client):
        payload = {
            "full_name": "TEST Norm", "email": unique_email(), "phone": "+91" + unique_phone(),
            "password": "Test@12345", "gym_name": "TEST_Norm Gym", "outlet_name": "Main",
        }
        r = client.post(f"{API}/auth/register", json=payload)
        assert r.status_code == 200, r.text
        TestRegistrationAndIsolation.created.append(r.json()["organisation"]["id"])
        assert r.json()["user"]["phone"] == "+91" + payload["phone"][3:]

    @classmethod
    def teardown_class(cls):
        c = MongoClient(MONGO_URL)
        db = c[DB_NAME]
        for org_id in cls.created:
            db.users.delete_many({"organisation_id": org_id})
            db.outlets.delete_many({"organisation_id": org_id})
            db.organisations.delete_many({"id": org_id})
            db.audit_logs.delete_many({"target": org_id})
        c.close()


# ---------------- module: forgot / reset password ----------------
class TestPasswordReset:
    def test_forgot_password_generic_for_known_and_unknown(self, client, creds):
        r1 = client.post(f"{API}/auth/forgot-password", json={"email": creds["demo"]["identifier"]})
        r2 = client.post(f"{API}/auth/forgot-password", json={"email": f"no_such_{uuid.uuid4().hex[:8]}@nowhere.in"})
        assert r1.status_code == r2.status_code == 200
        assert r1.json() == r2.json(), (r1.json(), r2.json())

    def test_forgot_password_bad_email_422(self, client):
        assert client.post(f"{API}/auth/forgot-password", json={"email": "bad"}).status_code == 422

    def test_reset_token_stored_hashed_and_full_flow(self, client, mongo):
        # create a throwaway account
        email = unique_email("TEST_reset")
        payload = {"full_name": "TEST Reset", "email": email, "phone": unique_phone(),
                   "password": "Test@12345", "gym_name": "TEST_Reset Gym", "outlet_name": "Main"}
        reg = client.post(f"{API}/auth/register", json=payload)
        assert reg.status_code == 200, reg.text
        org_id = reg.json()["organisation"]["id"]
        user_id = reg.json()["user"]["id"]
        try:
            # trigger brute-force lockout first (5 fails) - app level (localhost) since the
            # public ingress rotates request.client.host across pods
            s = requests.Session()
            for _ in range(6):
                s.post(f"{LOCAL_API}/auth/login", json={"identifier": email, "password": "Bad@12345678"})
            locked = s.post(f"{LOCAL_API}/auth/login", json={"identifier": email, "password": "Bad@12345678"})
            assert locked.status_code == 429, f"expected lockout after 5 fails, got {locked.status_code}"

            fresh = requests.Session()
            fp = fresh.post(f"{API}/auth/forgot-password", json={"email": email})
            assert fp.status_code == 200
            time.sleep(1)
            docs = list(mongo.password_reset_tokens.find({"email": email}))
            assert len(docs) == 1, docs
            doc = docs[0]
            assert "token" not in doc and "token_hash" in doc
            assert re.fullmatch(r"[0-9a-f]{64}", doc["token_hash"]), doc["token_hash"]
            assert doc["used"] is False

            # invalid token rejected
            bad = fresh.post(f"{API}/auth/reset-password", json={"token": "garbage", "password": "New@123456"})
            assert bad.status_code == 400

            # we can't read the raw token (correct behaviour) → inject a known one
            raw = "qa-known-token-" + uuid.uuid4().hex
            mongo.password_reset_tokens.update_one(
                {"_id": doc["_id"]}, {"$set": {"token_hash": hashlib.sha256(raw.encode()).hexdigest()}})
            rp = fresh.post(f"{API}/auth/reset-password", json={"token": raw, "password": "NewPass@2026"})
            assert rp.status_code == 200, rp.text

            # token single use
            again = fresh.post(f"{API}/auth/reset-password", json={"token": raw, "password": "NewPass@2027"})
            assert again.status_code == 400

            # login with new password works AND lockout was cleared
            li = requests.Session().post(f"{LOCAL_API}/auth/login", json={"identifier": email, "password": "NewPass@2026"})
            assert li.status_code == 200, f"post-reset login should clear lockout: {li.status_code} {li.text[:200]}"

            # old password rejected
            old = requests.Session().post(f"{API}/auth/login", json={"identifier": email, "password": "Test@12345"})
            assert old.status_code == 401

            # old session invalidated (token_version bumped)
            assert client.get(f"{API}/auth/me").status_code == 401
        finally:
            mongo.users.delete_many({"id": user_id})
            mongo.outlets.delete_many({"organisation_id": org_id})
            mongo.organisations.delete_many({"id": org_id})
            mongo.password_reset_tokens.delete_many({"email": email})
            mongo.login_attempts.delete_many({"email": email})


# ---------------- module: brute force protection ----------------
class TestBruteForce:
    def test_lockout_app_level(self, mongo):
        ident = f"bf_app_{uuid.uuid4().hex[:8]}@nowhere.in"
        s = requests.Session()
        codes = [s.post(f"{LOCAL_API}/auth/login", json={"identifier": ident, "password": "Bad@12345"}).status_code
                 for _ in range(8)]
        mongo.login_attempts.delete_many({"email": ident})
        assert 429 in codes, f"no lockout observed: {codes}"
        assert codes[:5] == [401] * 5, codes

    def test_lockout_via_public_ingress(self, mongo):
        """Real user path: lockout must also work through the public URL."""
        ident = f"bf_pub_{uuid.uuid4().hex[:8]}@nowhere.in"
        s = requests.Session()
        codes = [s.post(f"{API}/auth/login", json={"identifier": ident, "password": "Bad@12345"}).status_code
                 for _ in range(9)]
        keys = sorted({d["identifier"] for d in mongo.login_attempts.find({"email": ident})})
        mongo.login_attempts.delete_many({"email": ident})
        assert 429 in codes, (
            f"Brute-force lockout never triggers through the public ingress: {codes}. "
            f"request.client.host resolves to rotating proxy pod IPs, splitting the counter: {keys}"
        )


# ---------------- module: CORS ----------------
class TestCors:
    def test_cors_allows_credentials_with_explicit_origin(self):
        """App-level CORS config (edge proxy rewrites preflight headers, so assert on the app)."""
        origin = (os.environ.get("REACT_APP_BACKEND_URL")
                  or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
        r = requests.options(f"{LOCAL_API}/auth/login", headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        assert r.status_code in (200, 204), r.status_code
        assert r.headers.get("access-control-allow-credentials") == "true"
        allow = r.headers.get("access-control-allow-origin")
        assert allow == origin, f"expected explicit origin, got {allow}"
