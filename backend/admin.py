"""BuildVVO super-admin console: platform overview, gyms list/detail, disable/reactivate,
platform settings (price + Razorpay keys), and audit logs."""
import csv
import io
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from deps import db, now_utc, require_super_admin, derive_subscription, audit, get_plan_price, get_pricing_plans, org_mrr, PLAN_PRICE_INR

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


def _naive(dt):
    """Coerce datetime or ISO string to a naive datetime for safe comparison/bucketing."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt


def _health(status, last_activity_days, members):
    """Customer health from signals we actually track: subscription status, recency of
    activity (last member payment / member added), and whether any members exist.
    (No login/WhatsApp/attendance tracking exists, so those are intentionally not used.)"""
    if status == "cancelled":
        return "churned", 0
    if status in ("expired", "payment_due"):
        return "high_risk", 20
    score = 100
    if last_activity_days is None:
        score -= 45
    elif last_activity_days > 30:
        score -= 55
    elif last_activity_days > 14:
        score -= 30
    elif last_activity_days > 7:
        score -= 10
    if not members:
        score -= 25
    score = max(0, min(100, score))
    cat = "healthy" if score >= 70 else ("at_risk" if score >= 40 else "high_risk")
    return cat, score


@router.get("/admin/gyms")
async def admin_gyms(search: Optional[str] = None, status: Optional[str] = None, health: Optional[str] = None, user: dict = Depends(require_super_admin)):
    price = await get_plan_price()
    q = {}
    if search:
        q["name"] = {"$regex": re.escape(search.strip()), "$options": "i"}
    orgs = await db.organisations.find(q).sort("created_at", -1).to_list(2000)
    # One aggregation each (no N+1) for per-gym member & payment activity.
    pay_agg = {d["_id"]: d for d in await db.payments.aggregate([
        {"$group": {"_id": "$organisation_id", "cnt": {"$sum": 1}, "last": {"$max": "$created_at"}, "sum": {"$sum": "$amount"}}},
    ]).to_list(10000)}
    mem_agg = {d["_id"]: d for d in await db.members.aggregate([
        {"$match": {"deleted_at": None}}, {"$group": {"_id": "$organisation_id", "cnt": {"$sum": 1}, "last": {"$max": "$created_at"}}},
    ]).to_list(10000)}
    now = now_utc().replace(tzinfo=None)
    owners = {u["organisation_id"]: u for u in await db.users.find({"role": "owner"}, {"_id": 0, "full_name": 1, "email": 1, "phone": 1, "organisation_id": 1}).to_list(10000)}
    result = []
    for org in orgs:
        oid = org["id"]
        sub = derive_subscription(org, price)
        m = mem_agg.get(oid, {})
        p = pay_agg.get(oid, {})
        last_activity = max([x for x in [_naive(m.get("last")), _naive(p.get("last"))] if x], default=None)
        la_days = (now - last_activity).days if last_activity else None
        cat, score = _health(sub["status"], la_days, m.get("cnt", 0))
        result.append({
            "id": oid, "name": org.get("name"), "city": org.get("city"),
            "is_demo": bool(org.get("is_demo")), "disabled": bool(org.get("disabled")),
            "created_at": _naive(org.get("created_at")).isoformat() if org.get("created_at") else None,
            "owner": owners.get(oid), "member_count": m.get("cnt", 0),
            "subscription": sub,
            "monthly_revenue": org_mrr(sub, price),
            "collection_total": p.get("sum", 0),
            "last_activity": last_activity.isoformat() if last_activity else None,
            "last_activity_days": la_days,
            "health": cat, "health_score": score,
        })
    if status:
        result = [g for g in result if g["subscription"]["status"] == status]
    if health:
        result = [g for g in result if g["health"] == health]
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


class PricingPlanBody(BaseModel):
    id: str
    name: Optional[str] = None
    price: int
    offer_price: Optional[int] = None
    offer_label: Optional[str] = ""
    active: Optional[bool] = True


class PlatformSettingsBody(BaseModel):
    pricing_plans: Optional[List[PricingPlanBody]] = None
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
    settings["pricing_plans"] = await get_pricing_plans()
    return settings


@router.put("/admin/settings")
async def admin_update_settings(body: PlatformSettingsBody, user: dict = Depends(require_super_admin)):
    data = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "plan_price_inr" in data:
        if data["plan_price_inr"] is None or int(data["plan_price_inr"]) < 1:
            raise HTTPException(422, "Price must be at least ₹1")
        data["plan_price_inr"] = int(data["plan_price_inr"])
    if "pricing_plans" in data:
        plans = data["pricing_plans"] or []
        ids = {p["id"] for p in plans}
        if not ids <= {"monthly", "quarterly", "yearly"}:
            raise HTTPException(422, "Unknown plan")
        for p in plans:
            if p["price"] < 1:
                raise HTTPException(422, f"{p.get('name') or p['id']}: price must be at least ₹1")
            if p.get("offer_price") and not (1 <= p["offer_price"] < p["price"]):
                raise HTTPException(422, f"{p.get('name') or p['id']}: offer price must be lower than the regular price")
            p["offer_label"] = (p.get("offer_label") or "").strip()[:40]
            if p["id"] == "monthly":
                p["active"] = True
                data["plan_price_inr"] = p["price"]
    if data.get("razorpay_key_id"):
        kid = data["razorpay_key_id"].strip()
        if not kid.startswith(("rzp_test_", "rzp_live_")):
            raise HTTPException(422, "Razorpay Key ID must start with rzp_test_ or rzp_live_ — paste the Key ID from your Razorpay dashboard, not a link.")
        data["razorpay_key_id"] = kid
    if not data:
        return await db.settings.find_one({"id": "platform"}, {"_id": 0})
    await db.settings.update_one({"id": "platform"}, {"$set": data}, upsert=True)
    await audit(user["id"], "platform.settings_updated", "platform", {"keys": [k for k, v in data.items() if v]})
    return await admin_get_settings(user)


@router.get("/admin/churn-export")
async def admin_churn_export(health: str = "high_risk", user: dict = Depends(require_super_admin)):
    """CSV of churn-risk gyms for win-back campaigns."""
    levels = {"high_risk": ["high_risk"], "at_risk": ["at_risk"], "all_risk": ["high_risk", "at_risk"]}.get(health, ["high_risk"])
    gyms = [g for g in await admin_gyms(search=None, status=None, health=None, user=user) if g["health"] in levels and not g["is_demo"]]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Gym", "City", "Owner", "Email", "Phone", "Subscription Status", "Health", "Health Score",
                "Members", "Last Activity", "Days Since Activity", "Signed Up", "Trial Ends", "Subscription Ends"])
    for g in gyms:
        o, s = g.get("owner") or {}, g["subscription"]
        w.writerow([g["name"], g.get("city") or "", o.get("full_name", ""), o.get("email", ""), o.get("phone", ""),
                    s["status"], g["health"].replace("_", " ").title(), g["health_score"], g["member_count"],
                    (g.get("last_activity") or "")[:10], "" if g["last_activity_days"] is None else g["last_activity_days"],
                    (g.get("created_at") or "")[:10], (s.get("trial_ends_at") or "")[:10], (s.get("subscription_ends_at") or "")[:10]])
    await audit(user["id"], "admin.churn_export", "platform", {"rows": len(gyms), "health": health})
    fname = f"churn-watchlist-{now_utc().date().isoformat()}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(require_super_admin)):
    """All SaaS analytics from real data. Metrics we cannot source (marketing/CAC, website
    visitors, per-user logins, WhatsApp-sent, attendance, refunds) are omitted, not faked."""
    price = await get_plan_price()
    now = now_utc().replace(tzinfo=None)
    this_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    lm_start = (this_start - timedelta(days=1)).replace(day=1)

    orgs = await db.organisations.find({}, {"subscription": 1, "created_at": 1, "is_demo": 1, "name": 1}).to_list(10000)
    counts = {"trial": 0, "active": 0, "expired": 0, "payment_due": 0, "cancelled": 0}
    trials_today = trials_3d = trials_7d = 0
    mrr_total = 0
    for o in orgs:
        sd = derive_subscription(o, price)
        s = sd["status"]
        mrr_total += org_mrr(sd, price)
        counts[s] = counts.get(s, 0) + 1
        if s == "trial":
            te = _naive(o.get("subscription", {}).get("trial_ends_at"))
            if te:
                d = (te.date() - now.date()).days
                if d <= 0:
                    trials_today += 1
                if 0 <= d <= 3:
                    trials_3d += 1
                if 0 <= d <= 7:
                    trials_7d += 1
    paying, trial = counts["active"], counts["trial"]
    churned = counts["cancelled"] + counts["expired"] + counts["payment_due"]
    total = len(orgs)
    new_this = sum(1 for o in orgs if _naive(o.get("created_at")) and _naive(o["created_at"]) >= this_start)
    new_last = sum(1 for o in orgs if _naive(o.get("created_at")) and lm_start <= _naive(o["created_at"]) < this_start)

    # Last 12 month keys
    keys, yy, mm = [], this_start.year, this_start.month
    for _ in range(12):
        keys.append(f"{yy:04d}-{mm:02d}")
        mm -= 1
        if mm == 0:
            mm, yy = 12, yy - 1
    keys = list(reversed(keys))

    paid = await db.subscription_payments.find({"status": "paid"}, {"amount": 1, "paid_at": 1, "created_at": 1}).to_list(100000)
    rev_by = {k: 0 for k in keys}
    for p in paid:
        d = _naive(p.get("paid_at") or p.get("created_at"))
        if d and d.strftime("%Y-%m") in rev_by:
            rev_by[d.strftime("%Y-%m")] += p.get("amount", 0)
    signup_by = {k: 0 for k in keys}
    for o in orgs:
        d = _naive(o.get("created_at"))
        if d and d.strftime("%Y-%m") in signup_by:
            signup_by[d.strftime("%Y-%m")] += 1
    running = sum(1 for o in orgs if _naive(o.get("created_at")) and _naive(o["created_at"]).strftime("%Y-%m") < keys[0])
    series = []
    for k in keys:
        running += signup_by[k]
        series.append({"month": k, "revenue": rev_by[k], "new_customers": signup_by[k], "total_customers": running})

    rev_this, rev_last = rev_by[keys[-1]], rev_by[keys[-2]]
    rev_growth = round(100 * (rev_this - rev_last) / rev_last, 1) if rev_last else (100.0 if rev_this else 0.0)
    signup_growth = round(100 * (new_this - new_last) / new_last, 1) if new_last else (100.0 if new_this else 0.0)
    lifetime = sum(p.get("amount", 0) for p in paid)
    mrr = mrr_total
    ended = paying + churned
    churn_rate = round(100 * churned / ended, 1) if ended else 0.0
    retention = round(100 - churn_rate, 1)
    avg_lifetime_months = round(100 / churn_rate, 1) if churn_rate else None

    failed = await db.subscription_payments.count_documents({"status": "failed"})
    pending = await db.subscription_payments.count_documents({"status": "created"})
    success = len(paid)
    expired_subs = await db.subscriptions.count_documents({"status": {"$in": ["halted", "cancelled"]}})
    subs = await db.subscriptions.find({"status": "active"}, {"last_charged_at": 1}).to_list(10000)
    renew_week = 0
    for s in subs:
        lc = _naive(s.get("last_charged_at"))
        if lc and now <= lc + timedelta(days=30) <= now + timedelta(days=7):
            renew_week += 1

    # Product usage — real cross-tenant counts; "active gyms" uses member-payment recency as a
    # login proxy (we don't track logins), stated as such in the UI.
    total_members = await db.members.count_documents({"deleted_at": None})
    members_this = await db.members.count_documents({"deleted_at": None, "created_at": {"$gte": this_start}})
    member_payments = await db.payments.count_documents({})
    recent = await db.payments.find({"created_at": {"$gte": now - timedelta(days=30)}}, {"organisation_id": 1, "created_at": 1}).to_list(100000)
    dau, wau, mau = set(), set(), set()
    for p in recent:
        d, oid = _naive(p.get("created_at")), p.get("organisation_id")
        if not d or not oid:
            continue
        mau.add(oid)
        if d >= now - timedelta(days=7):
            wau.add(oid)
        if d >= now - timedelta(days=1):
            dau.add(oid)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=5, minutes=30)
    att_today = await db.attendance.count_documents({"check_in": {"$gte": today_start}})
    att_month = await db.attendance.count_documents({"check_in": {"$gte": this_start}})
    devices = await db.biometric_devices.count_documents({})

    return {
        "currency": "INR",
        "kpis": {
            "mrr": mrr, "arr": mrr * 12, "arpu": round(mrr / paying) if paying else 0,
            "total_customers": total, "paying": paying, "trial": trial,
            "expired": counts["expired"] + counts["payment_due"], "cancelled": counts["cancelled"],
            "new_this_month": new_this, "new_last_month": new_last, "signup_growth": signup_growth,
            "retention_rate": retention, "churn_rate": churn_rate,
            "trial_to_paid": round(100 * paying / ended, 1) if ended else 0.0,
            "avg_lifetime_months": avg_lifetime_months,
        },
        "revenue": {
            "this_month": rev_this, "last_month": rev_last, "growth": rev_growth,
            "current_mrr": mrr, "projected_arr": mrr * 12, "lifetime": lifetime,
        },
        "series": series,
        "funnel": {
            "registered": total, "trial_started": total,
            "paid": paying, "retained_30d": len(subs),
            "converted_trials": paying, "expired_trials": counts["expired"] + counts["payment_due"],
        },
        "trials": {"ending_today": trials_today, "ending_3d": trials_3d, "ending_7d": trials_7d, "active": trial},
        "payments": {
            "successful": success, "failed": failed, "pending": pending,
            "success_rate": round(100 * success / (success + failed), 1) if (success + failed) else 100.0,
            "renewals_this_week": renew_week, "expired_subscriptions": expired_subs,
            "revenue_collected": lifetime,
        },
        "usage": {
            "dau": len(dau), "wau": len(wau), "mau": len(mau),
            "total_members": total_members, "members_this_month": members_this,
            "member_payments": member_payments,
            "attendance_today": att_today, "attendance_month": att_month, "biometric_devices": devices,
        },
    }


@router.get("/admin/audit-logs")
async def admin_audit_logs(limit: int = 100, user: dict = Depends(require_super_admin)):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 500))
    for log in logs:
        if log.get("created_at"):
            log["created_at"] = log["created_at"].isoformat()
    return logs
