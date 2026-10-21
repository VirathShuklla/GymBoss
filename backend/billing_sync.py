"""Idempotent Razorpay → entitlement sync: payment ledger, webhook handling and daily reconciliation."""
import logging
from datetime import timedelta

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from deps import db, now_utc, new_id, audit, get_pricing_plan, get_plan_price
from analytics import track

logger = logging.getLogger(__name__)

SUB_STATUS = {
    "created": "created", "authenticated": "authenticated", "active": "active", "pending": "pending",
    "halted": "halted", "paused": "paused", "cancelled": "cancelled", "completed": "completed", "expired": "cancelled",
}
OPEN_SUB_STATUSES = ["created", "authenticated", "active", "pending", "halted", "paused"]


async def apply_payment(org_id: str, payment_id: str, actor: str = "razorpay", plan_id: str | None = None,
                        order_id: str | None = None):
    """Extend access exactly once per Razorpay payment_id. Returns new end date, or None if already applied."""
    if not payment_id:
        return None
    try:
        await db.subscription_ledger.insert_one({"payment_id": payment_id, "organisation_id": org_id, "order_id": order_id, "created_at": now_utc()})
    except DuplicateKeyError:
        return None
    try:
        return await _extend_access(org_id, payment_id, actor, plan_id, order_id)
    except Exception:
        await db.subscription_ledger.delete_one({"payment_id": payment_id})
        raise


async def _extend_access(org_id: str, payment_id: str, actor: str, plan_id: str | None, order_id: str | None):
    now = now_utc()
    org = await db.organisations.find_one({"id": org_id})
    if not org:
        await db.subscription_ledger.delete_one({"payment_id": payment_id})
        return None
    sub = org.get("subscription", {})
    plan = await get_pricing_plan(plan_id or sub.get("plan"))
    base = sub.get("subscription_ends_at")
    if base is not None and base.tzinfo is None:
        from datetime import timezone
        base = base.replace(tzinfo=timezone.utc)
    start = base if base and base > now else now
    ends = start + timedelta(days=30 * plan["months"])
    await db.organisations.update_one({"id": org_id}, {"$set": {
        "subscription.status": "active",
        "subscription.subscription_started_at": sub.get("subscription_started_at") or now,
        "subscription.subscription_ends_at": ends,
        "subscription.plan": plan["id"],
        "subscription.plan_months": plan["months"],
        "subscription.amount": plan["effective_price"],
        "subscription.billing_issue": False,
    }})
    if order_id:
        await db.subscription_payments.update_one(
            {"organisation_id": org_id, "order_id": order_id, "status": {"$ne": "paid"}},
            {"$set": {"status": "paid", "payment_id": payment_id, "paid_at": now}},
        )
    await audit(actor, "subscription.activated", org_id, {"payment_id": payment_id, "ends": ends.isoformat()}, org_id)
    await track("payment_successful", org_id, props={"payment_id": payment_id, "plan": plan["id"], "amount": plan["effective_price"]})
    await track("subscription_started", org_id, props={"plan": plan["id"]}, once=True)
    return ends


async def record_autodebit_payment(local: dict, payment_id: str, amount_paise: int | None, kind: str):
    """Upsert a paid autodebit payment row (verify + webhook may both report the same payment)."""
    ts = now_utc()
    amount = round(amount_paise / 100) if amount_paise else (local.get("amount") or await get_plan_price())
    await db.subscription_payments.update_one(
        {"payment_id": payment_id, "organisation_id": local["organisation_id"]},
        {"$setOnInsert": {"id": new_id(), "organisation_id": local["organisation_id"], "order_id": local["razorpay_subscription_id"],
                          "payment_id": payment_id, "amount": amount, "currency": "INR", "status": "paid", "kind": kind,
                          "plan_id": local.get("plan_key"), "created_at": ts, "paid_at": ts}},
        upsert=True,
    )
    await apply_payment(local["organisation_id"], payment_id, plan_id=local.get("plan_key"))


async def _set_sub_status(local: dict, status: str, extra: dict | None = None):
    await db.subscriptions.update_one({"id": local["id"]}, {"$set": {"status": status, "status_synced_at": now_utc(), **(extra or {})}})


async def _flag_billing_issue(local: dict, reason: str):
    org_id = local["organisation_id"]
    await db.organisations.update_one({"id": org_id}, {"$set": {"subscription.billing_issue": True}})
    recent = await db.subscription_payments.find_one({"organisation_id": org_id, "order_id": local["razorpay_subscription_id"], "status": "failed",
                                                      "created_at": {"$gt": now_utc() - timedelta(hours=24)}})
    if recent:
        return
    await db.subscription_payments.insert_one({
        "id": new_id(), "organisation_id": org_id, "order_id": local["razorpay_subscription_id"], "amount": local.get("amount"),
        "currency": "INR", "status": "failed", "kind": "autodebit_renewal", "failure_reason": reason, "created_at": now_utc(),
    })
    await audit("razorpay", f"subscription.{reason}", org_id, {"rzp_subscription": local["razorpay_subscription_id"]}, org_id)
    await track("payment_failed", org_id, props={"source": "autodebit", "reason": reason})


async def handle_subscription_event(event_name: str, event: dict) -> str:
    payload = event.get("payload", {})
    entity = payload.get("subscription", {}).get("entity", {})
    local = await db.subscriptions.find_one({"razorpay_subscription_id": entity.get("id")})
    if not local:
        return "unknown_subscription"
    pay = payload.get("payment", {}).get("entity", {})
    kind = event_name.split(".", 1)[1]
    if kind in ("authenticated", "activated", "resumed"):
        await _set_sub_status(local, "active" if kind != "authenticated" else "authenticated", {"activated_at": local.get("activated_at") or now_utc()})
        if pay.get("id") and pay.get("status") == "captured":
            await record_autodebit_payment(local, pay["id"], pay.get("amount"), "autodebit")
    elif kind == "charged":
        await _set_sub_status(local, "active", {"last_charged_at": now_utc()})
        if pay.get("id"):
            await record_autodebit_payment(local, pay["id"], pay.get("amount"), "autodebit_renewal")
    elif kind in ("pending", "halted"):
        await _set_sub_status(local, kind)
        await _flag_billing_issue(local, f"renewal_{kind}")
    elif kind == "paused":
        await _set_sub_status(local, "paused")
    elif kind in ("cancelled", "completed"):
        await _set_sub_status(local, "cancelled" if kind == "cancelled" else "completed", {"cancelled_at": now_utc()})
        await audit("razorpay", f"subscription.{kind}", local["organisation_id"], {"rzp_subscription": local["razorpay_subscription_id"]}, local["organisation_id"])
    elif kind == "updated" and entity.get("plan_id"):
        await db.subscriptions.update_one({"id": local["id"]}, {"$set": {"plan_id": entity["plan_id"]}})
    return "processed"


async def handle_payment_event(event_name: str, event: dict) -> str:
    entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = entity.get("order_id")
    record = await db.subscription_payments.find_one({"order_id": order_id}) if order_id else None
    if not record:
        return "ignored"
    if event_name == "payment.captured":
        from billing import payment_matches
        if not payment_matches(entity, record):
            logger.error("payment.captured mismatch for order %s; not applied", order_id)
            return "mismatch"
        await apply_payment(record["organisation_id"], entity.get("id", ""), plan_id=record.get("plan_id"), order_id=order_id)
    elif event_name == "payment.failed" and record.get("status") != "paid":
        await db.subscription_payments.update_one({"order_id": order_id, "status": {"$ne": "paid"}},
                                                  {"$set": {"status": "failed", "failure_reason": entity.get("error_reason") or entity.get("error_description")}})
        await track("payment_failed", record["organisation_id"], props={"order_id": order_id, "source": "webhook"})
    return "processed"


async def claim_event(event_id: str, event_name: str) -> bool:
    """False if this webhook event was already processed (Razorpay retries / duplicate deliveries)."""
    if not event_id:
        return True
    try:
        await db.webhook_events.insert_one({"event_id": event_id, "event": event_name, "received_at": now_utc()})
        return True
    except DuplicateKeyError:
        return False


async def release_event(event_id: str):
    if event_id:
        await db.webhook_events.delete_one({"event_id": event_id})


async def reconcile(razorpay_request) -> dict:
    """Pull truth from Razorpay for open subscriptions and recent unpaid orders. Safe to run repeatedly."""
    stats = {"subscriptions_checked": 0, "status_updates": 0, "payments_applied": 0, "orders_checked": 0, "errors": 0}
    async for local in db.subscriptions.find({"status": {"$in": OPEN_SUB_STATUSES}}):
        stats["subscriptions_checked"] += 1
        sid = local["razorpay_subscription_id"]
        try:
            remote, _ = await razorpay_request("GET", f"/subscriptions/{sid}")
            invoices, _ = await razorpay_request("GET", f"/invoices?subscription_id={sid}&count=100")
        except HTTPException:
            stats["errors"] += 1
            created = local.get("created_at")
            if local["status"] == "created" and created and created.replace(tzinfo=None) < (now_utc() - timedelta(days=7)).replace(tzinfo=None):
                await _set_sub_status(local, "abandoned")
            continue
        status = SUB_STATUS.get(remote.get("status"), local["status"])
        if status != local["status"]:
            await _set_sub_status(local, status)
            stats["status_updates"] += 1
            if status in ("pending", "halted"):
                await _flag_billing_issue(local, f"renewal_{status}")
        for inv in invoices.get("items", []):
            if inv.get("status") == "paid" and inv.get("payment_id"):
                before = await db.subscription_ledger.count_documents({"payment_id": inv["payment_id"]})
                await record_autodebit_payment(local, inv["payment_id"], inv.get("amount_paid") or inv.get("amount"), "autodebit_renewal")
                stats["payments_applied"] += 0 if before else 1
    now = now_utc()
    async for rec in db.subscription_payments.find({"status": "created", "order_id": {"$regex": "^order_"},
                                                    "created_at": {"$gt": now - timedelta(days=3), "$lt": now - timedelta(minutes=10)}}):
        stats["orders_checked"] += 1
        try:
            pays, _ = await razorpay_request("GET", f"/orders/{rec['order_id']}/payments")
        except HTTPException:
            stats["errors"] += 1
            continue
        items = pays.get("items", [])
        captured = next((p for p in items if p.get("status") == "captured"), None)
        if captured:
            if await apply_payment(rec["organisation_id"], captured["id"], plan_id=rec.get("plan_id"), order_id=rec["order_id"]):
                stats["payments_applied"] += 1
        elif items and all(p.get("status") == "failed" for p in items):
            await db.subscription_payments.update_one({"id": rec["id"]}, {"$set": {"status": "failed"}})
    await db.settings.update_one({"id": "billing_reconcile"}, {"$set": {"last_run_at": now, "last_stats": stats}}, upsert=True)
    logger.info("Billing reconcile: %s", stats)
    return stats
