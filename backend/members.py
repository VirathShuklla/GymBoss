"""Members & catalogue: plans, member CRUD, freeze/renew, payments, receipts, attendance,
batches, member-code generation, and tenant-scoped file uploads."""
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, Field

from deps import (
    db, now_utc, today_ist, new_id, get_org_user, require_write, get_current_user, audit,
    add_duration, member_status, days_left, member_public,
    next_receipt_no, next_member_code, normalize_phone, put_object, get_object,
)

router = APIRouter(tags=["members"])


# ---------------- Plans & Catalogue ----------------

class PlanBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    type: str = Field(default="membership")
    category: Optional[str] = None
    duration_type: Optional[str] = "months"
    duration: Optional[int] = 1
    price: float = Field(ge=0)
    sessions: Optional[int] = None
    inventory: Optional[int] = None
    trainer: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"


@router.get("/plans")
async def list_plans(type: Optional[str] = None, user: dict = Depends(get_org_user)):
    q = {"organisation_id": user["organisation_id"], "status": {"$ne": "archived"}}
    if type:
        q["$or"] = [{"type": type}, {"type": {"$exists": False}, "category": type}]
    plans = await db.plans.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return plans


@router.post("/plans")
async def create_plan(body: PlanBody, user: dict = Depends(require_write)):
    if body.type not in ("membership", "pt", "service", "product"):
        raise HTTPException(422, "Invalid plan type")
    doc = {"id": new_id(), "organisation_id": user["organisation_id"], **body.model_dump(), "created_at": now_utc()}
    await db.plans.insert_one(doc)
    await db.organisations.update_one({"id": user["organisation_id"]}, {"$set": {"onboarding.plan": True}})
    doc.pop("_id", None)
    return doc


@router.put("/plans/{plan_id}")
async def update_plan(plan_id: str, body: PlanBody, user: dict = Depends(require_write)):
    res = await db.plans.update_one(
        {"id": plan_id, "organisation_id": user["organisation_id"]},
        {"$set": {**body.model_dump(), "updated_at": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Plan not found")
    return await db.plans.find_one({"id": plan_id}, {"_id": 0})


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, user: dict = Depends(require_write)):
    res = await db.plans.update_one(
        {"id": plan_id, "organisation_id": user["organisation_id"]},
        {"$set": {"status": "archived", "updated_at": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Plan not found")
    await audit(user["id"], "plan.deleted", plan_id, org_id=user["organisation_id"])
    return {"message": "Plan deleted"}


# ---------------- Members ----------------

class MemberBody(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=10, max_length=15)
    email: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    joining_date: Optional[str] = None
    plan_id: str
    membership_start: Optional[str] = None
    batch: Optional[str] = None
    trainer: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    photo_url: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    admission_amount: float = 0
    payment_date: Optional[str] = None
    discount: float = 0
    amount_paid: float = 0
    payment_method: str = "Cash"
    notes: Optional[str] = None
    outlet_id: Optional[str] = None


async def create_membership(user: dict, body: MemberBody, enquiry_id: str | None = None) -> dict:
    org_id = user["organisation_id"]
    plan = await db.plans.find_one({"id": body.plan_id, "organisation_id": org_id})
    if not plan:
        raise HTTPException(404, "Membership plan not found")
    phone = normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(422, "Enter a valid 10-digit mobile number")
    outlet_id = body.outlet_id or (user.get("org_doc") or {}).get("primary_outlet_id")
    if not outlet_id:
        outlet_doc = await db.outlets.find_one({"organisation_id": org_id, "is_primary": True}) or await db.outlets.find_one({"organisation_id": org_id})
        outlet_id = outlet_doc["id"]
    start = date.fromisoformat((body.membership_start or body.joining_date or today_ist().isoformat())[:10])
    expiry = add_duration(start, plan.get("duration_type") or "months", plan.get("duration") or 1)
    price = plan.get("price", 0)
    payable = max(0, round(price + body.admission_amount - body.discount, 2))
    due = max(0, round(payable - body.amount_paid, 2))
    payment_status = "Paid" if due == 0 else ("Partially Paid" if body.amount_paid > 0 else "Due")
    ts = now_utc()
    org_name = (user.get("org_doc") or {}).get("name", "Gym")
    member = {
        "id": new_id(),
        "organisation_id": org_id,
        "outlet_id": outlet_id,
        "member_code": await next_member_code(org_id, org_name),
        "full_name": body.full_name.strip(),
        "phone": f"+91{phone}",
        "email": (body.email or "").strip().lower() or None,
        "gender": body.gender,
        "dob": body.dob,
        "address": body.address,
        "joining_date": (body.joining_date or start.isoformat())[:10],
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "plan_price": price,
        "membership_start": start.isoformat(),
        "membership_expiry": expiry.isoformat(),
        "batch": body.batch,
        "trainer": body.trainer,
        "height": body.height,
        "weight": body.weight,
        "photo_url": body.photo_url,
        "attachment_url": body.attachment_url,
        "attachment_name": body.attachment_name,
        "discount": body.discount,
        "admission_amount": body.admission_amount,
        "payable": payable,
        "payment_status": payment_status,
        "due_amount": due,
        "notes": body.notes,
        "frozen_until": None,
        "freeze_history": [],
        "whatsapp_opt_in": True,
        "created_at": ts,
        "deleted_at": None,
    }
    await db.members.insert_one(member)
    if body.batch:
        await db.batches.update_one(
            {"organisation_id": org_id, "name": body.batch.strip()},
            {"$setOnInsert": {"id": new_id(), "organisation_id": org_id, "name": body.batch.strip(), "created_at": ts}},
            upsert=True,
        )
    if body.amount_paid > 0:
        await db.payments.insert_one({
            "id": new_id(),
            "organisation_id": org_id,
            "outlet_id": outlet_id,
            "member_id": member["id"],
            "member_name": member["full_name"],
            "type": "admission",
            "plan_name": plan["name"],
            "amount": body.amount_paid,
            "discount": body.discount,
            "admission_amount": body.admission_amount,
            "payment_date": body.payment_date or today_ist().isoformat(),
            "method": body.payment_method,
            "receipt_no": await next_receipt_no(org_id),
            "created_at": ts,
            "created_by": user["id"],
        })
        await db.organisations.update_one({"id": org_id}, {"$set": {"onboarding.payment": True}})
    await db.organisations.update_one({"id": org_id}, {"$set": {"onboarding.member": True}})
    if enquiry_id:
        await db.enquiries.update_one({"id": enquiry_id, "organisation_id": org_id}, {"$set": {"status": "Converted", "converted_member_id": member["id"]}})
    await audit(user["id"], "member.created", member["id"], {"name": member["full_name"]}, org_id)
    return member_public(member)


@router.post("/members")
async def create_member(body: MemberBody, enquiry_id: Optional[str] = None, user: dict = Depends(require_write)):
    return await create_membership(user, body, enquiry_id)


@router.get("/members/next-code")
async def next_code(user: dict = Depends(get_org_user)):
    org = user.get("org_doc") or {}
    prefix = "".join(w[0] for w in (org.get("name") or "GB").split())[:3].upper() or "GB"
    doc = await db.counters.find_one({"_id": f"member:{user['organisation_id']}"})
    seq = ((doc or {}).get("seq") or 0) + 1
    return {"member_code": f"{prefix}-{1000 + seq}"}


@router.get("/batches")
async def list_batches(user: dict = Depends(get_org_user)):
    return await db.batches.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).sort("name", 1).to_list(200)


@router.get("/members")
async def list_members(
    search: Optional[str] = None,
    search_field: Optional[str] = None,
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    gender: Optional[str] = None,
    batch: Optional[str] = None,
    outlet_id: Optional[str] = None,
    due: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_org_user),
):
    q = {"organisation_id": user["organisation_id"], "deleted_at": None}
    if outlet_id:
        q["outlet_id"] = outlet_id
    if plan_id:
        q["plan_id"] = plan_id
    if gender and gender != "all":
        q["gender"] = gender
    if batch and batch != "all":
        q["batch"] = batch
    if search:
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        if search_field == "phone":
            q["phone"] = rx
        elif search_field == "code":
            q["member_code"] = rx
        elif search_field == "name":
            q["full_name"] = rx
        else:
            q["$or"] = [{"full_name": rx}, {"phone": rx}, {"member_code": rx}]
    members = await db.members.find(q).sort("created_at", -1).to_list(10000)
    items = [member_public(m) for m in members]
    if status and status != "all":
        items = [m for m in items if m["status"] == status]
    if due:
        items = [m for m in items if (m.get("due_amount") or 0) > 0]
    total = len(items)
    start_i = (max(page, 1) - 1) * limit
    return {"items": items[start_i:start_i + limit], "total": total, "page": page, "limit": limit}


@router.get("/members/{member_id}")
async def get_member(member_id: str, user: dict = Depends(get_org_user)):
    m = await db.members.find_one({"id": member_id, "organisation_id": user["organisation_id"], "deleted_at": None})
    if not m:
        raise HTTPException(404, "Member not found")
    payments = await db.payments.find({"member_id": member_id, "organisation_id": user["organisation_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    attendance = await db.attendance.find({"member_id": member_id, "organisation_id": user["organisation_id"]}, {"_id": 0}).sort("check_in", -1).to_list(50)
    return {"member": member_public(m), "payments": payments, "attendance": attendance}


class MemberUpdateBody(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    batch: Optional[str] = None
    trainer: Optional[str] = None
    notes: Optional[str] = None
    outlet_id: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    photo_url: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None


@router.put("/members/{member_id}")
async def update_member(member_id: str, body: MemberUpdateBody, user: dict = Depends(require_write)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "phone" in updates:
        p = normalize_phone(updates["phone"])
        if len(p) != 10:
            raise HTTPException(422, "Enter a valid 10-digit mobile number")
        updates["phone"] = f"+91{p}"
    if "full_name" in updates:
        updates["full_name"] = updates["full_name"].strip()
    updates["updated_at"] = now_utc()
    res = await db.members.update_one({"id": member_id, "organisation_id": user["organisation_id"], "deleted_at": None}, {"$set": updates})
    if not res.matched_count:
        raise HTTPException(404, "Member not found")
    if updates.get("batch"):
        await db.batches.update_one(
            {"organisation_id": user["organisation_id"], "name": updates["batch"].strip()},
            {"$setOnInsert": {"id": new_id(), "organisation_id": user["organisation_id"], "name": updates["batch"].strip(), "created_at": now_utc()}},
            upsert=True,
        )
    m = await db.members.find_one({"id": member_id})
    return member_public(m)


@router.delete("/members/{member_id}")
async def delete_member(member_id: str, user: dict = Depends(require_write)):
    res = await db.members.update_one(
        {"id": member_id, "organisation_id": user["organisation_id"], "deleted_at": None},
        {"$set": {"deleted_at": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Member not found")
    await audit(user["id"], "member.deleted", member_id, org_id=user["organisation_id"])
    return {"message": "Member deleted"}


class FreezeBody(BaseModel):
    freeze_from: str
    freeze_until: str
    reason: Optional[str] = None
    extend_expiry: bool = True


@router.post("/members/{member_id}/freeze")
async def freeze_member(member_id: str, body: FreezeBody, user: dict = Depends(require_write)):
    m = await db.members.find_one({"id": member_id, "organisation_id": user["organisation_id"], "deleted_at": None})
    if not m:
        raise HTTPException(404, "Member not found")
    f_from = date.fromisoformat(body.freeze_from[:10])
    f_until = date.fromisoformat(body.freeze_until[:10])
    if f_until < f_from:
        raise HTTPException(422, "Freeze-until must be after freeze-from")
    days = (f_until - f_from).days
    expiry = date.fromisoformat(str(m["membership_expiry"])[:10])
    new_expiry = expiry + timedelta(days=days) if body.extend_expiry else expiry
    entry = {"freeze_from": f_from.isoformat(), "freeze_until": f_until.isoformat(), "reason": body.reason, "days": days, "created_at": now_utc().isoformat()}
    await db.members.update_one(
        {"id": member_id},
        {"$set": {"frozen_until": f_until.isoformat(), "membership_expiry": new_expiry.isoformat()}, "$push": {"freeze_history": entry}},
    )
    await audit(user["id"], "member.frozen", member_id, {"days": days}, user["organisation_id"])
    updated = await db.members.find_one({"id": member_id})
    return member_public(updated)


@router.post("/members/{member_id}/unfreeze")
async def unfreeze_member(member_id: str, user: dict = Depends(require_write)):
    res = await db.members.update_one(
        {"id": member_id, "organisation_id": user["organisation_id"], "deleted_at": None},
        {"$set": {"frozen_until": None}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Member not found")
    m = await db.members.find_one({"id": member_id})
    return member_public(m)


class RenewBody(BaseModel):
    plan_id: str
    discount: float = 0
    amount_paid: float = 0
    payment_method: str = "Cash"


@router.post("/members/{member_id}/renew")
async def renew_member(member_id: str, body: RenewBody, user: dict = Depends(require_write)):
    org_id = user["organisation_id"]
    m = await db.members.find_one({"id": member_id, "organisation_id": org_id, "deleted_at": None})
    if not m:
        raise HTTPException(404, "Member not found")
    plan = await db.plans.find_one({"id": body.plan_id, "organisation_id": org_id})
    if not plan:
        raise HTTPException(404, "Plan not found")
    today = today_ist()
    expiry = date.fromisoformat(str(m["membership_expiry"])[:10])
    start = max(today, expiry)
    new_expiry = add_duration(start, plan.get("duration_type") or "months", plan.get("duration") or 1)
    price = plan.get("price", 0)
    payable = max(0, round(price - body.discount, 2))
    due = max(0, round(payable - body.amount_paid, 2))
    payment_status = "Paid" if due == 0 else ("Partially Paid" if body.amount_paid > 0 else "Due")
    ts = now_utc()
    await db.members.update_one({"id": member_id}, {"$set": {
        "plan_id": plan["id"], "plan_name": plan["name"], "plan_price": price,
        "membership_start": start.isoformat(), "membership_expiry": new_expiry.isoformat(),
        "due_amount": due, "discount": body.discount, "admission_amount": 0,
        "payable": payable, "payment_status": payment_status, "frozen_until": None, "updated_at": ts,
    }})
    if body.amount_paid > 0:
        await db.payments.insert_one({
            "id": new_id(), "organisation_id": org_id, "outlet_id": m["outlet_id"],
            "member_id": member_id, "member_name": m["full_name"], "type": "renewal",
            "plan_name": plan["name"], "amount": body.amount_paid, "discount": body.discount,
            "method": body.payment_method, "receipt_no": await next_receipt_no(org_id),
            "created_at": ts, "created_by": user["id"],
        })
    await audit(user["id"], "member.renewed", member_id, {"plan": plan["name"]}, org_id)
    updated = await db.members.find_one({"id": member_id})
    return member_public(updated)


# ---------------- Payments ----------------

class PaymentBody(BaseModel):
    member_id: str
    amount: float = Field(gt=0)
    method: str = "Cash"
    notes: Optional[str] = None


@router.post("/payments")
async def record_payment(body: PaymentBody, user: dict = Depends(require_write)):
    org_id = user["organisation_id"]
    if body.method not in ("Cash", "UPI", "Card", "Bank Transfer", "Other"):
        raise HTTPException(422, "Invalid payment method")
    m = await db.members.find_one({"id": body.member_id, "organisation_id": org_id, "deleted_at": None})
    if not m:
        raise HTTPException(404, "Member not found")
    ts = now_utc()
    payment = {
        "id": new_id(), "organisation_id": org_id, "outlet_id": m["outlet_id"],
        "member_id": m["id"], "member_name": m["full_name"], "type": "due",
        "plan_name": m.get("plan_name"), "amount": body.amount, "method": body.method,
        "notes": body.notes, "receipt_no": await next_receipt_no(org_id),
        "created_at": ts, "created_by": user["id"],
    }
    await db.payments.insert_one(payment)
    new_due = max(0, round(m.get("due_amount", 0) - body.amount, 2))
    new_status = "Paid" if new_due == 0 else "Partially Paid"
    await db.members.update_one({"id": m["id"]}, {"$set": {"due_amount": new_due, "payment_status": new_status}})
    await db.organisations.update_one({"id": org_id}, {"$set": {"onboarding.payment": True}})
    await audit(user["id"], "payment.recorded", payment["id"], {"amount": body.amount, "member": m["full_name"]}, org_id)
    payment.pop("_id", None)
    payment["member_due_remaining"] = new_due
    return payment


@router.get("/payments")
async def list_payments(
    search: Optional[str] = None,
    method: Optional[str] = None,
    type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    outlet_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_org_user),
):
    q = {"organisation_id": user["organisation_id"]}
    if outlet_id:
        q["outlet_id"] = outlet_id
    if method:
        q["method"] = method
    if type:
        q["type"] = type
    if date_from:
        q["created_at"] = {"$gte": datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)}
    if date_to:
        q.setdefault("created_at", {})["$lt"] = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc) + timedelta(days=1)
    if search:
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        q["$or"] = [{"member_name": rx}, {"receipt_no": rx}]
    total = await db.payments.count_documents(q)
    items = await db.payments.find(q, {"_id": 0}).sort("created_at", -1).skip((max(page, 1) - 1) * limit).limit(limit).to_list(limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/payments/{payment_id}/receipt")
async def payment_receipt(payment_id: str, user: dict = Depends(get_org_user)):
    p = await db.payments.find_one({"id": payment_id, "organisation_id": user["organisation_id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Payment not found")
    m = await db.members.find_one({"id": p["member_id"]}, {"_id": 0})
    org = await db.organisations.find_one({"id": user["organisation_id"]}, {"_id": 0})
    outlet = await db.outlets.find_one({"id": p["outlet_id"]}, {"_id": 0})
    return {
        "payment": p,
        "member": {"full_name": m["full_name"], "member_code": m["member_code"], "phone": m["phone"], "due_amount": m.get("due_amount", 0), "membership_expiry": str(m.get("membership_expiry"))[:10]} if m else None,
        "gym": {"name": org.get("name"), "city": org.get("city")},
        "outlet": {"name": outlet.get("name")} if outlet else None,
    }


# ---------------- Attendance ----------------

class CheckInBody(BaseModel):
    member_id: Optional[str] = None
    query: Optional[str] = None


@router.post("/attendance/check-in")
async def check_in(body: CheckInBody, user: dict = Depends(get_org_user)):
    org_id = user["organisation_id"]
    m = None
    if body.member_id:
        m = await db.members.find_one({"id": body.member_id, "organisation_id": org_id, "deleted_at": None})
    elif body.query:
        rx = {"$regex": re.escape(body.query.strip()), "$options": "i"}
        m = await db.members.find_one({"organisation_id": org_id, "deleted_at": None, "$or": [{"full_name": rx}, {"phone": rx}, {"member_code": rx}]})
    if not m:
        raise HTTPException(404, "Member not found")
    today = today_ist()
    open_visit = await db.attendance.find_one({"member_id": m["id"], "check_out": None, "check_in": {"$gte": datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)}})
    if open_visit:
        raise HTTPException(409, f"{m['full_name']} is already checked in")
    doc = {
        "id": new_id(), "organisation_id": org_id, "outlet_id": m["outlet_id"],
        "member_id": m["id"], "member_name": m["full_name"], "member_code": m["member_code"],
        "check_in": now_utc(), "check_out": None,
    }
    await db.attendance.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.post("/attendance/{attendance_id}/check-out")
async def check_out(attendance_id: str, user: dict = Depends(get_org_user)):
    res = await db.attendance.update_one(
        {"id": attendance_id, "organisation_id": user["organisation_id"], "check_out": None},
        {"$set": {"check_out": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Open check-in not found")
    return await db.attendance.find_one({"id": attendance_id}, {"_id": 0})


@router.get("/attendance")
async def list_attendance(date_str: Optional[str] = None, outlet_id: Optional[str] = None, user: dict = Depends(get_org_user)):
    d = date.fromisoformat(date_str) if date_str else today_ist()
    start = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    end = start + timedelta(days=1)
    q = {"organisation_id": user["organisation_id"], "check_in": {"$gte": start, "$lt": end}}
    if outlet_id:
        q["outlet_id"] = outlet_id
    return await db.attendance.find(q, {"_id": 0}).sort("check_in", -1).to_list(1000)


@router.get("/attendance/history")
async def attendance_history(month: Optional[int] = None, year: Optional[int] = None, user: dict = Depends(get_org_user)):
    t = today_ist()
    month = month or t.month
    year = year or t.year
    start = datetime(year, month, 1, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    end = datetime(year + (month == 12), (month % 12) + 1, 1, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    records = await db.attendance.find(
        {"organisation_id": user["organisation_id"], "check_in": {"$gte": start, "$lt": end}}, {"_id": 0}
    ).sort("check_in", -1).to_list(5000)
    by_day = {}
    for r in records:
        day = (r["check_in"] + timedelta(hours=5, minutes=30)).date().isoformat()
        by_day[day] = by_day.get(day, 0) + 1
    daily = [{"date": k, "count": v} for k, v in sorted(by_day.items(), reverse=True)]
    return {"records": records[:200], "daily": daily, "total": len(records)}


# ---------------- File uploads (object storage) ----------------

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
}


@router.post("/uploads")
async def upload_file(request: Request, user: dict = Depends(require_write)):
    form = await request.form()
    file = form.get("file")
    kind = form.get("kind", "attachment")
    if not file or not getattr(file, "filename", None):
        raise HTTPException(422, "No file provided")
    data = await file.read()
    if not data:
        raise HTTPException(422, "Empty file")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 10 MB)")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    allowed = {"jpg", "jpeg", "png", "webp", "gif", "pdf"} if kind == "attachment" else {"jpg", "jpeg", "png", "webp"}
    if ext not in allowed:
        raise HTTPException(422, f"Only {', '.join(sorted(allowed))} files are allowed")
    content_type = file.content_type or MIME_TYPES.get(ext, "application/octet-stream")
    path = f"gymbossvvo/{user['organisation_id']}/{uuid.uuid4()}.{ext}"
    try:
        result = await put_object(path, data, content_type)
    except Exception:
        raise HTTPException(502, "Upload failed. Please try again.")
    doc = {
        "id": new_id(),
        "organisation_id": user["organisation_id"],
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "kind": kind,
        "is_deleted": False,
        "created_at": now_utc(),
    }
    await db.files.insert_one(doc)
    return {"id": doc["id"], "url": f"/api/files/{doc['id']}", "filename": file.filename}


@router.get("/files/{file_id}")
async def get_file(file_id: str, user: dict = Depends(get_current_user)):
    record = await db.files.find_one({"id": file_id, "is_deleted": False})
    if not record:
        raise HTTPException(404, "File not found")
    if user.get("role") != "super_admin" and user.get("organisation_id") != record.get("organisation_id"):
        raise HTTPException(403, "Not authorized")
    data, content_type = await get_object(record["storage_path"])
    return Response(content=data, media_type=record.get("content_type") or content_type)
