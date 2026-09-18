"""SaaS subscription billing (gym -> BuildVVO): Razorpay one-time orders and auto-debit
subscriptions, HMAC signature verification, and webhook handling."""
import hashlib
import hmac
import os
import logging
from datetime import timedelta

import httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from deps import db, now_utc, new_id, get_org_user, derive_subscription, audit, get_plan_price, get_razorpay_keys, PLAN_PRICE_INR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


async def razorpay_request(method: str, path: str, payload: dict | None = None):
    key_id, key_secret = await get_razorpay_keys()
    if not key_id or not key_secret:
        raise HTTPException(503, "Online payments are being configured. Please contact BuildVVO support to activate your subscription.")
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.request(method, f"https://api.razorpay.com/v1{path}", auth=(key_id, key_secret), json=payload)
    if resp.status_code >= 400:
        logger.error("Razorpay %s %s failed: %s %s", method, path, resp.status_code, resp.text[:300])
        raise HTTPException(503, "Payment gateway error. Please try again or contact support.")
    return resp.json(), key_id


@router.get("/subscription")
async def get_subscription(user: dict = Depends(get_org_user)):
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    payments = await db.subscription_payments.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    key_id, _ = await get_razorpay_keys()
    price = await get_plan_price()
    autodebit = await db.subscriptions.find_one({"organisation_id": user["organisation_id"]}, {"_id": 0}, sort=[("created_at", -1)])
    if autodebit:
        for k in ("created_at", "activated_at", "cancelled_at", "last_charged_at"):
            if autodebit.get(k):
                autodebit[k] = autodebit[k].isoformat()
    return {
        "subscription": derive_subscription(org, price),
        "payments": payments,
        "razorpay_configured": bool(key_id) and key_id.startswith(("rzp_test_", "rzp_live_")),
        "autodebit": autodebit,
    }


@router.post("/subscription/create-order")
async def create_order(user: dict = Depends(get_org_user)):
    key_id, key_secret = await get_razorpay_keys()
    if not key_id or not key_secret:
        raise HTTPException(503, "Online payments are being configured. Please contact BuildVVO support to activate your subscription.")
    price = await get_plan_price()
    org_id = user["organisation_id"]
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            "https://api.razorpay.com/v1/orders",
            auth=(key_id, key_secret),
            json={"amount": price * 100, "currency": "INR", "receipt": f"sub_{org_id[:24]}", "payment_capture": 1},
        )
    if resp.status_code >= 400:
        raise HTTPException(503, "Could not create a payment order. Please try again.")
    order = resp.json()
    await db.subscription_payments.insert_one({
        "id": new_id(), "organisation_id": org_id, "order_id": order["id"],
        "amount": price, "currency": "INR", "status": "created", "created_at": now_utc(),
    })
    return {"order_id": order["id"], "amount": price * 100, "currency": "INR", "key_id": key_id}


class VerifyBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


async def activate_subscription(org_id: str, payment_id: str, actor: str = "razorpay"):
    now = now_utc()
    price = await get_plan_price()
    org = await db.organisations.find_one({"id": org_id})
    sub = (org or {}).get("subscription", {})
    base = sub.get("subscription_ends_at")
    if base and base > now:
        start = base
    else:
        start = now
    ends = start + timedelta(days=30)
    await db.organisations.update_one({"id": org_id}, {"$set": {
        "subscription.status": "active",
        "subscription.subscription_started_at": sub.get("subscription_started_at") or now,
        "subscription.subscription_ends_at": ends,
        "subscription.plan": "monthly",
        "subscription.amount": price,
    }})
    await db.subscription_payments.update_one(
        {"organisation_id": org_id, "status": {"$ne": "paid"}}, 
        {"$set": {"status": "paid", "payment_id": payment_id, "paid_at": now}},
    )
    await audit(actor, "subscription.activated", org_id, {"payment_id": payment_id, "ends": ends.isoformat()}, org_id)
    return ends


@router.post("/subscription/verify")
async def verify_payment(body: VerifyBody, user: dict = Depends(get_org_user)):
    _, key_secret = await get_razorpay_keys()
    if not key_secret:
        raise HTTPException(503, "Payments are not configured")
    expected = hmac.new(key_secret.encode(), f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, "Payment verification failed")
    ends = await activate_subscription(user["organisation_id"], body.razorpay_payment_id, actor=user["id"])
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    return {"message": "Subscription activated", "subscription": derive_subscription(org, await get_plan_price())}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    settings = await db.settings.find_one({"id": "platform"}) or {}
    webhook_secret = settings.get("razorpay_webhook_secret") or os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    payload = await request.body()
    if webhook_secret:
        signature = request.headers.get("X-Razorpay-Signature", "")
        expected = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(400, "Invalid webhook signature")
    import json
    event = json.loads(payload)
    event_name = event.get("event", "")
    if event_name.startswith("subscription."):
        sub_entity = event.get("payload", {}).get("subscription", {}).get("entity", {})
        sub_id = sub_entity.get("id")
        local = await db.subscriptions.find_one({"razorpay_subscription_id": sub_id})
        if not local:
            return {"status": "unknown_subscription"}
        if event_name in ("subscription.activated", "subscription.charged"):
            pay_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
            await db.subscriptions.update_one({"id": local["id"]}, {"$set": {"status": "active", "last_charged_at": now_utc()}})
            if event_name == "subscription.charged":
                price = await get_plan_price()
                ts = now_utc()
                await db.subscription_payments.insert_one({
                    "id": new_id(), "organisation_id": local["organisation_id"], "order_id": sub_id,
                    "payment_id": pay_entity.get("id", ""), "amount": price, "currency": "INR",
                    "status": "paid", "kind": "autodebit_renewal", "created_at": ts, "paid_at": ts,
                })
            await activate_subscription(local["organisation_id"], pay_entity.get("id", ""))
        elif event_name == "subscription.halted":
            await db.subscriptions.update_one({"id": local["id"]}, {"$set": {"status": "halted"}})
            await audit("razorpay", "subscription.halted", local["organisation_id"], {"rzp_subscription": sub_id}, local["organisation_id"])
        elif event_name in ("subscription.cancelled", "subscription.completed"):
            await db.subscriptions.update_one({"id": local["id"]}, {"$set": {"status": "cancelled"}})
            await audit("razorpay", "subscription.cancelled", local["organisation_id"], {"rzp_subscription": sub_id}, local["organisation_id"])
        return {"status": "processed"}
    entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = entity.get("order_id")
    if not order_id:
        return {"status": "ignored"}
    record = await db.subscription_payments.find_one({"order_id": order_id})
    if not record:
        return {"status": "unknown_order"}
    if event.get("event") == "payment.captured" and record.get("status") != "paid":
        await activate_subscription(record["organisation_id"], entity.get("id", ""))
    elif event.get("event") == "payment.failed":
        await db.subscription_payments.update_one({"order_id": order_id}, {"$set": {"status": "failed"}})
    return {"status": "processed"}


# ---------------- Auto-debit subscriptions (UPI Autopay / card recurring) ----------------

async def get_or_create_rzp_plan(price: int) -> str:
    cache = await db.settings.find_one({"id": "razorpay_plan_cache"}) or {}
    if cache.get("price") == price and cache.get("plan_id"):
        return cache["plan_id"]
    data, _ = await razorpay_request("POST", "/plans", {
        "period": "monthly",
        "interval": 1,
        "item": {"name": "GymBoss_VVO Monthly", "amount": price * 100, "currency": "INR"},
    })
    await db.settings.update_one({"id": "razorpay_plan_cache"}, {"$set": {"price": price, "plan_id": data["id"]}}, upsert=True)
    return data["id"]


@router.post("/subscription/autodebit/start")
async def autodebit_start(user: dict = Depends(get_org_user)):
    org_id = user["organisation_id"]
    price = await get_plan_price()
    plan_id = await get_or_create_rzp_plan(price)
    existing = await db.subscriptions.find_one({"organisation_id": org_id, "status": {"$in": ["created", "active"]}})
    _, key_id = None, None
    if existing:
        key_id = (await get_razorpay_keys())[0]
        return {"subscription_id": existing["razorpay_subscription_id"], "key_id": key_id, "amount": price * 100, "currency": "INR", "status": existing["status"]}
    data, key_id = await razorpay_request("POST", "/subscriptions", {
        "plan_id": plan_id,
        "total_count": 120,
        "quantity": 1,
        "customer_notify": 0,
        "notes": {"org_id": org_id},
    })
    await db.subscriptions.insert_one({
        "id": new_id(), "organisation_id": org_id, "razorpay_subscription_id": data["id"],
        "plan_id": plan_id, "amount": price, "status": "created", "created_at": now_utc(),
    })
    await audit(user["id"], "subscription.autodebit_started", org_id, {"rzp_subscription": data["id"]}, org_id)
    return {"subscription_id": data["id"], "key_id": key_id, "amount": price * 100, "currency": "INR", "status": "created"}


class AutodebitVerifyBody(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


@router.post("/subscription/autodebit/verify")
async def autodebit_verify(body: AutodebitVerifyBody, user: dict = Depends(get_org_user)):
    _, key_secret = await get_razorpay_keys()
    if not key_secret:
        raise HTTPException(503, "Payments are not configured")
    expected = hmac.new(key_secret.encode(), f"{body.razorpay_payment_id}|{body.razorpay_subscription_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, "Payment verification failed")
    sub = await db.subscriptions.find_one({"razorpay_subscription_id": body.razorpay_subscription_id, "organisation_id": user["organisation_id"]})
    if not sub:
        raise HTTPException(404, "Subscription not found")
    ts = now_utc()
    await db.subscriptions.update_one({"id": sub["id"]}, {"$set": {"status": "active", "activated_at": ts, "last_charged_at": ts}})
    price = await get_plan_price()
    await db.subscription_payments.insert_one({
        "id": new_id(), "organisation_id": user["organisation_id"], "order_id": body.razorpay_subscription_id,
        "payment_id": body.razorpay_payment_id, "amount": price, "currency": "INR",
        "status": "paid", "kind": "autodebit", "created_at": ts, "paid_at": ts,
    })
    await activate_subscription(user["organisation_id"], body.razorpay_payment_id, actor=user["id"])
    await audit(user["id"], "subscription.autodebit_activated", user["organisation_id"], {"rzp_subscription": body.razorpay_subscription_id}, user["organisation_id"])
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    return {"message": "Auto-debit activated", "subscription": derive_subscription(org, price)}


@router.post("/subscription/autodebit/cancel")
async def autodebit_cancel(user: dict = Depends(get_org_user)):
    org_id = user["organisation_id"]
    sub = await db.subscriptions.find_one({"organisation_id": org_id, "status": {"$in": ["active", "created"]}})
    if not sub:
        raise HTTPException(404, "No active auto-debit subscription found")
    await razorpay_request("POST", f"/subscriptions/{sub['razorpay_subscription_id']}/cancel")
    await db.subscriptions.update_one({"id": sub["id"]}, {"$set": {"status": "cancelled", "cancelled_at": now_utc()}})
    await audit(user["id"], "subscription.autodebit_cancelled", org_id, {"rzp_subscription": sub["razorpay_subscription_id"]}, org_id)
    return {"message": "Auto-debit cancelled. Your access continues until the end of the paid period."}
