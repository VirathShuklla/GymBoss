"""Iter25: in-process transactional atomicity / idempotency / concurrency / durable Razorpay cancellation tests.
Runs against an ISOLATED db (gymboss_txn_tests) on the replica set. Run with: pytest -n 0 tests/test_iter25_txn_recovery.py"""
import os
import sys
import json
import hmac
import uuid
import random
import asyncio
import hashlib
from datetime import timedelta, date

os.environ["DB_NAME"] = "gymboss_txn_tests"
import paths  # noqa: F401,E402  (adds backend/ to sys.path)

import pytest  # noqa: E402
import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import deps  # noqa: E402
import server  # noqa: E402
import billing  # noqa: E402
import billing_sync  # noqa: E402
import member_ledger  # noqa: E402

db = deps.db
assert db.name == "gymboss_txn_tests"
LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)
PW = "TxnTest@2026"
WH_SECRET = "whsec_txn_tests"


def run(coro):
    return LOOP.run_until_complete(coro)


@pytest.fixture(scope="module", autouse=True)
def isolated_db():
    run(deps.client.drop_database("gymboss_txn_tests"))
    run(server.ensure_indexes())
    run(db.settings.update_one({"id": "platform"}, {"$set": {"id": "platform", "razorpay_webhook_secret": WH_SECRET}}, upsert=True))
    yield
    deps.FAULTS.clear()
    run(deps.client.drop_database("gymboss_txn_tests"))


def phone():
    return "9" + "".join(random.choice("0123456789") for _ in range(9))


async def tenant():
    c = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app, raise_app_exceptions=False), base_url="https://test", timeout=120)
    email = f"txn_{uuid.uuid4().hex[:10]}@example.com"
    r = await c.post("/api/auth/register", json={"full_name": "Txn Owner", "email": email, "phone": phone(), "password": PW,
                                                 "gym_name": "Txn Gym", "outlet_name": "Main"})
    assert r.status_code == 200, r.text
    org_id = r.json()["organisation"]["id"]
    r = await c.post("/api/plans", json={"name": "Monthly", "type": "membership", "duration_type": "months", "duration": 1, "price": 1000})
    assert r.status_code == 200, r.text
    return c, org_id, r.json()["id"]


async def new_member(c, plan_id, paid=0, key=None):
    h = {"Idempotency-Key": key} if key else {}
    r = await c.post("/api/members", json={"full_name": "TEST_Txn Member", "phone": phone(), "plan_id": plan_id, "amount_paid": paid}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def state(member_id):
    m = await db.members.find_one({"id": member_id})
    inv = await db.member_invoices.find({"member_id": member_id}).to_list(None)
    pays = await db.payments.find({"member_id": member_id}).to_list(None)
    return m, inv, pays


async def assert_balance(member_id):
    m, inv, pays = await state(member_id)
    charged = round(sum(i["amount"] for i in inv if i.get("status") != "void"), 2)
    paid = round(sum(p["amount"] for p in pays), 2)
    assert m["due_amount"] == round(max(0, charged - paid), 2), (m["due_amount"], charged, paid)
    assert m.get("credit_balance", 0) == round(max(0, paid - charged), 2)
    return m, inv, pays


# ---------------- Fault injection: member create ----------------
def test_member_create_faults_rollback_then_retry():
    async def go():
        c, org_id, plan_id = await tenant()
        for cp in ("member.create.after_member", "member.create.after_invoice", "member.create.after_payment"):
            key, ph = f"k-{uuid.uuid4()}", phone()
            body = {"full_name": "TEST_Fault Member", "phone": ph, "plan_id": plan_id, "amount_paid": 400}
            deps.FAULTS.add(cp)
            r = await c.post("/api/members", json=body, headers={"Idempotency-Key": key})
            assert r.status_code == 500, (cp, r.status_code, r.text)
            assert await db.members.count_documents({"phone": f"+91{ph}"}) == 0, cp
            assert await db.idempotency_keys.count_documents({"key": key}) == 0, cp
            assert await db.member_invoices.count_documents({"organisation_id": org_id, "member_id": {"$nin": [m["id"] async for m in db.members.find({"organisation_id": org_id})]}}) == 0
            r = await c.post("/api/members", json=body, headers={"Idempotency-Key": key})
            assert r.status_code == 200, r.text
            mid = r.json()["id"]
            r2 = await c.post("/api/members", json=body, headers={"Idempotency-Key": key})
            assert r2.status_code == 200 and r2.json()["id"] == mid
            assert await db.members.count_documents({"phone": f"+91{ph}"}) == 1
            m, inv, pays = await assert_balance(mid)
            assert len(inv) == 1 and len(pays) == 1 and m["due_amount"] == 600, cp
        await c.aclose()
    run(go())


# ---------------- Fault injection: renew ----------------
def test_renew_faults_rollback_then_retry():
    async def go():
        c, org_id, plan_id = await tenant()
        mem = await new_member(c, plan_id, paid=1000)
        mid = mem["id"]
        for cp in ("renew.after_member", "renew.after_invoice", "renew.after_payment"):
            m0, inv0, pay0 = await state(mid)
            key = f"k-{uuid.uuid4()}"
            deps.FAULTS.add(cp)
            r = await c.post(f"/api/members/{mid}/renew", json={"plan_id": plan_id, "amount_paid": 400}, headers={"Idempotency-Key": key})
            assert r.status_code == 500, (cp, r.status_code)
            m1, inv1, pay1 = await state(mid)
            assert m1["membership_expiry"] == m0["membership_expiry"] and len(inv1) == len(inv0) and len(pay1) == len(pay0), cp
            assert m1["due_amount"] == m0["due_amount"]
            for _ in range(2):
                r = await c.post(f"/api/members/{mid}/renew", json={"plan_id": plan_id, "amount_paid": 400}, headers={"Idempotency-Key": key})
                assert r.status_code == 200, r.text
            m2, inv2, pay2 = await assert_balance(mid)
            assert len(inv2) == len(inv0) + 1 and len(pay2) == len(pay0) + 1, cp
            exp0 = date.fromisoformat(str(m0["membership_expiry"])[:10])
            assert m2["membership_expiry"] == deps.add_duration(max(exp0, deps.today_ist()), "months", 1).isoformat()
            assert m2["due_amount"] == m0["due_amount"] + 600
        await c.aclose()
    run(go())


# ---------------- Fault injection: payment record / edit / reverse ----------------
def test_payment_record_edit_reverse_faults():
    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id, paid=0))["id"]
        # record
        key = f"k-{uuid.uuid4()}"
        ctr0 = await db.counters.find_one({"_id": f"receipt:{org_id}"})
        deps.FAULTS.add("payment.record.after_payment")
        r = await c.post("/api/payments", json={"member_id": mid, "amount": 300}, headers={"Idempotency-Key": key})
        assert r.status_code == 500
        _, _, pays = await state(mid)
        assert pays == []
        assert await db.counters.find_one({"_id": f"receipt:{org_id}"}) == ctr0, "receipt counter consumed by rolled-back txn"
        r = await c.post("/api/payments", json={"member_id": mid, "amount": 300}, headers={"Idempotency-Key": key})
        assert r.status_code == 200 and r.json()["member_due_remaining"] == 700
        pid = r.json()["id"]
        # edit
        deps.FAULTS.add("payment.edit.after_payment")
        r = await c.put(f"/api/payments/{pid}", json={"amount": 500})
        assert r.status_code == 500
        p = await db.payments.find_one({"id": pid})
        assert p["amount"] == 300 and not p.get("edit_history")
        assert (await db.members.find_one({"id": mid}))["due_amount"] == 700
        r = await c.put(f"/api/payments/{pid}", json={"amount": 500})
        assert r.status_code == 200 and r.json()["member_due_remaining"] == 500
        # reverse
        for cp in ("payment.reverse.after_negative_entry", "payment.reverse.after_mark_original"):
            deps.FAULTS.add(cp)
            r = await c.delete(f"/api/payments/{pid}", headers={"Idempotency-Key": f"r-{pid}"})
            assert r.status_code == 500, cp
            p = await db.payments.find_one({"id": pid})
            assert p["status"] != "reversed", cp
            assert await db.payments.count_documents({"reversal_of": pid}) == 0, cp
            assert (await db.members.find_one({"id": mid}))["due_amount"] == 500
        for _ in range(2):
            r = await c.delete(f"/api/payments/{pid}", headers={"Idempotency-Key": f"r-{pid}"})
            assert r.status_code == 200, r.text
            assert r.json()["member_due_remaining"] == 1000
        assert await db.payments.count_documents({"reversal_of": pid}) == 1
        rev = await db.payments.find_one({"reversal_of": pid})
        assert rev["amount"] == -500
        await assert_balance(mid)
        await c.aclose()
    run(go())


# ---------------- Fault injection: opening-balance ledger ----------------
async def legacy_member(org_id, due, paid):
    mid = deps.new_id()
    await db.members.insert_one({"id": mid, "organisation_id": org_id, "outlet_id": "x", "full_name": "TEST_Legacy", "phone": f"+91{phone()}",
                                 "member_code": f"LG-{uuid.uuid4().hex[:8]}", "membership_start": "2025-01-01",
                                 "membership_expiry": "2025-02-01", "due_amount": due, "created_at": deps.now_utc(), "deleted_at": None})
    if paid:
        await db.payments.insert_one({"id": deps.new_id(), "organisation_id": org_id, "member_id": mid, "amount": paid,
                                      "status": "active", "type": "admission", "created_at": deps.now_utc()})
    return mid


def test_opening_invoice_fault_and_retry():
    async def go():
        org_id = f"org-{uuid.uuid4()}"
        mid = await legacy_member(org_id, 500, 300)
        deps.FAULTS.add("ledger.after_opening_invoice")
        with pytest.raises(RuntimeError):
            await member_ledger.migrate_member(org_id, mid)
        assert await db.member_invoices.count_documents({"member_id": mid}) == 0
        assert not (await db.members.find_one({"id": mid})).get("ledger_v")
        await member_ledger.migrate_member(org_id, mid)
        await member_ledger.migrate_member(org_id, mid)
        inv = await db.member_invoices.find({"member_id": mid}).to_list(None)
        assert len(inv) == 1 and inv[0]["kind"] == "opening" and inv[0]["amount"] == 800
        assert (await db.members.find_one({"id": mid}))["due_amount"] == 500
    run(go())


def test_concurrent_migration_workers():
    async def go():
        org_id = f"org-{uuid.uuid4()}"
        specs = [(500, 300), (0, 1000), (250, 0), (1200, 400), (0, 0), (99.5, 0.5), (700, 700), (10, 0)]
        mids = [await legacy_member(org_id, d, p) for d, p in specs]
        res = await asyncio.gather(member_ledger.migrate_all(), member_ledger.migrate_all(), member_ledger.migrate_all(),
                                   *[member_ledger.migrate_member(org_id, m) for m in mids], return_exceptions=True)
        errs = [r for r in res if isinstance(r, Exception)]
        assert not errs, errs
        for mid, (due, paid) in zip(mids, specs):
            ops = await db.member_invoices.count_documents({"member_id": mid, "kind": "opening"})
            assert ops == (1 if due + paid > 0 else 0), (mid, ops)
            m = await db.members.find_one({"id": mid})
            assert m["ledger_v"] == 1 and m["due_amount"] == due, (m["due_amount"], due)
        await db.migrations.delete_many({})
        res = await asyncio.gather(server.run_migrations(), server.run_migrations(), return_exceptions=True)
        assert not [r for r in res if isinstance(r, Exception)], res
        assert await db.migrations.count_documents({}) == 1
    run(go())


# ---------------- Subscription grant ----------------
async def bare_org():
    org_id = f"org-{uuid.uuid4()}"
    await db.organisations.insert_one({"id": org_id, "name": "Grant Gym", "subscription": {"status": "trial"}})
    return org_id


async def sub_end(org_id):
    o = await db.organisations.find_one({"id": org_id})
    return (o.get("subscription") or {}).get("subscription_ends_at")


def test_apply_payment_faults_rollback():
    async def go():
        org_id = await bare_org()
        order = f"order_{uuid.uuid4().hex[:8]}"
        await db.subscription_payments.insert_one({"id": deps.new_id(), "organisation_id": org_id, "order_id": order, "status": "created", "amount": 999})
        for cp in ("subscription.after_ledger", "subscription.after_grant", "subscription.after_payment_row"):
            deps.FAULTS.add(cp)
            with pytest.raises(RuntimeError):
                await billing_sync.apply_payment(org_id, "pay_F1", plan_id="monthly", order_id=order)
            assert await sub_end(org_id) is None, cp
            assert await db.subscription_ledger.count_documents({"payment_id": "pay_F1"}) == 0, cp
            assert (await db.subscription_payments.find_one({"order_id": order}))["status"] == "created", cp
        ends = await billing_sync.apply_payment(org_id, "pay_F1", plan_id="monthly", order_id=order)
        assert ends is not None
        assert await billing_sync.apply_payment(org_id, "pay_F1", plan_id="monthly", order_id=order) is None
        assert await db.subscription_ledger.count_documents({"payment_id": "pay_F1"}) == 1
        assert (await db.subscription_payments.find_one({"order_id": order}))["status"] == "paid"
        got = await sub_end(org_id)
        assert abs((got - deps.now_utc()) - timedelta(days=30)) < timedelta(minutes=5)
    run(go())


def test_apply_payment_concurrency():
    async def go():
        org_id = await bare_org()
        res = await asyncio.gather(*[billing_sync.apply_payment(org_id, "pay_SAME", plan_id="monthly") for _ in range(5)], return_exceptions=True)
        assert not [r for r in res if isinstance(r, Exception)], res
        assert len([r for r in res if r]) == 1, res
        e1 = await sub_end(org_id)
        assert abs((e1 - deps.now_utc()) - timedelta(days=30)) < timedelta(minutes=5)
        res = await asyncio.gather(billing_sync.apply_payment(org_id, "pay_A", plan_id="monthly"),
                                   billing_sync.apply_payment(org_id, "pay_B", plan_id="monthly"), return_exceptions=True)
        assert all(r and not isinstance(r, Exception) for r in res), res
        e2 = await sub_end(org_id)
        assert abs((e2 - e1) - timedelta(days=60)) < timedelta(seconds=5), (e1, e2)
    run(go())


def test_apply_payment_side_effect_failures(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("analytics down")
    monkeypatch.setattr(billing_sync, "audit", boom)
    monkeypatch.setattr(billing_sync, "track", boom)

    async def go():
        org_id = await bare_org()
        ends = await billing_sync.apply_payment(org_id, "pay_SE", plan_id="monthly")
        assert ends is not None
        assert await db.subscription_ledger.count_documents({"payment_id": "pay_SE"}) == 1
        assert await sub_end(org_id) == ends or abs(await sub_end(org_id) - ends) < timedelta(seconds=1)
        assert await billing_sync.apply_payment(org_id, "pay_SE", plan_id="monthly") is None
        assert abs(await sub_end(org_id) - ends) < timedelta(seconds=1)
    run(go())


# ---------------- Webhook claim / recovery ----------------
def test_claim_event_states():
    async def go():
        eid = f"evt_{uuid.uuid4().hex[:8]}"
        assert await billing_sync.claim_event(eid, "x") == "new"
        assert await billing_sync.claim_event(eid, "x") == "busy"
        await db.webhook_events.update_one({"event_id": eid}, {"$set": {"claimed_at": deps.now_utc() - timedelta(minutes=6)}})
        assert await billing_sync.claim_event(eid, "x") == "new"
        await billing_sync.finish_event(eid, False, "err")
        assert await billing_sync.claim_event(eid, "x") == "new"
        await billing_sync.finish_event(eid, True)
        assert await billing_sync.claim_event(eid, "x") == "duplicate"
        assert (await db.webhook_events.find_one({"event_id": eid}))["attempts"] == 3
    run(go())


def test_webhook_crash_then_redelivery_grants_once():
    async def go():
        c = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app, raise_app_exceptions=False), base_url="https://test")
        org_id = await bare_org()
        rzp = f"sub_{uuid.uuid4().hex[:8]}"
        await db.subscriptions.insert_one({"id": deps.new_id(), "organisation_id": org_id, "razorpay_subscription_id": rzp,
                                           "status": "active", "plan_key": "monthly", "amount": 999})
        body = json.dumps({"event": "subscription.charged", "payload": {"subscription": {"entity": {"id": rzp}},
                           "payment": {"entity": {"id": "pay_WH1", "amount": 99900}}}}).encode()
        sig = hmac.new(WH_SECRET.encode(), body, hashlib.sha256).hexdigest()
        h = {"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_WH1", "Content-Type": "application/json"}
        deps.FAULTS.add("subscription.after_grant")
        r = await c.post("/api/webhooks/razorpay", content=body, headers=h)
        assert r.status_code == 500, r.text
        assert (await db.webhook_events.find_one({"event_id": "evt_WH1"}))["status"] == "failed"
        assert await sub_end(org_id) is None
        assert await db.subscription_payments.count_documents({"payment_id": "pay_WH1"}) == 0
        r = await c.post("/api/webhooks/razorpay", content=body, headers=h)
        assert r.status_code == 200 and r.json()["status"] == "processed", r.text
        r = await c.post("/api/webhooks/razorpay", content=body, headers=h)
        assert r.json()["status"] == "duplicate"
        # a different event id for the same payment must not grant twice
        h2 = {**h, "X-Razorpay-Event-Id": "evt_WH2"}
        r = await c.post("/api/webhooks/razorpay", content=body, headers=h2)
        assert r.status_code == 200
        assert await db.subscription_ledger.count_documents({"payment_id": "pay_WH1"}) == 1
        assert await db.subscription_payments.count_documents({"payment_id": "pay_WH1"}) == 1
        assert abs((await sub_end(org_id) - deps.now_utc()) - timedelta(days=30)) < timedelta(minutes=5)
        await c.aclose()
    run(go())


# ---------------- Idempotency-Key HTTP ----------------
def test_idempotency_keys_http():
    async def go():
        c, org_id, plan_id = await tenant()
        key = f"k-{uuid.uuid4()}"
        m = await new_member(c, plan_id, paid=0, key=key)
        mid = m["id"]
        # different scope with same key -> 422
        r = await c.post("/api/payments", json={"member_id": mid, "amount": 100}, headers={"Idempotency-Key": key})
        assert r.status_code == 422, r.text
        # concurrent same key payment x5
        pk = f"p-{uuid.uuid4()}"
        res = await asyncio.gather(*[c.post("/api/payments", json={"member_id": mid, "amount": 100}, headers={"Idempotency-Key": pk}) for _ in range(5)])
        codes = [r.status_code for r in res]
        assert all(cd == 200 for cd in codes), codes
        assert len({r.json()["id"] for r in res}) == 1
        assert await db.payments.count_documents({"member_id": mid}) == 1
        pid = res[0].json()["id"]
        # concurrent same key renewal x4
        rk = f"r-{uuid.uuid4()}"
        res = await asyncio.gather(*[c.post(f"/api/members/{mid}/renew", json={"plan_id": plan_id, "amount_paid": 0}, headers={"Idempotency-Key": rk}) for _ in range(4)])
        assert [r.status_code for r in res] == [200] * 4, [(r.status_code, r.text[:80]) for r in res]
        assert await db.member_invoices.count_documents({"member_id": mid, "kind": "renewal"}) == 1
        # renewal key reused on a different member -> 422
        mid2 = (await new_member(c, plan_id))["id"]
        r = await c.post(f"/api/members/{mid2}/renew", json={"plan_id": plan_id}, headers={"Idempotency-Key": rk})
        assert r.status_code == 422
        # concurrent same key member create x4
        ck, ph = f"c-{uuid.uuid4()}", phone()
        res = await asyncio.gather(*[c.post("/api/members", json={"full_name": "TEST_Conc", "phone": ph, "plan_id": plan_id, "amount_paid": 200},
                                             headers={"Idempotency-Key": ck}) for _ in range(4)])
        assert [r.status_code for r in res] == [200] * 4, [(r.status_code, r.text[:80]) for r in res]
        assert await db.members.count_documents({"phone": f"+91{ph}"}) == 1
        # concurrent same key reversal x4
        dk = f"d-{uuid.uuid4()}"
        res = await asyncio.gather(*[c.delete(f"/api/payments/{pid}", headers={"Idempotency-Key": dk}) for _ in range(4)])
        codes = [r.status_code for r in res]
        assert await db.payments.count_documents({"reversal_of": pid}) == 1
        assert codes == [200] * 4, f"same-key concurrent reversal codes {codes}"
        await assert_balance(mid)
        await c.aclose()
    run(go())


# ---------------- Concurrent renewals without key ----------------
def test_concurrent_renewals_no_key():
    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id, paid=1000))["id"]
        m0 = await db.members.find_one({"id": mid})
        res = await asyncio.gather(*[c.post(f"/api/members/{mid}/renew", json={"plan_id": plan_id, "amount_paid": 250}) for _ in range(5)])
        ok = [r for r in res if r.status_code == 200]
        assert all(r.status_code in (200, 409) for r in res), [r.status_code for r in res]
        m, inv, pays = await assert_balance(mid)
        ren = [i for i in inv if i["kind"] == "renewal"]
        assert len(ren) == len(ok)
        assert len({i["cycle_key"] for i in inv}) == len(inv)
        exp = date.fromisoformat(str(m0["membership_expiry"])[:10])
        for _ in ok:
            exp = deps.add_duration(max(exp, deps.today_ist()), "months", 1)
        assert m["membership_expiry"] == exp.isoformat()
        assert m["due_amount"] == 750 * len(ok)
        print(f"concurrent renewals: {len(ok)}/5 succeeded")
        await c.aclose()
    run(go())


# ---------------- Edit racing reversal / double reversal ----------------
def test_edit_racing_reversal():
    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id))["id"]
        outcomes = []
        for i in range(6):
            r = await c.post("/api/payments", json={"member_id": mid, "amount": 300})
            pid = r.json()["id"]
            calls = [c.put(f"/api/payments/{pid}", json={"amount": 200}), c.delete(f"/api/payments/{pid}")]
            if i % 2:
                calls.reverse()
            res = await asyncio.gather(*calls)
            codes = sorted(r.status_code for r in res)
            outcomes.append(codes)
            p = await db.payments.find_one({"id": pid})
            revs = await db.payments.find({"reversal_of": pid}).to_list(None)
            assert p["status"] == "reversed" and len(revs) == 1
            assert revs[0]["amount"] == -p["amount"], (p["amount"], revs[0]["amount"])
            assert codes in ([200, 200], [200, 409]), codes
            await assert_balance(mid)
        print("edit/reverse outcomes", outcomes)
        await c.aclose()
    run(go())


def test_double_reversal_concurrent():
    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id))["id"]
        pid = (await c.post("/api/payments", json={"member_id": mid, "amount": 400})).json()["id"]
        res = await asyncio.gather(*[c.delete(f"/api/payments/{pid}") for _ in range(5)])
        codes = sorted(r.status_code for r in res)
        assert codes.count(200) == 1, codes
        assert await db.payments.count_documents({"reversal_of": pid}) == 1
        assert set(codes) <= {200, 404}, codes
        await assert_balance(mid)
        await c.aclose()
    run(go())


# ---------------- Razorpay cancellation durability ----------------
def fake_rzp(cancel=None, get=None, fail_ids=()):
    calls = []

    async def rq(method, path, payload=None):
        calls.append((method, path))
        sid = path.split("/")[2] if path.startswith("/subscriptions/") else None
        if method == "POST" and path.endswith("/cancel"):
            if cancel == "raise" or sid in fail_ids:
                raise HTTPException(503, "gateway down")
            return {"status": cancel or "cancelled"}, "key"
        if method == "GET" and sid:
            return {"status": "active" if sid in fail_ids else (get or "cancelled")}, "key"
        return {"items": []}, "key"
    rq.calls = calls
    return rq


async def add_sub(org_id, status="active"):
    rzp = f"sub_{uuid.uuid4().hex[:10]}"
    await db.subscriptions.insert_one({"id": deps.new_id(), "organisation_id": org_id, "razorpay_subscription_id": rzp,
                                       "status": status, "plan_key": "monthly", "amount": 999, "created_at": deps.now_utc()})
    return rzp


def _delete(c):
    return c.post("/api/auth/delete-account", json={"password": PW, "confirm": "DELETE"})


def test_delete_account_cancel_confirmed(monkeypatch):
    async def go():
        c, org_id, plan_id = await tenant()
        await new_member(c, plan_id, paid=100)
        rzp = await add_sub(org_id)
        monkeypatch.setattr(server, "razorpay_request", fake_rzp(cancel="cancelled"))
        r = await _delete(c)
        assert r.status_code == 200, r.text
        assert await db.organisations.count_documents({"id": org_id}) == 0
        assert await db.members.count_documents({"organisation_id": org_id}) == 0
        op = await db.razorpay_ops.find_one({"target": rzp})
        assert op and op["status"] == "succeeded"
    run(go())


def test_delete_account_cancel_fails_blocks(monkeypatch):
    async def go():
        c, org_id, plan_id = await tenant()
        await new_member(c, plan_id, paid=100)
        rzp = await add_sub(org_id)
        monkeypatch.setattr(server, "razorpay_request", fake_rzp(fail_ids=(rzp,)))
        r = await _delete(c)
        assert r.status_code == 409, r.text
        assert await db.organisations.count_documents({"id": org_id}) == 1
        assert await db.members.count_documents({"organisation_id": org_id}) == 1
        assert await db.users.count_documents({"organisation_id": org_id}) == 1
        op = await db.razorpay_ops.find_one({"target": rzp})
        assert op["status"] == "failed" and op["attempts"] == 1
        assert (await db.subscriptions.find_one({"razorpay_subscription_id": rzp}))["status"] == "active"
        # reconcile retries the failed op once Razorpay recovers
        stats = await billing_sync.reconcile(fake_rzp(cancel="cancelled"))
        assert stats["cancellations_confirmed"] >= 1
        op = await db.razorpay_ops.find_one({"target": rzp})
        assert op["status"] == "succeeded" and op["attempts"] == 2
        assert (await db.subscriptions.find_one({"razorpay_subscription_id": rzp}))["status"] == "cancelled"
        monkeypatch.setattr(server, "razorpay_request", fake_rzp(cancel="raise"))
        r = await _delete(c)
        assert r.status_code == 200, r.text
        await c.aclose()
    run(go())


def test_delete_account_cancel_raises_but_get_cancelled(monkeypatch):
    async def go():
        c, org_id, _ = await tenant()
        await add_sub(org_id)
        monkeypatch.setattr(server, "razorpay_request", fake_rzp(cancel="raise", get="cancelled"))
        r = await _delete(c)
        assert r.status_code == 200, r.text
        assert await db.organisations.count_documents({"id": org_id}) == 0
    run(go())


def test_delete_account_multiple_subs_one_failing(monkeypatch):
    async def go():
        c, org_id, _ = await tenant()
        rzps = [await add_sub(org_id, st) for st in ("created", "active", "halted", "paused", "abandoned")]
        await add_sub(org_id, "cancelled")
        fake = fake_rzp(fail_ids=(rzps[3],))
        monkeypatch.setattr(server, "razorpay_request", fake)
        r = await _delete(c)
        assert r.status_code == 409
        cancelled = {p.split("/")[2] for m, p in fake.calls if p.endswith("/cancel")}
        assert cancelled == set(rzps), "every billable sub must be cancel-attempted"
        assert await db.organisations.count_documents({"id": org_id}) == 1
        fake2 = fake_rzp()
        monkeypatch.setattr(server, "razorpay_request", fake2)
        r = await _delete(c)
        assert r.status_code == 200, r.text
        assert {p.split("/")[2] for m, p in fake2.calls if p.endswith("/cancel")} == {rzps[3]}
    run(go())


def test_autodebit_cancel_unconfirmed_503(monkeypatch):
    async def go():
        c, org_id, _ = await tenant()
        rzp = await add_sub(org_id)
        monkeypatch.setattr(billing, "razorpay_request", fake_rzp(fail_ids=(rzp,)))
        r = await c.post("/api/subscription/autodebit/cancel")
        assert r.status_code == 503, r.text
        assert (await db.subscriptions.find_one({"razorpay_subscription_id": rzp}))["status"] == "active"
        monkeypatch.setattr(billing, "razorpay_request", fake_rzp())
        r = await c.post("/api/subscription/autodebit/cancel")
        assert r.status_code == 200
        assert (await db.subscriptions.find_one({"razorpay_subscription_id": rzp}))["status"] == "cancelled"
        await c.aclose()
    run(go())


def test_edit_reversal_forced_interleaving(monkeypatch):
    """Hold one txn open at a checkpoint while the other runs, in both orders."""
    import members
    real = deps.checkpoint
    hold = {}

    async def slow(name):
        if name in hold:
            await asyncio.sleep(hold[name])
        await real(name)
    monkeypatch.setattr(members, "checkpoint", slow)

    async def go():
        c, org_id, plan_id = await tenant()
        mid = (await new_member(c, plan_id))["id"]
        # A) edit in flight, reversal arrives -> reversal must reverse the EDITED amount
        hold.clear(); hold["payment.edit.after_payment"] = 0.5
        pid = (await c.post("/api/payments", json={"member_id": mid, "amount": 300})).json()["id"]

        async def later(coro, d):
            await asyncio.sleep(d)
            return await coro
        e, d = await asyncio.gather(c.put(f"/api/payments/{pid}", json={"amount": 200}), later(c.delete(f"/api/payments/{pid}"), 0.1))
        p = await db.payments.find_one({"id": pid})
        rev = await db.payments.find({"reversal_of": pid}).to_list(None)
        print("A", e.status_code, d.status_code, p["amount"], [r["amount"] for r in rev])
        assert p["status"] == "reversed" and len(rev) == 1 and rev[0]["amount"] == -p["amount"]
        await assert_balance(mid)
        # B) reversal in flight, edit arrives -> edit must get 409
        hold.clear(); hold["payment.reverse.after_negative_entry"] = 0.5
        pid = (await c.post("/api/payments", json={"member_id": mid, "amount": 300})).json()["id"]
        d, e = await asyncio.gather(c.delete(f"/api/payments/{pid}"), later(c.put(f"/api/payments/{pid}", json={"amount": 200}), 0.1))
        p = await db.payments.find_one({"id": pid})
        rev = await db.payments.find({"reversal_of": pid}).to_list(None)
        print("B", d.status_code, e.status_code, p["amount"], [r["amount"] for r in rev])
        assert d.status_code == 200 and e.status_code in (200, 409), (d.status_code, e.status_code, e.text)
        assert len(rev) == 1 and rev[0]["amount"] == -p["amount"]
        assert p["amount"] == (200 if e.status_code == 200 else 300)
        await assert_balance(mid)
        # D) reversal holds the original (after mark) -> edit must wait and then 409
        hold.clear(); hold["payment.reverse.after_mark_original"] = 0.5
        pid = (await c.post("/api/payments", json={"member_id": mid, "amount": 300})).json()["id"]
        d, e = await asyncio.gather(c.delete(f"/api/payments/{pid}"), later(c.put(f"/api/payments/{pid}", json={"amount": 200}), 0.1))
        p = await db.payments.find_one({"id": pid})
        rev = await db.payments.find({"reversal_of": pid}).to_list(None)
        print("D", d.status_code, e.status_code, p["amount"], [r["amount"] for r in rev])
        assert d.status_code == 200 and e.status_code == 409 and p["amount"] == 300 and rev[0]["amount"] == -300
        await assert_balance(mid)
        # C) sequential: reverse then edit -> 409
        pid = (await c.post("/api/payments", json={"member_id": mid, "amount": 50})).json()["id"]
        assert (await c.delete(f"/api/payments/{pid}")).status_code == 200
        assert (await c.put(f"/api/payments/{pid}", json={"amount": 20})).status_code == 409
        await c.aclose()
    run(go())
