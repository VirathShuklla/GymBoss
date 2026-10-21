"""Member accounting: one invoice per membership cycle, payments allocated FIFO, credit for overpayment.
All ledger writes run inside a MongoDB transaction together with the balance recompute."""
import logging

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from deps import db, now_utc, new_id, run_txn, checkpoint

logger = logging.getLogger(__name__)

METHODS = ("Cash", "UPI", "Card", "Bank Transfer", "Other")
CYCLE_KINDS = ("admission", "renewal")


def validate_method(method: str):
    if method not in METHODS:
        raise HTTPException(422, "Invalid payment method")


async def membership_plan(org_id: str, plan_id: str) -> dict:
    plan = await db.plans.find_one({"id": plan_id, "organisation_id": org_id})
    if not plan:
        raise HTTPException(404, "Membership plan not found")
    if plan.get("status") == "archived" or plan.get("status") == "inactive":
        raise HTTPException(422, "This plan is archived. Choose an active plan.")
    if (plan.get("type") or plan.get("category") or "membership") != "membership":
        raise HTTPException(422, "Choose a membership plan")
    return plan


def cycle_payable(price: float, admission: float, discount: float) -> float:
    gross = round((price or 0) + (admission or 0), 2)
    if discount > gross:
        raise HTTPException(422, "Discount can't be more than the plan price plus admission charge")
    return round(gross - discount, 2)


async def create_invoice(s, org_id: str, member_id: str, kind: str, plan: dict | None, amount: float,
                         period_start: str | None, period_end: str | None, user_id: str | None) -> dict:
    inv = {"id": new_id(), "organisation_id": org_id, "member_id": member_id, "kind": kind,
           "plan_id": (plan or {}).get("id"), "plan_name": (plan or {}).get("name"), "amount": round(amount, 2),
           "paid": 0, "status": "open", "period_start": period_start, "period_end": period_end,
           "created_at": now_utc(), "created_by": user_id}
    if kind in CYCLE_KINDS and period_start:
        inv["cycle_key"] = period_start
    await db.member_invoices.insert_one(inv, session=s)
    inv.pop("_id", None)
    return inv


async def _payments_total(s, org_id: str, member_id: str) -> float:
    rows = await db.payments.aggregate([
        {"$match": {"organisation_id": org_id, "member_id": member_id}},
        {"$group": {"_id": None, "t": {"$sum": "$amount"}}},
    ], session=s).to_list(1)
    return round(rows[0]["t"], 2) if rows else 0.0


async def ensure_ledger(s, m: dict):
    """One-time migration: an opening invoice reproduces the pre-ledger balance exactly."""
    if m.get("ledger_v"):
        return
    paid = await _payments_total(s, m["organisation_id"], m["id"])
    opening = round(paid + (m.get("due_amount") or 0), 2)
    if opening > 0 and not await db.member_invoices.find_one({"member_id": m["id"], "kind": "opening"}, session=s):
        await db.member_invoices.insert_one({
            "id": new_id(), "organisation_id": m["organisation_id"], "member_id": m["id"], "kind": "opening",
            "plan_id": m.get("plan_id"), "plan_name": m.get("plan_name"), "amount": opening, "paid": 0, "status": "open",
            "period_start": m.get("membership_start"), "period_end": str(m.get("membership_expiry") or "")[:10] or None,
            "created_at": m.get("created_at") or now_utc(), "created_by": None,
        }, session=s)
        await checkpoint("ledger.after_opening_invoice")
    await db.members.update_one({"id": m["id"]}, {"$set": {"ledger_v": 1}}, session=s)
    m["ledger_v"] = 1


async def recompute(s, org_id: str, member_id: str) -> dict:
    """Recompute balances from invoices + payments. Must run inside the caller's transaction."""
    m = await db.members.find_one({"id": member_id, "organisation_id": org_id}, session=s)
    if not m:
        raise HTTPException(404, "Member not found")
    await ensure_ledger(s, m)
    invoices = await db.member_invoices.find(
        {"organisation_id": org_id, "member_id": member_id, "status": {"$ne": "void"}}, session=s
    ).sort("created_at", 1).to_list(None)
    paid_total = await _payments_total(s, org_id, member_id)
    charged = round(sum(i["amount"] for i in invoices), 2)
    left, alloc = paid_total, []
    for inv in invoices:
        p = round(max(0, min(inv["amount"], left)), 2)
        left = round(left - p, 2)
        alloc.append((inv, p))
    due = round(max(0, charged - paid_total), 2)
    credit = round(max(0, paid_total - charged), 2)
    cur_paid = alloc[-1][1] if alloc else 0
    status = "Paid" if due == 0 else ("Due" if cur_paid == 0 and paid_total <= 0 else "Partially Paid")
    await db.members.update_one({"id": member_id}, {
        "$set": {"due_amount": due, "credit_balance": credit, "payment_status": status, "total_charged": charged, "total_paid": paid_total},
        "$inc": {"ledger_rev": 1},
    }, session=s)
    for inv, p in alloc:
        st = "paid" if p >= inv["amount"] else ("partial" if p > 0 else "open")
        if inv.get("paid") != p or inv.get("status") != st:
            await db.member_invoices.update_one({"id": inv["id"]}, {"$set": {"paid": p, "status": st}}, session=s)
    return {"due_amount": due, "credit_balance": credit, "payment_status": status}


async def migrate_member(org_id: str, member_id: str):
    try:
        await run_txn(lambda s: recompute(s, org_id, member_id))
    except DuplicateKeyError:
        logger.info("Opening invoice for member %s was created by another worker", member_id)


async def migrate_all():
    async for m in db.members.find({"ledger_v": {"$exists": False}}, {"_id": 0, "id": 1, "organisation_id": 1}):
        await migrate_member(m["organisation_id"], m["id"])
