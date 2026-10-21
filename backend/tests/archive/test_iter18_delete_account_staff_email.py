# Iteration 18: POST /api/auth/delete-account + PUT /api/staff/{id} login email/password changes
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

from conftest import API, unique_email, unique_phone

PW = "QaStart@2026"
STAFF_PW = "StaffPw@2026"
benv = dotenv_values("/app/backend/.env")
mongo = MongoClient(benv["MONGO_URL"])[benv["DB_NAME"]]


def register(prefix="test_iter18"):
    s = requests.Session()
    email = unique_email(prefix)
    r = s.post(f"{API}/auth/register", json={
        "full_name": "TEST Iter18", "email": email, "phone": unique_phone(), "password": PW,
        "gym_name": "TEST Iter18 Gym", "outlet_name": "Main",
    })
    assert r.status_code == 200, r.text
    me = s.get(f"{API}/auth/me").json()
    return s, email, me


def login(email, pw):
    return requests.post(f"{API}/auth/login", json={"identifier": email, "password": pw})


def create_staff(s, email=None, password=None, role="trainer"):
    body = {"name": "TEST Staff", "role": role, "phone": unique_phone(), "permission": "manage"}
    if email:
        body["email"] = email
    if password:
        body["password"] = password
    r = s.post(f"{API}/staff", json=body)
    assert r.status_code == 200, r.text
    return r.json(), body


def org_id_of(me):
    return me.get("organisation_id") or (me.get("user") or {}).get("organisation_id")


# ---- delete-account validation
class TestDeleteAccountValidation:
    def test_confirm_not_delete_400(self):
        s, _, _ = register()
        r = s.post(f"{API}/auth/delete-account", json={"password": PW, "confirm": "delete"})
        assert r.status_code == 400
        assert "DELETE" in r.json()["detail"]

    def test_wrong_password_400(self):
        s, email, _ = register()
        r = s.post(f"{API}/auth/delete-account", json={"password": "wrongpw123", "confirm": "DELETE"})
        assert r.status_code == 400
        assert "incorrect" in r.json()["detail"].lower()
        assert login(email, PW).status_code == 200

    def test_unauthenticated_401(self):
        r = requests.post(f"{API}/auth/delete-account", json={"password": PW, "confirm": "DELETE"})
        assert r.status_code == 401

    def test_demo_owner_403(self, demo_client, creds):
        r = demo_client.post(f"{API}/auth/delete-account", json={"password": creds["demo"]["password"], "confirm": "DELETE"})
        assert r.status_code == 403
        assert login(creds["demo"]["identifier"], creds["demo"]["password"]).status_code == 200

    def test_super_admin_403(self, client, creds):
        assert client.post(f"{API}/auth/login", json=creds["super_admin"]).status_code == 200
        r = client.post(f"{API}/auth/delete-account", json={"password": creds["super_admin"]["password"], "confirm": "DELETE"})
        assert r.status_code == 403


# ---- delete-account success paths
class TestDeleteAccountSuccess:
    def test_staff_self_delete(self):
        owner, _, _ = register()
        semail = unique_email("test_iter18_staff")
        staff, _ = create_staff(owner, semail, STAFF_PW)
        ss = requests.Session()
        assert ss.post(f"{API}/auth/login", json={"identifier": semail, "password": STAFF_PW}).status_code == 200
        r = ss.post(f"{API}/auth/delete-account", json={"password": STAFF_PW, "confirm": "DELETE"})
        assert r.status_code == 200, r.text
        assert "login" in r.json()["message"].lower()
        assert login(semail, STAFF_PW).status_code == 401
        rows = owner.get(f"{API}/staff").json()
        row = next(x for x in rows if x["id"] == staff["id"])
        assert row["has_login"] is False
        assert row.get("user_id") is None
        assert owner.get(f"{API}/auth/me").status_code == 200

    def test_owner_delete_wipes_org(self):
        s, email, me = register()
        org_id = org_id_of(me)
        assert org_id
        create_staff(s, unique_email("test_iter18_os"), STAFF_PW)
        plans = s.get(f"{API}/plans")
        assert mongo.outlets.count_documents({"organisation_id": org_id}) >= 1
        r = s.post(f"{API}/auth/delete-account", json={"password": PW, "confirm": "  DELETE  "})
        assert r.status_code == 200, r.text
        set_cookie = r.headers.get("set-cookie", "")
        assert "access_token" in set_cookie
        assert login(email, PW).status_code == 401
        assert mongo.organisations.count_documents({"id": org_id}) == 0
        for coll in ["users", "members", "payments", "outlets", "plans", "staff", "attendance", "enquiries", "expenses"]:
            assert mongo[coll].count_documents({"organisation_id": org_id}) == 0, coll
        assert requests.get(f"{API}/auth/me", cookies=s.cookies).status_code == 401


# ---- staff login email change
class TestStaffEmailChange:
    def test_change_email_updates_login(self):
        owner, _, _ = register()
        old = unique_email("test_iter18_old")
        new = unique_email("test_iter18_new")
        staff, body = create_staff(owner, old, STAFF_PW)
        body.pop("password")
        body["email"] = new.upper()
        r = owner.put(f"{API}/staff/{staff['id']}", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["email"] == new
        assert login(old, STAFF_PW).status_code == 401
        assert login(new, STAFF_PW).status_code == 200

    def test_existing_session_invalidated_on_email_change(self):
        owner, _, _ = register()
        old = unique_email("test_iter18_sess")
        staff, body = create_staff(owner, old, STAFF_PW)
        ss = requests.Session()
        assert ss.post(f"{API}/auth/login", json={"identifier": old, "password": STAFF_PW}).status_code == 200
        body.pop("password")
        body["email"] = unique_email("test_iter18_sess2")
        assert owner.put(f"{API}/staff/{staff['id']}", json=body).status_code == 200
        assert ss.get(f"{API}/auth/me").status_code == 401

    def test_duplicate_email_409(self):
        owner, owner_email, _ = register()
        staff, body = create_staff(owner, unique_email("test_iter18_dup"), STAFF_PW)
        body.pop("password")
        body["email"] = owner_email
        r = owner.put(f"{API}/staff/{staff['id']}", json=body)
        assert r.status_code == 409

    def test_new_password_sets_password(self):
        owner, _, _ = register()
        em = unique_email("test_iter18_pw")
        staff, body = create_staff(owner, em, STAFF_PW)
        body["password"] = "BrandNew@2026"
        assert owner.put(f"{API}/staff/{staff['id']}", json=body).status_code == 200
        assert login(em, STAFF_PW).status_code == 401
        assert login(em, "BrandNew@2026").status_code == 200

    def test_short_password_422(self):
        owner, _, _ = register()
        staff, body = create_staff(owner, unique_email("test_iter18_spw"), STAFF_PW)
        body["password"] = "short"
        assert owner.put(f"{API}/staff/{staff['id']}", json=body).status_code == 422

    def test_remove_email_from_login_staff_422(self):
        owner, _, _ = register()
        staff, body = create_staff(owner, unique_email("test_iter18_rm"), STAFF_PW)
        body.pop("password")
        body["email"] = ""
        assert owner.put(f"{API}/staff/{staff['id']}", json=body).status_code == 422

    def test_password_on_no_login_staff_creates_login(self):
        owner, _, _ = register()
        staff, body = create_staff(owner)
        assert staff["has_login"] is False
        em = unique_email("test_iter18_nl")
        body["email"] = em
        body["password"] = "FreshLogin@2026"
        r = owner.put(f"{API}/staff/{staff['id']}", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["has_login"] is True
        assert login(em, "FreshLogin@2026").status_code == 200

    def test_no_login_staff_email_only_no_login(self):
        owner, _, _ = register()
        staff, body = create_staff(owner)
        body["email"] = unique_email("test_iter18_eo")
        r = owner.put(f"{API}/staff/{staff['id']}", json=body)
        assert r.status_code == 200
        assert r.json()["has_login"] is False

    def test_manager_can_reset_admin_password(self):
        """Security probe: a 'manager' staff can change an 'admin' staff's email/password (privilege escalation)."""
        owner, _, _ = register()
        mgr_email = unique_email("test_iter18_mgr")
        create_staff(owner, mgr_email, STAFF_PW, role="manager")
        admin, abody = create_staff(owner, unique_email("test_iter18_adm"), STAFF_PW, role="admin")
        ms = requests.Session()
        assert ms.post(f"{API}/auth/login", json={"identifier": mgr_email, "password": STAFF_PW}).status_code == 200
        abody["password"] = "Hijack@2026"
        r = ms.put(f"{API}/staff/{admin['id']}", json=abody)
        print("manager->admin password reset status", r.status_code)
        assert r.status_code == 403, "manager could reset admin's login password"
