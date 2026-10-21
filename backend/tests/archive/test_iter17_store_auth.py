# Iteration 17: change-password, forgot-password, login, assetlinks, legal routes
import os
from datetime import timedelta, datetime, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

from conftest import API, BASE_URL, unique_email, unique_phone

PW = "QaStart@2026"
NEW_PW = "QaNewPw@2026"
benv = dotenv_values("/app/backend/.env")
mongo = MongoClient(benv["MONGO_URL"])[benv["DB_NAME"]]


def register(prefix="test_iter17"):
    s = requests.Session()
    email = unique_email(prefix)
    r = s.post(f"{API}/auth/register", json={
        "full_name": "TEST Iter17", "email": email, "phone": unique_phone(), "password": PW,
        "gym_name": "TEST Iter17 Gym", "outlet_name": "Main",
    })
    assert r.status_code == 200, r.text
    return s, email, r.json()


# ---- change-password core flow
class TestChangePassword:
    def test_wrong_current_400(self):
        s, _, _ = register()
        r = s.post(f"{API}/auth/change-password", json={"current_password": "nope12345", "new_password": NEW_PW})
        assert r.status_code == 400
        assert "incorrect" in r.json()["detail"].lower()

    def test_same_new_400(self):
        s, _, _ = register()
        r = s.post(f"{API}/auth/change-password", json={"current_password": PW, "new_password": PW})
        assert r.status_code == 400
        assert "different" in r.json()["detail"].lower()

    def test_short_new_422(self):
        s, _, _ = register()
        r = s.post(f"{API}/auth/change-password", json={"current_password": PW, "new_password": "short"})
        assert r.status_code == 422

    def test_unauthenticated_401(self):
        r = requests.post(f"{API}/auth/change-password", json={"current_password": PW, "new_password": NEW_PW})
        assert r.status_code == 401

    def test_valid_flow_sessions(self):
        s, email, _ = register()
        # second "device"
        other = requests.Session()
        assert other.post(f"{API}/auth/login", json={"identifier": email, "password": PW}).status_code == 200
        old_cookies = {c.name: c.value for c in s.cookies}
        r = s.post(f"{API}/auth/change-password", json={"current_password": PW, "new_password": NEW_PW})
        assert r.status_code == 200, r.text
        assert "signed out" in r.json()["message"].lower()
        # current session re-issued cookies still work
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200 and me.json()["user"]["email"] == email
        # old cookies invalid
        assert requests.get(f"{API}/auth/me", cookies=old_cookies).status_code == 401
        assert other.get(f"{API}/auth/me").status_code == 401
        # old refresh token cannot refresh
        assert requests.post(f"{API}/auth/refresh", cookies={"refresh_token": old_cookies["refresh_token"]}).status_code == 401
        # login checks
        assert requests.post(f"{API}/auth/login", json={"identifier": email, "password": PW}).status_code == 401
        assert requests.post(f"{API}/auth/login", json={"identifier": email, "password": NEW_PW}).status_code == 200
        u = mongo.users.find_one({"email": email})
        assert u["password_hash"].startswith("$2b$")
        assert u["token_version"] == 1

    def test_lockout_429(self):
        s, _, _ = register()
        codes = [s.post(f"{API}/auth/change-password", json={"current_password": f"bad{i}xxxxx", "new_password": NEW_PW}).status_code for i in range(5)]
        assert codes == [400] * 5
        r = s.post(f"{API}/auth/change-password", json={"current_password": PW, "new_password": NEW_PW})
        assert r.status_code == 429

    def test_expired_trial_org(self):
        s, email, data = register()
        org_id = data["organisation"]["id"] if "id" in data["organisation"] else mongo.users.find_one({"email": email})["organisation_id"]
        past = datetime.now(timezone.utc) - timedelta(days=1)
        mongo.organisations.update_one({"id": org_id}, {"$set": {"subscription.trial_ends_at": past, "subscription.trial_started_at": past - timedelta(days=10)}})
        me = s.get(f"{API}/auth/me").json()
        print("expired sub:", me.get("subscription"))
        r = s.post(f"{API}/auth/change-password", json={"current_password": PW, "new_password": NEW_PW})
        assert r.status_code == 200, r.text


# ---- forgot / login
class TestForgotAndLogin:
    def test_forgot_generic(self):
        _, email, _ = register()
        r1 = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        r2 = requests.post(f"{API}/auth/forgot-password", json={"email": unique_email("nobody")})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json() == r2.json()
        tok = mongo.password_reset_tokens.find_one({"email": email})
        assert tok and len(tok["token_hash"]) == 64 and "token" not in tok

    def test_demo_login(self, creds):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=creds["demo"])
        assert r.status_code == 200
        sc = r.headers.get("set-cookie", "").lower()
        assert "httponly" in sc and "access_token" in sc
        assert s.get(f"{API}/auth/me").json()["user"]["role"] == "owner"


# ---- store readiness static
class TestStatic:
    def test_assetlinks(self):
        r = requests.get(f"{BASE_URL}/.well-known/assetlinks.json")
        assert r.status_code == 200
        print("content-type:", r.headers.get("content-type"))
        data = r.json()
        assert isinstance(data, list)
