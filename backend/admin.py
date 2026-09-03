import re
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from deps import db, now_utc, require_super_admin, derive_subscription, audit, get_plan_price, PLAN_PRICE_INR

router = APIRouter(tags=["super-admin"])


@router.get("/admin/overview")
async def admin_overview(user: dict = Depends(require_super_admin)):
    orgs = await db.organisations.find({}, {"subscription": 1, "created_at": 1}).to_list(10000)
    trial = paying = expired = cancelled = 0
    for org in orgs:
        status = derive_subscription(org)["status"]
        if status == "trial":
            trial += 1
        elif status == "active":
            paying += 1
        elif status in ("expired", "payment_due"):
            expired += 1
        elif status == "cancelled":
            cancelled += 1
    cutoff = now_utc() - timedelta(days=30)
    new_signups = sum(1 for o in orgs if o.get("created_at") and o["created_at"].replace(tzinfo=None) >= cutoff.replace(tzinfo=None))
    sub_revenue_docs = await db.subscription_payments.find({"status": "paid"}, {"amount": 1}).to_list(10000)
    revenue = sum(p.get("amount", 0) for p in sub_revenue_docs)
    ended = paying + expired + cancelled
    return {
        "total_gyms": len(orgs),
        "trial": trial,
        "paying": paying,
        "expired": expired,
        "cancelled": cancelled,
        "new_signups_30d": new_signups,
        "mrr": paying * await get_plan_price(),
        "subscription_revenue": revenue,
        "trial_to_paid": round(100 * paying / ended, 1) if ended else 0,
    }


@router.get("/admin/gyms")
async def admin_gyms(search: Optional[str] = None, user: dict = Depends(require_super_admin)):
    q = {}
    if search:
        q["name"] = {"$regex": re.escape(search.strip()), "$options": "i"}
    orgs = await db.organisations.find(q).sort("created_at", -1).to_list(1000)
    result = []
    for org in orgs:
        owner = await db.users.find_one({"organisation_id": org["id"], "role": "owner"}, {"_id": 0, "full_name": 1, "email": 1, "phone": 1})
        member_count = await db.members.count_documents({"organisation_id": org["id"], "deleted_at": None})
        last_payment = await db.subscription_payments.find_one({"organisation_id": org["id"], "status": "paid"}, {"_id": 0, "amount": 1, "paid_at": 1}, sort=[("paid_at", -1)])
        result.append({
            "id": org["id"],
            "name": org.get("name"),
            "city": org.get("city"),
            "is_demo": bool(org.get("is_demo")),
            "disabled": bool(org.get("disabled")),
            "created_at": org.get("created_at").isoformat() if org.get("created_at") else None,
            "owner": owner,
            "member_count": member_count,
            "subscription": derive_subscription(org),
            "last_payment": last_payment,
        })
    return result


@router.get("/admin/gyms/{org_id}")
async def admin_gym_detail(org_id: str, user: dict = Depends(require_super_admin)):
    org = await db.organisations.find_one({"id": org_id}, {"_id": 0, "onboarding": 0})
    if not org:
        raise HTTPException(404, "Gym not found")
    org["created_at"] = org["created_at"].isoformat() if org.get("created_at") else None
    owner = await db.users.find_one({"organisation_id": org_id, "role": "owner"}, {"_id": 0, "full_name": 1, "email": 1, "phone": 1, "created_at": 1})
    if owner and owner.get("created_at"):
        owner["created_at"] = owner["created_at"].isoformat()
    outlets = await db.outlets.find({"organisation_id": org_id}, {"_id": 0, "id": 1, "name": 1, "city": 1, "status": 1}).to_list(50)
    members = await db.members.count_documents({"organisation_id": org_id, "deleted_at": None})
    staff = await db.staff.count_documents({"organisation_id": org_id})
    payments = await db.payments.find({"organisation_id": org_id}, {"amount": 1}).to_list(10000)
    sub_payments = await db.subscription_payments.find({"organisation_id": org_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for p in sub_payments:
        for k in ("created_at", "paid_at"):
            if p.get(k):
                p[k] = p[k].isoformat()
    return {
        "organisation": org,
        "owner": owner,
        "outlets": outlets,
        "stats": {"members": members, "staff": staff, "collection_total": sum(p.get("amount", 0) for p in payments)},
        "subscription": derive_subscription(org),
        "subscription_payments": sub_payments,
    }


@router.post("/admin/gyms/{org_id}/toggle")
async def admin_toggle_gym(org_id: str, user: dict = Depends(require_super_admin)):
    org = await db.organisations.find_one({"id": org_id})
    if not org:
        raise HTTPException(404, "Gym not found")
    disabled = not org.get("disabled", False)
    await db.organisations.update_one({"id": org_id}, {"$set": {"disabled": disabled}})
    await audit(user["id"], "org.disabled" if disabled else "org.reactivated", org_id, {"gym": org.get("name")})
    return {"id": org_id, "disabled": disabled}


class PlatformSettingsBody(BaseModel):
    whatsapp_number: Optional[str] = ""
    support_email: Optional[str] = ""
    play_store_url: Optional[str] = ""
    app_store_url: Optional[str] = ""
    plan_price_inr: Optional[int] = None
    razorpay_key_id: Optional[str] = ""
    razorpay_key_secret: Optional[str] = ""
    razorpay_webhook_secret: Optional[str] = ""


@router.get("/admin/settings")
async def admin_get_settings(user: dict = Depends(require_super_admin)):
    settings = await db.settings.find_one({"id": "platform"}, {"_id": 0}) or {}
    return settings


@router.put("/admin/settings")
async def admin_update_settings(body: PlatformSettingsBody, user: dict = Depends(require_super_admin)):
    data = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "plan_price_inr" in data:
        if data["plan_price_inr"] is None or int(data["plan_price_inr"]) < 1:
            raise HTTPException(422, "Price must be at least ₹1")
        data["plan_price_inr"] = int(data["plan_price_inr"])
    if not data:
        return await db.settings.find_one({"id": "platform"}, {"_id": 0})
    await db.settings.update_one({"id": "platform"}, {"$set": data}, upsert=True)
    await audit(user["id"], "platform.settings_updated", "platform", {"keys": [k for k, v in data.items() if v]})
    return await db.settings.find_one({"id": "platform"}, {"_id": 0})


@router.get("/admin/audit-logs")
async def admin_audit_logs(limit: int = 100, user: dict = Depends(require_super_admin)):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 500))
    for log in logs:
        if log.get("created_at"):
            log["created_at"] = log["created_at"].isoformat()
    return logs
