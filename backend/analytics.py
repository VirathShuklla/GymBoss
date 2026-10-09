"""Conversion analytics: first-party event tracking, onboarding milestones, Activated Trial,
super-admin funnel, and the owner-facing trial status (value created during trial)."""
import re
from datetime import timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

import jwt
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from deps import (
    db, now_utc, get_org_user, require_super_admin, derive_subscription, get_plan_price,
    get_jwt_secret, JWT_ALGORITHM, TRIAL_DAYS,
)

router = APIRouter(tags=["analytics"])

EVENTS = {
    "landing_visit": "Landing page visit",
    "hero_cta_click": "Hero CTA click",
    "demo_click": "Demo click",
    "pricing_viewed": "Pricing viewed",
    "pricing_cta_click": "Pricing CTA click",
    "signup_started": "Signup started",
    "signup_completed": "Signup completed",
    "gym_created": "Gym created",
    "membership_plan_created": "Membership plan created",
    "first_member_added": "First member added",
    "third_member_added": "Third member added",
    "first_payment_recorded": "First payment recorded",
    "excel_import_used": "Excel import used",
    "whatsapp_used": "WhatsApp feature used",
    "trial_activated": "Trial activated",
    "subscription_started": "Subscription started",
    "subscription_plan_selected": "Subscription plan selected",
    "payment_initiated": "Payment initiated",
    "payment_successful": "Payment successful",
    "payment_failed": "Payment failed",
}
CLIENT_EVENTS = {"landing_visit", "hero_cta_click", "demo_click", "pricing_viewed", "pricing_cta_click", "signup_started",
                 "whatsapp_used", "subscription_plan_selected", "payment_failed", "excel_import_used"}
DEFAULT_RULES = {"min_plans": 1, "min_members": 3, "min_payments": 1}


async def track(event: str, org_id: str | None = None, user_id: str | None = None, visitor_id: str | None = None,
                props: dict | None = None, once: bool = False):
    if once and org_id and await db.events.find_one({"event": event, "org_id": org_id}, {"_id": 1}):
        return
    await db.events.insert_one({"event": event, "org_id": org_id, "user_id": user_id, "visitor_id": visitor_id,
                                "props": props or {}, "created_at": now_utc()})


async def activation_rules() -> dict:
    s = await db.settings.find_one({"id": "platform"}, {"activation_rules": 1}) or {}
    return {**DEFAULT_RULES, **(s.get("activation_rules") or {})}


async def org_progress(org_id: str) -> dict:
    return {
        "plans": await db.plans.count_documents({"organisation_id": org_id}),
        "members": await db.members.count_documents({"organisation_id": org_id, "deleted_at": None}),
        "payments": await db.payments.count_documents({"organisation_id": org_id}),
    }


def meets(p: dict, r: dict) -> bool:
    return p["plans"] >= r["min_plans"] and p["members"] >= r["min_members"] and p["payments"] >= r["min_payments"]


async def after_change(org_id: str, user_id: str | None = None, plan_created: bool = False):
    """Emit onboarding milestones and mark the trial Activated once the rules are met."""
    if plan_created:
        await track("membership_plan_created", org_id, user_id)
    p = await org_progress(org_id)
    if p["members"] >= 1:
        await track("first_member_added", org_id, user_id, once=True)
    if p["members"] >= 3:
        await track("third_member_added", org_id, user_id, once=True)
    if p["payments"] >= 1:
        await track("first_payment_recorded", org_id, user_id, once=True)
    org = await db.organisations.find_one({"id": org_id}, {"activated_at": 1})
    if org and not org.get("activated_at") and meets(p, await activation_rules()):
        await db.organisations.update_one({"id": org_id}, {"$set": {"activated_at": now_utc()}})
        await track("trial_activated", org_id, user_id, once=True)


def _clean(v, n=120):
    return str(v)[:n] if v not in (None, "") else None


class EventBody(BaseModel):
    event: str
    visitor_id: Optional[str] = None
    path: Optional[str] = None
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    device: Optional[str] = None
    props: Optional[dict] = None


@router.post("/events")
async def ingest_event(body: EventBody, request: Request):
    if body.event not in CLIENT_EVENTS:
        return {"ok": False}
    org_id = user_id = None
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
            u = await db.users.find_one({"id": payload.get("sub")}, {"organisation_id": 1, "id": 1})
            if u:
                org_id, user_id = u.get("organisation_id"), u["id"]
        except jwt.PyJWTError:
            pass
    ref_host = urlparse(body.referrer).netloc if body.referrer else None
    props = {k: _clean(v) for k, v in {
        "path": body.path, "referrer": ref_host, "utm_source": body.utm_source, "utm_medium": body.utm_medium,
        "utm_campaign": body.utm_campaign, "device": body.device}.items() if v}
    props.update({k[:30]: _clean(v, 60) for k, v in list((body.props or {}).items())[:8]})
    await track(body.event, org_id, user_id, _clean(body.visitor_id, 64), props)
    return {"ok": True}


async def link_visitor(visitor_id: str | None, org_id: str, user_id: str):
    """Attach a visitor's pre-signup events to the new gym and record signup + gym creation."""
    first = None
    if visitor_id:
        await db.events.update_many({"visitor_id": visitor_id, "org_id": None}, {"$set": {"org_id": org_id}})
        first = await db.events.find_one({"visitor_id": visitor_id, "event": "landing_visit"}, sort=[("created_at", 1)])
    src = (first or {}).get("props", {})
    source = src.get("utm_source") or src.get("referrer") or ("direct" if first else None)
    await db.organisations.update_one({"id": org_id}, {"$set": {"visitor_id": visitor_id, "acquisition_source": source}})
    await track("signup_completed", org_id, user_id, visitor_id, {"source": source})
    await track("gym_created", org_id, user_id, visitor_id)


# ---------------- Owner: trial status & value created ----------------

@router.get("/trial/status")
async def trial_status(user: dict = Depends(get_org_user)):
    org = user["org_doc"]
    org_id = org["id"]
    sub = derive_subscription(org, await get_plan_price())
    started = org.get("subscription", {}).get("trial_started_at") or org.get("created_at")
    if started and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    day = max(1, (now_utc() - started).days + 1) if started else 1
    return {
        "status": sub["status"], "days_left": sub["trial_days_left"], "day_number": min(day, TRIAL_DAYS),
        "trial_days": TRIAL_DAYS, "from_price": sub["plan_price_inr"],
        "stats": {
            "members": await db.members.count_documents({"organisation_id": org_id, "deleted_at": None}),
            "payments": await db.payments.count_documents({"organisation_id": org_id}),
            "attendance": await db.attendance.count_documents({"organisation_id": org_id}),
            "renewals": await db.payments.count_documents({"organisation_id": org_id, "type": "renewal"}),
            "plans": await db.plans.count_documents({"organisation_id": org_id}),
        },
    }


# ---------------- Super admin: funnel ----------------

def _pct(a, b):
    return round(100 * a / b, 1) if b else None


@router.get("/admin/funnel")
async def admin_funnel(days: int = 30, user: dict = Depends(require_super_admin)):
    days = max(1, min(days, 365))
    now = now_utc()
    start = now - timedelta(days=days)
    rules = await activation_rules()

    async def uniq(event):
        return len(await db.events.distinct("visitor_id", {"event": event, "created_at": {"$gte": start}, "visitor_id": {"$ne": None}}))

    visitors = await uniq("landing_visit")
    signup_started = await uniq("signup_started")
    orgs = await db.organisations.find({"created_at": {"$gte": start}, "is_demo": {"$ne": True}},
                                       {"_id": 0, "id": 1, "name": 1, "city": 1, "subscription": 1, "activated_at": 1, "created_at": 1,
                                        "acquisition_source": 1}).to_list(10000)
    org_ids = [o["id"] for o in orgs]
    owners = len(await db.users.distinct("organisation_id", {"organisation_id": {"$in": org_ids}, "role": "owner"}))

    async def counts(coll, extra=None):
        rows = await db[coll].aggregate([{"$match": {"organisation_id": {"$in": org_ids}, **(extra or {})}},
                                         {"$group": {"_id": "$organisation_id", "n": {"$sum": 1}}}]).to_list(10000)
        return {r["_id"]: r["n"] for r in rows}

    plans, members, pays = await counts("plans"), await counts("members", {"deleted_at": None}), await counts("payments")
    subpays = await db.subscription_payments.aggregate([
        {"$match": {"organisation_id": {"$in": org_ids}, "status": "paid"}},
        {"$group": {"_id": "$organisation_id", "n": {"$sum": 1}, "first": {"$min": "$created_at"}}}]).to_list(10000)
    paid = {r["_id"]: r for r in subpays}
    price = await get_plan_price()
    activated = paying = retained = 0
    stuck = []
    for o in orgs:
        p = {"plans": plans.get(o["id"], 0), "members": members.get(o["id"], 0), "payments": pays.get(o["id"], 0)}
        sub = derive_subscription(o, price)
        is_act = bool(o.get("activated_at")) or meets(p, rules)
        is_paying = o["id"] in paid or sub["status"] == "active"
        activated += is_act
        paying += is_paying
        first = paid.get(o["id"], {}).get("first")
        if first is not None and first.tzinfo is None:
            first = first.replace(tzinfo=timezone.utc)
        if is_paying and (paid.get(o["id"], {}).get("n", 0) >= 2 or (sub["status"] == "active" and first and now - first >= timedelta(days=30))):
            retained += 1
        if sub["status"] == "trial" and not is_act:
            stuck.append({"id": o["id"], "name": o["name"], "city": o.get("city"), "days_left": sub["trial_days_left"], **p,
                          "missing": [m for m, ok in [("membership plan", p["plans"] >= rules["min_plans"]),
                                                      (f"{rules['min_members']} members", p["members"] >= rules["min_members"]),
                                                      ("a payment", p["payments"] >= rules["min_payments"])] if not ok]})

    stages = [
        ("visitors", "Visitors", "People who opened the landing page", visitors),
        ("signup_started", "Signup Started", "Opened the signup form and started typing", signup_started),
        ("registered", "Registered", "Created an account", owners),
        ("gym_created", "Gym Created", "Gym profile created (happens during signup)", len(orgs)),
        ("activated", "Activated Trial", f"Added {rules['min_plans']}+ plan, {rules['min_members']}+ members and {rules['min_payments']}+ payment", activated),
        ("paying", "Paying Customer", "Paid for a subscription", paying),
        ("retained", "Retained Customer", "Paid again, or still active 30+ days after first payment", retained),
    ]
    funnel, prev = [], None
    for key, label, desc, n in stages:
        funnel.append({"key": key, "label": label, "description": desc, "count": n,
                       "from_previous": _pct(n, prev) if prev is not None else None, "from_top": _pct(n, stages[0][3])})
        prev = n

    ev_rows = await db.events.aggregate([
        {"$match": {"created_at": {"$gte": start}}},
        {"$group": {"_id": "$event", "n": {"$sum": 1}, "v": {"$addToSet": {"$ifNull": ["$org_id", "$visitor_id"]}}}}]).to_list(100)
    ev = {r["_id"]: r for r in ev_rows}
    events = [{"event": k, "label": label, "count": ev.get(k, {}).get("n", 0), "unique": len(ev.get(k, {}).get("v", []))} for k, label in EVENTS.items()]

    daily = await db.events.aggregate([
        {"$match": {"created_at": {"$gte": start}, "event": {"$in": ["landing_visit", "signup_completed", "trial_activated", "payment_successful"]}}},
        {"$group": {"_id": {"d": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at", "timezone": "+05:30"}}, "e": "$event"}, "n": {"$sum": 1}}}]).to_list(5000)
    series = {}
    for r in daily:
        series.setdefault(r["_id"]["d"], {"date": r["_id"]["d"]})[r["_id"]["e"]] = r["n"]
    src_rows = await db.events.aggregate([
        {"$match": {"event": "landing_visit", "created_at": {"$gte": start}}},
        {"$group": {"_id": {"$ifNull": ["$props.utm_source", {"$ifNull": ["$props.referrer", "direct"]}]}, "v": {"$addToSet": "$visitor_id"}}},
        {"$project": {"n": {"$size": "$v"}}}, {"$sort": {"n": -1}}, {"$limit": 8}]).to_list(8)
    signups_by_src = {}
    for o in orgs:
        s = o.get("acquisition_source") or "unknown"
        signups_by_src[s] = signups_by_src.get(s, 0) + 1
    sources = [{"source": r["_id"] or "direct", "visitors": r["n"], "signups": signups_by_src.get(r["_id"] or "direct", 0)} for r in src_rows]

    cta = {k: next(e["unique"] for e in events if e["event"] == k) for k in ["hero_cta_click", "demo_click", "pricing_viewed", "pricing_cta_click"]}
    return {
        "days": days, "rules": rules, "funnel": funnel, "events": events,
        "daily": sorted(series.values(), key=lambda x: x["date"]), "sources": sources,
        "cta": {k: {"count": v, "rate": _pct(v, visitors)} for k, v in cta.items()},
        "stuck": sorted(stuck, key=lambda x: x["days_left"])[:25],
        "tracking_since": (await db.events.find_one({}, sort=[("created_at", 1)]) or {}).get("created_at"),
    }
