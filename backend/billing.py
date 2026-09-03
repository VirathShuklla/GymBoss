import hashlib
import hmac
import os
from datetime import timedelta

import httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from deps import db, now_utc, new_id, get_org_user, derive_subscription, audit, PLAN_PRICE_INR

router = APIRouter(tags=["billing"])


def razorpay_keys():
    return os.environ.get("RAZORPAY_KEY_ID", ""), os.environ.get("RAZORPAY_KEY_SECRET", "")


@router.get("/subscription")
async def get_subscription(user: dict = Depends(get_org_user)):
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    payments = await db.subscription_payments.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    key_id, _ = razorpay_keys()
    return {
        "subscription": derive_subscription(org),
        "payments": payments,
        "razorpay_configured": bool(key_id),
    }


@router.post("/subscription/create-order")
async def create_order(user: dict = Depends(get_org_user)):
    key_id, key_secret = razorpay_keys()
    if not key_id or not key_secret:
        raise HTTPException(503, "Online payments are being configured. Please contact BuildVVO support to activate your subscription.")
    org_id = user["organisation_id"]
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            "https://api.razorpay.com/v1/orders",
            auth=(key_id, key_secret),
            json={"amount": PLAN_PRICE_INR * 100, "currency": "INR", "receipt": f"sub_{org_id[:24]}", "payment_capture": 1},
        )
    if resp.status_code >= 400:
        raise HTTPException(502, "Could not create a payment order. Please try again.")
    order = resp.json()
    await db.subscription_payments.insert_one({
        "id": new_id(), "organisation_id": org_id, "order_id": order["id"],
        "amount": PLAN_PRICE_INR, "currency": "INR", "status": "created", "created_at": now_utc(),
    })
    return {"order_id": order["id"], "amount": PLAN_PRICE_INR * 100, "currency": "INR", "key_id": key_id}


class VerifyBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


async def activate_subscription(org_id: str, payment_id: str, actor: str = "razorpay"):
    now = now_utc()
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
        "subscription.amount": PLAN_PRICE_INR,
    }})
    await db.subscription_payments.update_one(
        {"organisation_id": org_id, "status": {"$ne": "paid"}}, 
        {"$set": {"status": "paid", "payment_id": payment_id, "paid_at": now}},
    )
    await audit(actor, "subscription.activated", org_id, {"payment_id": payment_id, "ends": ends.isoformat()}, org_id)
    return ends


@router.post("/subscription/verify")
async def verify_payment(body: VerifyBody, user: dict = Depends(get_org_user)):
    _, key_secret = razorpay_keys()
    if not key_secret:
        raise HTTPException(503, "Payments are not configured")
    expected = hmac.new(key_secret.encode(), f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, "Payment verification failed")
    ends = await activate_subscription(user["organisation_id"], body.razorpay_payment_id, actor=user["id"])
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    return {"message": "Subscription activated", "subscription": derive_subscription(org)}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    payload = await request.body()
    if webhook_secret:
        signature = request.headers.get("X-Razorpay-Signature", "")
        expected = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(400, "Invalid webhook signature")
    import json
    event = json.loads(payload)
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
