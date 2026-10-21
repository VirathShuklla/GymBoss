# Iteration 20: Razorpay billing sync (webhooks, idempotency, reconcile, invoices, store-client protection, native tokens, CORS)
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

from conftest import API, unique_email

WEBHOOK_SECRET = "whsec_preview_test_only"
CRON_SECRET = "c4ccd2fc5f01b0403c339b6de9042097438609f5411d34bf"
_env = dotenv_values("/app/backend/.env")
mdb = MongoClient(_env["MONGO_URL"])[_env["DB_NAME"]]


def register(headers=None):
    s = requests.Session()
    email = unique_email("test_bill")
    phone = "9" + str(uuid.uuid4().int)[:9]
    r = s.post(f"{API}/auth/register", json={"full_name": "TEST Bill", "email": email, "phone": phone, "password": "QaTest@2026",
                                              "gym_name": "TEST Billing Gym", "outlet_name": "Main", "city": "Pune"}, headers=headers or {})
    assert r.status_code == 200, r.text
    return s, r.json(), email


def sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def send(event: dict, event_id=None, signature=None):
    body = json.dumps(event).encode()
    h = {"Content-Type": "application/json", "X-Razorpay-Signature": signature if signature is not None else sign(body)}
    if event_id:
        h["X-Razorpay-Event-Id"] = event_id
    return requests.post(f"{API}/webhooks/razorpay", data=body, headers=h)


def org_sub(org_id):
    return mdb.organisations.find_one({"id": org_id})["subscription"]


def ends(org_id):
    e = org_sub(org_id).get("subscription_ends_at")
    return e.replace(tzinfo=timezone.utc) if e and e.tzinfo is None else e


@pytest.fixture(scope="module")
def org():
    s, data, email = register()
    org_id = data["organisation"]["id"]
    rzp_sub = f"sub_TEST{uuid.uuid4().hex[:10]}"
    mdb.subscriptions.insert_one({"id": str(uuid.uuid4()), "organisation_id": org_id, "razorpay_subscription_id": rzp_sub,
                                  "plan_key": "monthly", "amount": 999, "status": "created", "created_at": datetime.now(timezone.utc)})
    yield {"s": s, "org_id": org_id, "rzp_sub": rzp_sub, "email": email}
    for c in ("subscriptions", "subscription_payments", "subscription_ledger"):
        mdb[c].delete_many({"organisation_id": org_id})


def sub_event(name, rzp_sub, pay_id=None, amount=99900):
    payload = {"subscription": {"entity": {"id": rzp_sub, "status": name}}}
    if pay_id:
        payload["payment"] = {"entity": {"id": pay_id, "status": "captured", "amount": amount}}
    return {"event": f"subscription.{name}", "payload": payload}


# --- Webhook signature + dedupe
class TestWebhookSignature:
    def test_missing_signature(self):
        r = requests.post(f"{API}/webhooks/razorpay", data=b'{"event":"x"}', headers={"Content-Type": "application/json"})
        assert r.status_code == 400

    def test_invalid_signature(self):
        assert send({"event": "x"}, signature="deadbeef").status_code == 400

    def test_duplicate_event_id(self):
        eid = f"evt_TEST{uuid.uuid4().hex[:10]}"
        r1 = send({"event": "order.paid", "payload": {}}, eid)
        assert r1.status_code == 200 and r1.json()["status"] == "ignored"
        r2 = send({"event": "order.paid", "payload": {}}, eid)
        assert r2.json() == {"status": "duplicate"}


# --- Subscription lifecycle
class TestSubscriptionLifecycle:
    def test_activated_and_charged_same_payment_once(self, org):
        pay = f"pay_TEST{uuid.uuid4().hex[:10]}"
        before = datetime.now(timezone.utc)
        r = send(sub_event("activated", org["rzp_sub"], pay), f"evt_{uuid.uuid4().hex}")
        assert r.json()["status"] == "processed"
        e1 = ends(org["org_id"])
        assert org_sub(org["org_id"])["status"] == "active"
        assert timedelta(days=29, hours=23) < e1 - before < timedelta(days=30, hours=1)
        r = send(sub_event("charged", org["rzp_sub"], pay), f"evt_{uuid.uuid4().hex}")
        assert r.json()["status"] == "processed"
        assert ends(org["org_id"]) == e1
        assert mdb.subscription_payments.count_documents({"organisation_id": org["org_id"], "payment_id": pay}) == 1
        assert mdb.subscriptions.find_one({"razorpay_subscription_id": org["rzp_sub"]})["status"] == "active"

    def test_new_payment_extends_again(self, org):
        e1 = ends(org["org_id"])
        send(sub_event("charged", org["rzp_sub"], f"pay_TEST{uuid.uuid4().hex[:10]}"), f"evt_{uuid.uuid4().hex}")
        e2 = ends(org["org_id"])
        assert abs((e2 - e1) - timedelta(days=30)) < timedelta(seconds=5)

    @pytest.mark.parametrize("kind", ["pending", "halted"])
    def test_pending_halted_flag_then_charged_clears(self, org, kind):
        fails_before = mdb.subscription_payments.count_documents({"organisation_id": org["org_id"], "status": "failed"})
        r = send(sub_event(kind, org["rzp_sub"]), f"evt_{uuid.uuid4().hex}")
        assert r.json()["status"] == "processed"
        assert org_sub(org["org_id"])["billing_issue"] is True
        assert mdb.subscriptions.find_one({"razorpay_subscription_id": org["rzp_sub"]})["status"] == kind
        # one failed row per renewal attempt window (24h dedupe), so pending then halted adds at most one
        assert fails_before <= mdb.subscription_payments.count_documents({"organisation_id": org["org_id"], "status": "failed"}) <= fails_before + 1
        # visible through API
        g = org["s"].get(f"{API}/subscription").json()
        assert any(p["status"] == "failed" for p in g["payments"])
        send(sub_event("charged", org["rzp_sub"], f"pay_TEST{uuid.uuid4().hex[:10]}"), f"evt_{uuid.uuid4().hex}")
        assert org_sub(org["org_id"])["billing_issue"] is False

    def test_cancelled(self, org):
        send(sub_event("cancelled", org["rzp_sub"]), f"evt_{uuid.uuid4().hex}")
        local = mdb.subscriptions.find_one({"razorpay_subscription_id": org["rzp_sub"]})
        assert local["status"] == "cancelled" and local.get("cancelled_at")
        g = org["s"].get(f"{API}/subscription").json()
        assert g["autodebit"]["status"] == "cancelled"

    def test_unknown_subscription(self):
        r = send(sub_event("activated", "sub_DOESNOTEXIST"), f"evt_{uuid.uuid4().hex}")
        assert r.json()["status"] == "unknown_subscription"


# --- Invoice PDF
class TestInvoice:
    def test_invoice_own_paid(self, org):
        g = org["s"].get(f"{API}/subscription").json()
        paid = [p for p in g["payments"] if p["status"] == "paid"]
        assert paid
        r = org["s"].get(f"{API}/subscription/payments/{paid[0]['id']}/invoice.pdf")
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf") and r.content[:4] == b"%PDF"

    def test_invoice_unpaid_404(self, org):
        g = org["s"].get(f"{API}/subscription").json()
        failed = [p for p in g["payments"] if p["status"] == "failed"]
        assert failed
        assert org["s"].get(f"{API}/subscription/payments/{failed[0]['id']}/invoice.pdf").status_code == 404

    def test_invoice_other_org_404(self, org):
        other, _, _ = register()
        paid = next(p for p in org["s"].get(f"{API}/subscription").json()["payments"] if p["status"] == "paid")
        assert other.get(f"{API}/subscription/payments/{paid['id']}/invoice.pdf").status_code == 404


# --- One-time order flow
class TestOrderFlow:
    def test_create_order_capture_and_fail(self):
        s, data, _ = register()
        org_id = data["organisation"]["id"]
        r = s.post(f"{API}/subscription/create-order", json={"plan_id": "monthly"})
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["order_id"].startswith("order_") and o["amount"] == 99900
        pay = f"pay_TEST{uuid.uuid4().hex[:10]}"
        ev = {"event": "payment.captured", "payload": {"payment": {"entity": {"id": pay, "order_id": o["order_id"], "status": "captured"}}}}
        assert send(ev, f"evt_{uuid.uuid4().hex}").json()["status"] == "processed"
        e1 = ends(org_id)
        assert org_sub(org_id)["status"] == "active"
        assert send(ev, f"evt_{uuid.uuid4().hex}").json()["status"] == "processed"  # retry with new event id
        assert ends(org_id) == e1
        assert mdb.subscription_payments.find_one({"order_id": o["order_id"]})["status"] == "paid"
        # payment.failed for a second order
        o2 = s.post(f"{API}/subscription/create-order", json={"plan_id": "monthly"}).json()
        fev = {"event": "payment.failed", "payload": {"payment": {"entity": {"id": f"pay_F{uuid.uuid4().hex[:8]}", "order_id": o2["order_id"], "error_reason": "TEST_declined"}}}}
        send(fev, f"evt_{uuid.uuid4().hex}")
        assert mdb.subscription_payments.find_one({"order_id": o2["order_id"]})["status"] == "failed"
        # failed for already-paid order must not downgrade
        fev["payload"]["payment"]["entity"]["order_id"] = o["order_id"]
        send(fev, f"evt_{uuid.uuid4().hex}")
        assert mdb.subscription_payments.find_one({"order_id": o["order_id"]})["status"] == "paid"
        mdb.subscription_payments.delete_many({"organisation_id": org_id})

    def test_verify_bad_signature(self):
        s, _, _ = register()
        r = s.post(f"{API}/subscription/verify", json={"razorpay_order_id": "order_x", "razorpay_payment_id": "pay_x", "razorpay_signature": "bad"})
        assert r.status_code == 400

    def test_verify_unknown_order(self):
        s, _, _ = register()
        secret = (mdb.settings.find_one({"id": "platform"}) or {}).get("razorpay_key_secret") or _env.get("RAZORPAY_KEY_SECRET")
        oid, pid = "order_TESTUNKNOWN1", "pay_TESTUNKNOWN1"
        sig = hmac.new(secret.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
        r = s.post(f"{API}/subscription/verify", json={"razorpay_order_id": oid, "razorpay_payment_id": pid, "razorpay_signature": sig})
        assert r.status_code == 404


# --- Reconcile
class TestReconcile:
    def test_cron_ok(self):
        r = requests.post(f"{API}/internal/billing/reconcile", headers={"X-Cron-Secret": CRON_SECRET}, timeout=90)
        assert r.status_code == 200, r.text
        assert {"subscriptions_checked", "status_updates", "payments_applied", "orders_checked", "errors"} <= set(r.json())

    def test_cron_wrong(self):
        assert requests.post(f"{API}/internal/billing/reconcile", headers={"X-Cron-Secret": "nope"}).status_code == 403
        assert requests.post(f"{API}/internal/billing/reconcile").status_code == 403

    def test_admin_requires_super(self, demo_client, creds):
        assert demo_client.post(f"{API}/admin/billing/reconcile").status_code == 403
        s = requests.Session()
        assert s.post(f"{API}/auth/login", json=creds["super_admin"]).status_code == 200
        r = s.post(f"{API}/admin/billing/reconcile", timeout=90)
        assert r.status_code == 200 and "subscriptions_checked" in r.json()


# --- Store client protection & native tokens
class TestStoreClients:
    @pytest.mark.parametrize("plat", ["android_store", "ios_store"])
    def test_store_purchase_blocked_and_tokens(self, plat):
        h = {"X-Client-Platform": plat}
        s, data, email = register(h)
        assert data["tokens"]["access_token"] and data["tokens"]["refresh_token"]
        assert s.post(f"{API}/subscription/create-order", json={}, headers=h).status_code == 403
        assert s.post(f"{API}/subscription/autodebit/start", json={}, headers=h).status_code == 403
        r = requests.post(f"{API}/auth/login", json={"identifier": email, "password": "QaTest@2026"}, headers=h)
        t = r.json()["tokens"]
        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {t['access_token']}"})
        assert me.status_code == 200 and me.json()["user"]["email"] == email
        rr = requests.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]}, headers=h)
        assert rr.status_code == 200 and rr.json()["tokens"]["access_token"]
        me2 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {rr.json()['tokens']['access_token']}"})
        assert me2.status_code == 200

    def test_web_no_tokens(self, creds):
        r = requests.post(f"{API}/auth/login", json=creds["demo"])
        assert r.status_code == 200 and "tokens" not in r.json()
        _, data, _ = register()
        assert "tokens" not in data

    def test_expired_trial_readonly_but_billing_allowed(self):
        s, data, _ = register()
        org_id = data["organisation"]["id"]
        mdb.organisations.update_one({"id": org_id}, {"$set": {"subscription.trial_ends_at": datetime.now(timezone.utc) - timedelta(days=1)}})
        assert s.get(f"{API}/subscription").json()["subscription"]["status"] == "expired"
        r = s.post(f"{API}/members", json={"full_name": "TEST M", "phone": "9876500000"})
        assert r.status_code in (402, 403), r.status_code
        r = s.post(f"{API}/subscription/create-order", json={"plan_id": "monthly"})
        assert r.status_code == 200, r.text


# --- CORS
def test_cors_capacitor():
    r = requests.options(f"{API}/auth/login", headers={"Origin": "capacitor://localhost", "Access-Control-Request-Method": "POST",
                                                        "Access-Control-Request-Headers": "content-type,x-client-platform,authorization"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "capacitor://localhost"
    assert r.headers.get("access-control-allow-credentials") == "true"
