# Iteration 19: retest privilege-escalation fixes on PUT /api/staff/{id}, delete-account owner check + 429 lockout, demo trial
from datetime import datetime, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

from conftest import API, unique_email, unique_phone

PW = "QaStart@2026"
STAFF_PW = "StaffPw@2026"
benv = dotenv_values("/app/backend/.env")
mongo = MongoClient(benv["MONGO_URL"])[benv["DB_NAME"]]


def register(prefix="test_iter19"):
    s = requests.Session()
    email = unique_email(prefix)
    r = s.post(f"{API}/auth/register", json={
        "full_name": "TEST Iter19", "email": email, "phone": unique_phone(), "password": PW,
        "gym_name": "TEST Iter19 Gym", "outlet_name": "Main",
    })
    assert r.status_code == 200, r.text
    me = s.get(f"{API}/auth/me").json()
    return s, email, me


def login(email, pw):
    return requests.post(f"{API}/auth/login", json={"identifier": email, "password": pw})


def session_for(email, pw):
    s = requests.Session()
    assert s.post(f"{API}/auth/login", json={"identifier": email, "password": pw}).status_code == 200
    return s


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


# ---- role validation on update
class TestRoleValidation:
    @pytest.mark.parametrize("bad", ["owner", "OWNER", "super_admin", "god"])
    def test_owner_put_invalid_role_422(self, bad):
        owner, _, _ = register()
        staff, body = create_staff(owner, unique_email("test_iter19_r"), STAFF_PW)
        body.pop("password")
        body["role"] = bad
        r = owner.put(f"{API}/staff/{staff['id']}", json=body)
        assert r.status_code == 422, r.text
        u = mongo.users.find_one({"staff_id": staff["id"]})
        assert u["role"] == "trainer"

    def test_manager_self_role_owner_blocked(self):
        owner, _, me = register()
        org_id = org_id_of(me)
        mgr_email = unique_email("test_iter19_mgr")
        mgr, mbody = create_staff(owner, mgr_email, STAFF_PW, role="manager")
        ms = session_for(mgr_email, STAFF_PW)
        mbody.pop("password")
        mbody["role"] = "owner"
        r = ms.put(f"{API}/staff/{mgr['id']}", json=mbody)
        assert r.status_code in (403, 422), r.text
        # delete-account by manager must never wipe org
        r = ms.post(f"{API}/auth/delete-account", json={"password": STAFF_PW, "confirm": "DELETE"})
        assert r.status_code == 200
        assert "login" in r.json()["message"].lower()
        assert mongo.organisations.count_documents({"id": org_id}) == 1
        assert owner.get(f"{API}/auth/me").status_code == 200

    def test_staff_cannot_change_own_role(self):
        owner, _, _ = register()
        em = unique_email("test_iter19_self")
        st, body = create_staff(owner, em, STAFF_PW, role="manager")
        ss = session_for(em, STAFF_PW)
        body.pop("password")
        body["role"] = "admin"
        r = ss.put(f"{API}/staff/{st['id']}", json=body)
        assert r.status_code == 403, r.text
        assert mongo.users.find_one({"staff_id": st["id"]})["role"] == "manager"

    def test_owner_can_change_role_valid(self):
        owner, _, _ = register()
        st, body = create_staff(owner, unique_email("test_iter19_ok"), STAFF_PW)
        body.pop("password")
        body["role"] = "Receptionist"
        r = owner.put(f"{API}/staff/{st['id']}", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "receptionist"


# ---- credential changes restricted to owner
class TestCredentialChangeOwnerOnly:
    @pytest.mark.parametrize("actor_role", ["manager", "admin"])
    def test_non_owner_cannot_change_other_password(self, actor_role):
        owner, _, _ = register()
        a_email = unique_email("test_iter19_act")
        create_staff(owner, a_email, STAFF_PW, role=actor_role)
        tgt_email = unique_email("test_iter19_tgt")
        tgt, tbody = create_staff(owner, tgt_email, STAFF_PW, role="admin")
        a = session_for(a_email, STAFF_PW)
        tbody["password"] = "Hijack@2026"
        r = a.put(f"{API}/staff/{tgt['id']}", json=tbody)
        assert r.status_code == 403, r.text
        assert login(tgt_email, "Hijack@2026").status_code == 401
        assert login(tgt_email, STAFF_PW).status_code == 200

    @pytest.mark.parametrize("actor_role", ["manager", "admin"])
    def test_non_owner_cannot_change_other_email(self, actor_role):
        owner, _, _ = register()
        a_email = unique_email("test_iter19_act")
        create_staff(owner, a_email, STAFF_PW, role=actor_role)
        tgt_email = unique_email("test_iter19_tgt")
        tgt, tbody = create_staff(owner, tgt_email, STAFF_PW, role="trainer")
        a = session_for(a_email, STAFF_PW)
        tbody.pop("password")
        tbody["email"] = unique_email("test_iter19_hij")
        r = a.put(f"{API}/staff/{tgt['id']}", json=tbody)
        assert r.status_code == 403, r.text
        assert login(tgt_email, STAFF_PW).status_code == 200

    def test_manager_can_edit_non_credential_fields(self):
        owner, _, _ = register()
        a_email = unique_email("test_iter19_mgr2")
        create_staff(owner, a_email, STAFF_PW, role="manager")
        tgt, tbody = create_staff(owner, unique_email("test_iter19_t2"), STAFF_PW)
        a = session_for(a_email, STAFF_PW)
        tbody.pop("password")
        tbody["name"] = "TEST Renamed"
        r = a.put(f"{API}/staff/{tgt['id']}", json=tbody)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "TEST Renamed"

    def test_owner_changes_admin_email_and_password(self):
        owner, _, _ = register()
        old = unique_email("test_iter19_adm")
        new = unique_email("test_iter19_admnew")
        st, body = create_staff(owner, old, STAFF_PW, role="admin")
        body["email"] = new
        body["password"] = "NewAdmin@2026"
        r = owner.put(f"{API}/staff/{st['id']}", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["email"] == new
        assert login(old, STAFF_PW).status_code == 401
        assert login(new, STAFF_PW).status_code == 401
        assert login(new, "NewAdmin@2026").status_code == 200


# ---- delete-account owner check + lockout
class TestDeleteAccountHardening:
    def test_lockout_after_5_wrong(self):
        s, email, me = register()
        org_id = org_id_of(me)
        for i in range(5):
            r = s.post(f"{API}/auth/delete-account", json={"password": f"wrong{i}xxxx", "confirm": "DELETE"})
            assert r.status_code == 400, (i, r.text)
        r = s.post(f"{API}/auth/delete-account", json={"password": "wrongagain", "confirm": "DELETE"})
        assert r.status_code == 429, r.text
        # even correct password locked out
        r = s.post(f"{API}/auth/delete-account", json={"password": PW, "confirm": "DELETE"})
        assert r.status_code == 429
        assert mongo.organisations.count_documents({"id": org_id}) == 1
        # cleanup the lock, then delete the throwaway tenant
        uid = me.get("id") or (me.get("user") or {}).get("id")
        mongo.login_attempts.delete_many({"identifier": f"delacct:{uid}"})
        assert s.post(f"{API}/auth/delete-account", json={"password": PW, "confirm": "DELETE"}).status_code == 200

    def test_owner_role_staff_record_injected_no_wipe(self):
        """Even if a staff user's role is forced to 'owner' in DB, delete-account must not wipe the org."""
        owner, _, me = register()
        org_id = org_id_of(me)
        em = unique_email("test_iter19_inj")
        st, _ = create_staff(owner, em, STAFF_PW, role="manager")
        mongo.users.update_one({"staff_id": st["id"]}, {"$set": {"role": "owner"}})
        ss = session_for(em, STAFF_PW)
        r = ss.post(f"{API}/auth/delete-account", json={"password": STAFF_PW, "confirm": "DELETE"})
        assert r.status_code == 200, r.text
        assert mongo.organisations.count_documents({"id": org_id}) == 1
        assert owner.get(f"{API}/auth/me").status_code == 200

    def test_true_owner_wipes_org(self):
        s, email, me = register()
        org_id = org_id_of(me)
        r = s.post(f"{API}/auth/delete-account", json={"password": PW, "confirm": "DELETE"})
        assert r.status_code == 200
        assert mongo.organisations.count_documents({"id": org_id}) == 0
        assert mongo.users.count_documents({"organisation_id": org_id}) == 0


# ---- demo trial refresh
def test_demo_trial_at_least_3_days(creds):
    s = requests.Session()
    assert s.post(f"{API}/auth/login", json=creds["demo"]).status_code == 200
    org = mongo.organisations.find_one({"is_demo": True})
    ends = org["subscription"]["trial_ends_at"]
    if ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    days = (ends - datetime.now(timezone.utc)).total_seconds() / 86400
    print("demo trial days left", days)
    assert days >= 3
