"""Idempotent Razorpay → entitlement sync: payment ledger, webhook handling and daily reconciliation."""
import logging
from datetime import timedelta, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from deps import db, now_utc, new_id, audit, get_pricing_plan, get_plan_price, run_txn, checkpoint, best_effort
from analytics import track

logger = logging.getLogger(__name__)

SUB_STATUS = {
    "created": "created", "authenticated": "authenticated", "active": "active", "pending": "pending",
    "halted": "halted", "paused": "paused", "cancelled": "cancelled", "completed": "completed", "expired": "cancelled",
}
OPEN_SUB_STATUSES = ["created", "authenticated", "active", "pending", "halted", "paused"]
BILLABLE_SUB_STATUSES = OPEN_SUB_STATUSES + ["abandoned"]
REMOTE_ENDED = ("cancelled", "completed", "expired")
EVENT_LEASE = timedelta(minutes=5)


async def apply_payment(org_id: str, payment_id: str, actor: str = "razorpay", plan_id: str | None = None,
                        order_id: str | None = None, payment_row: dict | None = None):
    """Extend access exactly once per Razorpay payment_id, atomically with its ledger entry and payment row.
    Returns the new end date, or None if already applied."""
    if not payment_id:
        return None

    async def txn(s):
        if payment_row:
            await db.subscription_payments.update_one(
                {"payment_id": payment_id, "organisation_id": org_id}, {"$setOnInsert": payment_row}, upsert=True, session=s)
        if await db.subscription_ledger.find_one({"payment_id": payment_id}, session=s):
            return None
        org = await db.organisations.find_one({"id": org_id}, session=s)
        if not org:
            return None
        now = now_utc()
        await db.subscription_ledger.insert_one({"payment_id": payment_id, "organisation_id": org_id, "order_id": order_id,
                                                 "status": "applied", "created_at": now}, session=s)
        await checkpoint("subscription.after_ledger")
        sub = org.get("subscription", {})
        plan = await get_pricing_plan(plan_id or sub.get("plan"))
        base = sub.get("subscription_ends_at")
        if base is not None and base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        ends = (base if base and base > now else now) + timedelta(days=30 * plan["months"])
        await db.organisations.update_one({"id": org_id}, {"$set": {
            "subscription.status": "active",
            "subscription.subscription_started_at": sub.get("subscription_started_at") or now,
            "subscription.subscription_ends_at": ends,
            "subscription.plan": plan["id"],
            "subscription.plan_months": plan["months"],
            "subscription.amount": plan["effective_price"],
            "subscription.billing_issue": False,
        }}, session=s)
        await checkpoint("subscription.after_grant")
        if order_id:
            await db.subscription_payments.update_one(
                {"organisation_id": org_id, "order_id": order_id, "status": {"$ne": "paid"}},
                {"$set": {"status": "paid", "payment_id": payment_id, "paid_at": now}}, session=s,
            )
        await checkpoint("subscription.after_payment_row")
        return ends, plan

    try:
        res = await run_txn(txn)
    except DuplicateKeyError:
        return None
    if not res:
        return None
    ends, plan = res
    await best_effort(audit(actor, "subscription.activated", org_id, {"payment_id": payment_id, "ends": ends.isoformat()}, org_id))
    await best_effort(track("payment_successful", org_id, props={"payment_id": payment_id, "plan": plan["id"], "amount": plan["effective_price"]}))
    await best_effort(track("subscription_started", org_id, props={"plan": plan["id"]}, once=True))
    return ends


async def record_autodebit_payment(local: dict, payment_id: str, amount_paise: int | None, kind: str):
    """Paid autodebit payment row + access grant in one transaction (verify + webhook may both report it)."""
    ts = now_utc()
    amount = round(amount_paise / 100) if amount_paise else (local.get("amount") or await get_plan_price())
    row = {"id": new_id(), "organisation_id": local["organisation_id"], "order_id": local["razorpay_subscription_id"],
           "payment_id": payment_id, "amount": amount, "currency": "INR", "status": "paid", "kind": kind,
           "plan_id": local.get("plan_key"), "created_at": ts, "paid_at": ts}
    await apply_payment(local["organisation_id"], payment_id, plan_id=local.get("plan_key"), payment_row=row)


async def cancel_remote_subscription(razorpay_request, sub: dict, reason: str) -> bool:
    """Cancel at Razorpay with a durable op record. True only once Razorpay confirms it can no longer bill."""
    rzp_id, org_id = sub["razorpay_subscription_id"], sub["organisation_id"]
    op_id = f"cancel_subscription:{rzp_id}"
    now = now_utc()
    await db.razorpay_ops.update_one({"id": op_id}, {"$setOnInsert": {
        "id": op_id, "kind": "cancel_subscription", "organisation_id": org_id, "target": rzp_id, "local_id": sub["id"],
        "reason": reason, "status": "pending", "attempts": 0, "created_at": now}}, upsert=True)
    remote_status, error = None, None
    try:
        data, _ = await razorpay_request("POST", f"/subscriptions/{rzp_id}/cancel")
        remote_status = data.get("status")
    except Exception as e:
        error = f"cancel failed: {getattr(e, 'detail', None) or e}"
    if remote_status not in REMOTE_ENDED:
        try:
            data, _ = await razorpay_request("GET", f"/subscriptions/{rzp_id}")
            remote_status = data.get("status")
        except Exception as e:
            error = f"{error or ''} status check failed: {getattr(e, 'detail', None) or e}".strip()
    confirmed = remote_status in REMOTE_ENDED
    await db.razorpay_ops.update_one({"id": op_id}, {
        "$set": {"status": "succeeded" if confirmed else "failed", "remote_status": remote_status,
                 "last_error": None if confirmed else (error or f"Razorpay status is {remote_status}"), "last_attempt_at": now},
        "$inc": {"attempts": 1}})
    if confirmed:
        await db.subscriptions.update_one({"id": sub["id"]}, {"$set": {"status": "cancelled", "cancelled_at": now}})
    else:
        logger.error("Razorpay cancellation of %s not confirmed: %s", rzp_id, error or remote_status)
    return confirmed


async def retry_pending_cancellations(razorpay_request) -> int:
    done = 0
    async for op in db.razorpay_ops.find({"kind": "cancel_subscription", "status": {"$in": ["pending", "failed"]}}):
        sub = await db.subscriptions.find_one({"id": op["local_id"]}) or {
            "id": op["local_id"], "razorpay_subscription_id": op["target"], "organisation_id": op["organisation_id"]}
        done += 1 if await cancel_remote_subscription(razorpay_request, sub, op.get("reason") or "retry") else 0
    return done


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


async def claim_event(event_id: str, event_name: str) -> str:
    """'new' = process it; 'duplicate' = already done; 'busy' = another worker holds a fresh lease.
    A crashed or failed claim is re-claimable, so a webhook is never silently skipped."""
    if not event_id:
        return "new"
    now = now_utc()
    try:
        await db.webhook_events.insert_one({"event_id": event_id, "event": event_name, "status": "processing",
                                            "claimed_at": now, "attempts": 1, "received_at": now})
        return "new"
    except DuplicateKeyError:
        pass
    reclaimed = await db.webhook_events.find_one_and_update(
        {"event_id": event_id, "$or": [{"status": "failed"}, {"status": "processing", "claimed_at": {"$lt": now - EVENT_LEASE}}]},
        {"$set": {"status": "processing", "claimed_at": now}, "$inc": {"attempts": 1}},
    )
    if reclaimed:
        return "new"
    existing = await db.webhook_events.find_one({"event_id": event_id}) or {}
    return "busy" if existing.get("status") == "processing" else "duplicate"


async def finish_event(event_id: str, ok: bool, error: str | None = None):
    if event_id:
        await db.webhook_events.update_one({"event_id": event_id}, {"$set": {
            "status": "done" if ok else "failed", "finished_at": now_utc(), "last_error": error}})


async def reconcile(razorpay_request) -> dict:
    """Pull truth from Razorpay for open subscriptions and recent unpaid orders. Safe to run repeatedly."""
    stats = {"subscriptions_checked": 0, "status_updates": 0, "payments_applied": 0, "orders_checked": 0, "errors": 0,
             "cancellations_confirmed": await retry_pending_cancellations(razorpay_request)}
    from server import resume_purges
    await resume_purges()
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
    await db.subscription_payments.update_many({"status": "created", "created_at": {"$lt": now - timedelta(days=3)}}, {"$set": {"status": "expired"}})
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
