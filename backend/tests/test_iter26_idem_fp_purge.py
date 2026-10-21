"""Iter26: idempotency body fingerprint, cancel_remote_subscription exception handling, resumable org purge, disabled org.
In-process against ISOLATED db gymboss_txn_tests. Run: pytest -n 0 tests/test_iter26_idem_fp_purge.py"""
import os
import sys
import uuid
import asyncio

os.environ["DB_NAME"] = "gymboss_txn_tests"
sys.path.insert(0, "/app/backend")

import pytest  # noqa: E402
import httpx  # noqa: E402

import deps  # noqa: E402
import server  # noqa: E402
import billing  # noqa: E402
from tests.test_iter25_txn_recovery import tenant, new_member, add_sub, PW, run, LOOP  # noqa: E402,F401

db = deps.db
assert db.name == "gymboss_txn_tests"


@pytest.fixture(scope="module", autouse=True)
def isolated_db():
    run(deps.client.drop_database("gymboss_txn_tests"))
    run(server.ensure_indexes())
    yield
    run(deps.client.drop_database("gymboss_txn_tests"))


def connect_err_rzp():
    calls = []

    async def rq(method, path, payload=None):
        calls.append((method, path))
        raise httpx.ConnectError("connection refused")
    rq.calls = calls
    return rq


# ---- Idempotency body fingerprint ----
def test_idem_key_different_body_422_same_body_replay():
    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id))["id"]
        k = f"fp-{uuid.uuid4()}"
        r1 = await c.post("/api/payments", json={"member_id": mid, "amount": 10}, headers={"Idempotency-Key": k})
        assert r1.status_code == 200, r1.text
        r2 = await c.post("/api/payments", json={"member_id": mid, "amount": 20}, headers={"Idempotency-Key": k})
        assert r2.status_code == 422, r2.text
        r3 = await c.post("/api/payments", json={"member_id": mid, "amount": 10}, headers={"Idempotency-Key": k})
        assert r3.status_code == 200, r3.text
        assert r3.json()["id"] == r1.json()["id"]
        assert await db.payments.count_documents({"member_id": mid}) == 1
        doc = await db.idempotency_keys.find_one({"organisation_id": org_id, "key": k})
        assert isinstance(doc.get("fp"), str) and len(doc["fp"]) == 64
        # member create: same key different body
        mk = f"mfp-{uuid.uuid4()}"
        r = await c.post("/api/members", json={"full_name": "TEST_FP A", "phone": "9876500001", "plan_id": plan_id}, headers={"Idempotency-Key": mk})
        assert r.status_code == 200, r.text
        r = await c.post("/api/members", json={"full_name": "TEST_FP B", "phone": "9876500002", "plan_id": plan_id}, headers={"Idempotency-Key": mk})
        assert r.status_code == 422, r.text
        # renew: same key different body
        rk = f"rfp-{uuid.uuid4()}"
        r = await c.post(f"/api/members/{mid}/renew", json={"plan_id": plan_id, "amount_paid": 0}, headers={"Idempotency-Key": rk})
        assert r.status_code == 200, r.text
        r = await c.post(f"/api/members/{mid}/renew", json={"plan_id": plan_id, "amount_paid": 50}, headers={"Idempotency-Key": rk})
        assert r.status_code == 422, r.text
        await c.aclose()
    run(go())


def test_idem_concurrent_different_bodies_same_key():
    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id))["id"]
        k = f"cfp-{uuid.uuid4()}"
        res = await asyncio.gather(*[c.post("/api/payments", json={"member_id": mid, "amount": a}, headers={"Idempotency-Key": k}) for a in (10, 20, 30)])
        codes = sorted(r.status_code for r in res)
        assert codes == [200, 422, 422], codes
        assert await db.payments.count_documents({"member_id": mid}) == 1
        await c.aclose()
    run(go())


# ---- cancel_remote_subscription catches arbitrary exceptions ----
def test_delete_account_connect_error_409(monkeypatch):
    async def go():
        c, org_id, plan_id = await tenant()
        await new_member(c, plan_id, paid=100)
        rzp = await add_sub(org_id)
        monkeypatch.setattr(server, "razorpay_request", connect_err_rzp())
        r = await c.post("/api/auth/delete-account", json={"password": PW, "confirm": "DELETE"})
        assert r.status_code == 409, r.text
        op = await db.razorpay_ops.find_one({"target": rzp})
        assert op["status"] == "failed" and op["attempts"] == 1 and op["last_error"]
        assert "connection refused" in op["last_error"]
        r = await c.post("/api/auth/delete-account", json={"password": PW, "confirm": "DELETE"})
        assert r.status_code == 409
        op = await db.razorpay_ops.find_one({"target": rzp})
        assert op["attempts"] == 2
        org = await db.organisations.find_one({"id": org_id})
        assert org and not org.get("deleting_at") and not org.get("disabled")
        assert await db.members.count_documents({"organisation_id": org_id}) == 1
        await c.aclose()
    run(go())


def test_autodebit_cancel_connect_error_503(monkeypatch):
    async def go():
        c, org_id, _ = await tenant()
        rzp = await add_sub(org_id)
        monkeypatch.setattr(billing, "razorpay_request", connect_err_rzp())
        r = await c.post("/api/subscription/autodebit/cancel")
        assert r.status_code == 503, r.text
        assert (await db.subscriptions.find_one({"razorpay_subscription_id": rzp}))["status"] == "active"
        op = await db.razorpay_ops.find_one({"target": rzp})
        assert op["status"] == "failed" and op["last_error"]
        await c.aclose()
    run(go())


# ---- Resumable purge ----
def test_resume_purges_finishes_partial_delete():
    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id, paid=300))["id"]
        await c.post("/api/payments", json={"member_id": mid, "amount": 50})
        await db.razorpay_ops.insert_one({"id": f"op-{uuid.uuid4()}", "organisation_id": org_id, "kind": "cancel_subscription", "status": "succeeded"})
        # other org must be untouched
        c2, org2, plan2 = await tenant()
        await new_member(c2, plan2, paid=100)
        before = {n: await db[n].count_documents({"organisation_id": org_id}) for n in await db.list_collection_names()}
        assert before["members"] >= 1 and before["payments"] >= 1 and before["users"] >= 1
        await db.organisations.update_one({"id": org_id}, {"$set": {"deleting_at": deps.now_utc(), "disabled": True}})
        # disabled org -> API rejected
        r = await c.get("/api/members")
        assert r.status_code == 403, r.text
        # partial purge
        await db.members.delete_many({"organisation_id": org_id})
        await db.payments.delete_many({"organisation_id": org_id})
        await server.resume_purges()
        for n in await db.list_collection_names():
            if n in ("razorpay_ops", "settings"):
                continue
            cnt = await db[n].count_documents({"$or": [{"organisation_id": org_id}, {"org_id": org_id}]})
            assert cnt == 0, f"{n} still has {cnt} docs for purged org"
        assert await db.organisations.count_documents({"id": org_id}) == 0
        assert await db.razorpay_ops.count_documents({"organisation_id": org_id}) >= 1
        assert await db.organisations.count_documents({"id": org2}) == 1
        assert await db.members.count_documents({"organisation_id": org2}) == 1
        # idempotent
        await server.purge_org(org_id)
        await server.resume_purges()
        await c.aclose()
        await c2.aclose()
    run(go())


def test_disabled_org_login_and_api_rejected():
    async def go():
        c, org_id, plan_id = await tenant()
        email = (await db.users.find_one({"organisation_id": org_id}))["email"]
        await db.organisations.update_one({"id": org_id}, {"$set": {"disabled": True}})
        r = await c.get("/api/plans")
        assert r.status_code == 403, r.text
        r = await c.post("/api/payments", json={"member_id": "x", "amount": 1})
        assert r.status_code == 403, r.text
        c2 = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app, raise_app_exceptions=False), base_url="https://test")
        r = await c2.post("/api/auth/login", json={"identifier": email, "password": PW})
        print("disabled-org login:", r.status_code, r.text[:200])
        assert r.status_code == 403, f"login for disabled org returned {r.status_code}"
        await c.aclose()
        await c2.aclose()
    run(go())
