"""SaaS subscription billing (gym -> BuildVVO): Razorpay one-time orders and auto-debit
subscriptions, HMAC signature verification, and webhook handling."""
import hashlib
import hmac
import os
import logging

import httpx
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from typing import Optional

from deps import db, now_utc, new_id, get_org_user, require_super_admin, derive_subscription, audit, get_plan_price, get_razorpay_keys, get_pricing_plan, get_pricing_plans
from analytics import track
from billing_sync import release_event, apply_payment, record_autodebit_payment, claim_event, handle_subscription_event, handle_payment_event, reconcile

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
    stale = now_utc() - timedelta(hours=1)
    payments = await db.subscription_payments.find(
        {"organisation_id": user["organisation_id"], "$nor": [{"status": "created", "created_at": {"$lt": stale}}]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
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
        "plans": await get_pricing_plans(active_only=True),
    }


class PlanChoice(BaseModel):
    plan_id: Optional[str] = "monthly"


@router.post("/subscription/create-order")
async def create_order(request: Request, body: PlanChoice | None = None, user: dict = Depends(get_org_user)):
    block_store_clients(request)
    require_billing_role(user)
    key_id, key_secret = await get_razorpay_keys()
    if not key_id or not key_secret:
        raise HTTPException(503, "Online payments are being configured. Please contact BuildVVO support to activate your subscription.")
    plan = await get_pricing_plan(body.plan_id if body else None)
    price = plan["effective_price"]
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
        "amount": price, "currency": "INR", "status": "created", "plan_id": plan["id"], "created_at": now_utc(),
    })
    await track("payment_initiated", org_id, user["id"], props={"plan": plan["id"], "amount": price, "mode": "order"})
    return {"order_id": order["id"], "amount": price * 100, "currency": "INR", "key_id": key_id, "plan": plan}


class VerifyBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


async def activate_subscription(org_id: str, payment_id: str, actor: str = "razorpay", plan_id: str | None = None, order_id: str | None = None):
    return await apply_payment(org_id, payment_id, actor=actor, plan_id=plan_id, order_id=order_id)


STORE_PLATFORMS = ("android_store", "ios_store")


def payment_matches(pay: dict, rec: dict) -> bool:
    """A signed payment must belong to this exact order, for the expected amount/currency, and be successful."""
    return (pay.get("order_id") == rec.get("order_id") and pay.get("currency") == rec.get("currency", "INR")
            and int(pay.get("amount") or 0) == int(round((rec.get("amount") or 0) * 100))
            and pay.get("status") in ("captured", "authorized"))


def require_billing_role(user: dict):
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "Only the gym owner or an admin can manage billing.")


def block_store_clients(request: Request):
    if request.headers.get("X-Client-Platform", "").lower() in STORE_PLATFORMS:
        raise HTTPException(403, "Subscriptions can't be purchased in the mobile app.")


@router.post("/subscription/verify")
async def verify_payment(body: VerifyBody, user: dict = Depends(get_org_user)):
    require_billing_role(user)
    _, key_secret = await get_razorpay_keys()
    if not key_secret:
        raise HTTPException(503, "Payments are not configured")
    expected = hmac.new(key_secret.encode(), f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, "Payment verification failed")
    rec = await db.subscription_payments.find_one({"order_id": body.razorpay_order_id, "organisation_id": user["organisation_id"]})
    if not rec:
        raise HTTPException(404, "Order not found")
    try:
        pay, _ = await razorpay_request("GET", f"/payments/{body.razorpay_payment_id}")
    except HTTPException:
        raise HTTPException(400, "Payment could not be verified with Razorpay")
    if not payment_matches(pay, rec):
        raise HTTPException(400, "Payment does not match this order")
    await activate_subscription(user["organisation_id"], body.razorpay_payment_id, actor=user["id"], plan_id=rec.get("plan_id"), order_id=body.razorpay_order_id)
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    return {"message": "Subscription activated", "subscription": derive_subscription(org, await get_plan_price())}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    settings = await db.settings.find_one({"id": "platform"}) or {}
    webhook_secret = settings.get("razorpay_webhook_secret") or os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    payload = await request.body()
    if not webhook_secret:
        logger.error("Razorpay webhook received but RAZORPAY_WEBHOOK_SECRET is not configured; rejecting")
        raise HTTPException(503, "Webhook secret not configured")
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Invalid webhook signature")
    import json
    event = json.loads(payload)
    event_name = event.get("event", "")
    if not await claim_event(request.headers.get("X-Razorpay-Event-Id", ""), event_name):
        return {"status": "duplicate"}
    try:
        if event_name.startswith("subscription."):
            return {"status": await handle_subscription_event(event_name, event)}
        if event_name.startswith("payment."):
            return {"status": await handle_payment_event(event_name, event)}
        return {"status": "ignored"}
    except Exception:
        await release_event(request.headers.get("X-Razorpay-Event-Id", ""))
        raise


# ---------------- Auto-debit subscriptions (UPI Autopay / card recurring) ----------------

async def get_or_create_rzp_plan(plan: dict) -> str:
    cache_id = "razorpay_plan_cache" if plan["id"] == "monthly" else f"razorpay_plan_cache_{plan['id']}"
    price = plan["effective_price"]
    key_id = (await get_razorpay_keys())[0]
    cache = await db.settings.find_one({"id": cache_id}) or {}
    if cache.get("price") == price and cache.get("plan_id") and cache.get("key_id") == key_id:
        return cache["plan_id"]
    data, _ = await razorpay_request("POST", "/plans", {
        "period": "monthly",
        "interval": plan["months"],
        "item": {"name": f"GymBoss_VVO {plan['name']}", "amount": price * 100, "currency": "INR"},
    })
    await db.settings.update_one({"id": cache_id}, {"$set": {"price": price, "plan_id": data["id"], "key_id": key_id}}, upsert=True)
    return data["id"]


async def reusable_subscription(sub: dict, key_id: str) -> bool:
    if sub.get("key_id", key_id) != key_id:
        return False
    try:
        data, _ = await razorpay_request("GET", f"/subscriptions/{sub['razorpay_subscription_id']}")
    except HTTPException:
        return False
    return data.get("status") in ("created", "authenticated", "active")


@router.post("/subscription/autodebit/start")
async def autodebit_start(request: Request, body: PlanChoice | None = None, user: dict = Depends(get_org_user)):
    block_store_clients(request)
    require_billing_role(user)
    org_id = user["organisation_id"]
    plan = await get_pricing_plan(body.plan_id if body else None)
    price = plan["effective_price"]
    plan_id = await get_or_create_rzp_plan(plan)
    existing = await db.subscriptions.find_one({"organisation_id": org_id, "status": {"$in": ["created", "active"]}})
    key_id = (await get_razorpay_keys())[0]
    if existing and existing["status"] == "created" and (existing.get("plan_id") != plan_id or not await reusable_subscription(existing, key_id)):
        await db.subscriptions.update_one({"id": existing["id"]}, {"$set": {"status": "abandoned"}})
        existing = None
    await track("payment_initiated", org_id, user["id"], props={"plan": plan["id"], "amount": price, "mode": "autodebit"})
    if existing:
        return {"subscription_id": existing["razorpay_subscription_id"], "key_id": key_id, "amount": price * 100, "currency": "INR", "status": existing["status"]}
    data, key_id = await razorpay_request("POST", "/subscriptions", {
        "plan_id": plan_id,
        "total_count": max(1, 120 // plan["months"]),
        "quantity": 1,
        "customer_notify": 0,
        "notes": {"org_id": org_id},
    })
    await db.subscriptions.insert_one({
        "id": new_id(), "organisation_id": org_id, "razorpay_subscription_id": data["id"],
        "plan_id": plan_id, "plan_key": plan["id"], "amount": price, "status": "created", "key_id": key_id, "created_at": now_utc(),
    })
    await audit(user["id"], "subscription.autodebit_started", org_id, {"rzp_subscription": data["id"]}, org_id)
    return {"subscription_id": data["id"], "key_id": key_id, "amount": price * 100, "currency": "INR", "status": "created"}


class AutodebitVerifyBody(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


@router.post("/subscription/autodebit/verify")
async def autodebit_verify(body: AutodebitVerifyBody, user: dict = Depends(get_org_user)):
    require_billing_role(user)
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
    price = sub.get("amount") or await get_plan_price()
    await record_autodebit_payment(sub, body.razorpay_payment_id, None, "autodebit")
    await audit(user["id"], "subscription.autodebit_activated", user["organisation_id"], {"rzp_subscription": body.razorpay_subscription_id}, user["organisation_id"])
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    return {"message": "Auto-debit activated", "subscription": derive_subscription(org, price)}


@router.post("/subscription/autodebit/cancel")
async def autodebit_cancel(user: dict = Depends(get_org_user)):
    require_billing_role(user)
    org_id = user["organisation_id"]
    sub = await db.subscriptions.find_one({"organisation_id": org_id, "status": {"$in": ["active", "created", "authenticated", "pending", "halted", "paused"]}})
    if not sub:
        raise HTTPException(404, "No active auto-debit subscription found")
    await razorpay_request("POST", f"/subscriptions/{sub['razorpay_subscription_id']}/cancel")
    await db.subscriptions.update_one({"id": sub["id"]}, {"$set": {"status": "cancelled", "cancelled_at": now_utc()}})
    await audit(user["id"], "subscription.autodebit_cancelled", org_id, {"rzp_subscription": sub["razorpay_subscription_id"]}, org_id)
    return {"message": "Auto-debit cancelled. Your access continues until the end of the paid period."}


@router.post("/internal/billing/reconcile")
async def reconcile_cron(request: Request):
    secret = os.environ.get("CRON_SECRET", "")
    if not secret or not hmac.compare_digest(request.headers.get("X-Cron-Secret", ""), secret):
        raise HTTPException(403, "Forbidden")
    return await reconcile(razorpay_request)


@router.post("/admin/billing/reconcile")
async def reconcile_admin(user: dict = Depends(require_super_admin)):
    return await reconcile(razorpay_request)


@router.get("/subscription/payments/{payment_id}/invoice.pdf")
async def subscription_invoice(payment_id: str, user: dict = Depends(get_org_user)):
    from fastapi import Response
    from receipt_pdf import build_saas_invoice_pdf
    rec = await db.subscription_payments.find_one({"id": payment_id, "organisation_id": user["organisation_id"], "status": "paid"}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Invoice not found")
    org = await db.organisations.find_one({"id": user["organisation_id"]}, {"_id": 0, "name": 1, "city": 1})
    plan = await get_pricing_plan(rec.get("plan_id"))
    pdf = build_saas_invoice_pdf(rec, org or {}, plan)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="GymBoss-Invoice-{payment_id[:8]}.pdf"'})
