from dotenv import load_dotenv
load_dotenv()

import os
import re
import uuid
import secrets
import hashlib
import random
import logging
from html import escape
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List

import jwt
import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from deps import (
    db, now_utc, today_ist, new_id, normalize_phone, hash_password, verify_password,
    create_access_token, create_refresh_token, set_auth_cookies, get_current_user,
    get_org_user, derive_subscription, public_user, org_public, audit, init_storage,
    get_plan_price, TRIAL_DAYS, PLAN_PRICE_INR,
)
from members import router as members_router
from ops import router as ops_router
from comms import router as comms_router
from finance import router as finance_router
from billing import router as billing_router
from admin import router as admin_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="GymBoss_VVO API")
api = APIRouter(prefix="/api")

EMAIL_BASE_URL = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip().rstrip("/") or "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME") or "GymBoss_VVO"


# ---------------- Email (password reset only) ----------------

async def send_password_reset_email(to_email: str, token: str) -> bool:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{base}/reset-password?token={token}"
    if not EMAIL_KEY or EMAIL_KEY.startswith("{") or not base.startswith("https://"):
        if urlparse(base).hostname in ("localhost", "127.0.0.1", "::1"):
            logger.warning("Email not configured; password reset link: %s", link)
        else:
            logger.error("Password reset email not configured (EMERGENT_EMAIL_KEY / FRONTEND_URL)")
        return False
    brand = escape(EMAIL_FROM_NAME)
    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>We received a request to reset your {brand} password.</p>"
        f'<p><a href="{escape(link)}">Reset your password</a></p>'
        f"<p>This link expires in 1 hour and can be used once. If you did not request it, "
        f"ignore this email — your password is unchanged.</p>"
        f'<p style="font-size:12px;color:#888">Sent by {brand}. We never ask for your password by email.</p>'
        f"</td></tr></table>"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json={"to": [to_email], "subject": f"Reset your {EMAIL_FROM_NAME} password", "html": html, "from_name": EMAIL_FROM_NAME},
            )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
        return False


# ---------------- Request models ----------------

class RegisterBody(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=8, max_length=100)
    gym_name: str = Field(min_length=2, max_length=80)
    outlet_name: str = Field(min_length=2, max_length=80)
    city: Optional[str] = None


class LoginBody(BaseModel):
    identifier: str
    password: str


class ForgotBody(BaseModel):
    email: EmailStr


class ResetBody(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=100)


class OnboardingBody(BaseModel):
    plan: Optional[bool] = None
    member: Optional[bool] = None
    staff: Optional[bool] = None
    payment: Optional[bool] = None
    dismissed: Optional[bool] = None


# ---------------- Auth endpoints ----------------

@api.post("/auth/register")
async def register(body: RegisterBody, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    phone = normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(status_code=422, detail="Enter a valid 10-digit mobile number")
    ts = now_utc()
    org_id = new_id()
    outlet_id = new_id()
    org = {
        "id": org_id,
        "name": body.gym_name.strip(),
        "city": (body.city or "").strip() or None,
        "subscription": {"status": "trial", "trial_started_at": ts, "trial_ends_at": ts + timedelta(days=TRIAL_DAYS)},
        "onboarding": {"plan": False, "member": False, "staff": False, "payment": False, "dismissed": False},
        "created_at": ts,
    }
    outlet = {"id": outlet_id, "organisation_id": org_id, "name": body.outlet_name.strip(), "is_primary": True, "status": "active", "created_at": ts}
    user = {
        "id": new_id(),
        "full_name": body.full_name.strip(),
        "email": email,
        "phone": f"+91{phone}",
        "role": "owner",
        "organisation_id": org_id,
        "password_hash": hash_password(body.password),
        "token_version": 0,
        "status": "active",
        "created_at": ts,
    }
    await db.organisations.insert_one(org)
    await db.outlets.insert_one(outlet)
    await db.users.insert_one(user)
    await db.batches.insert_many([
        {"id": new_id(), "organisation_id": org_id, "name": "Morning (6–9 AM)", "created_at": ts},
        {"id": new_id(), "organisation_id": org_id, "name": "Evening (4–9 PM)", "created_at": ts},
    ])
    await audit(user["id"], "org.registered", org_id, {"gym": org["name"]}, org_id)
    set_auth_cookies(response, user)
    return {"user": public_user(user), "organisation": org_public(org)}


async def find_user_by_identifier(identifier: str) -> Optional[dict]:
    ident = (identifier or "").strip()
    user = await db.users.find_one({"username": ident})
    if not user:
        user = await db.users.find_one({"email": ident.lower()})
    if not user:
        digits = normalize_phone(ident)
        if len(digits) == 10:
            user = await db.users.find_one({"phone": f"+91{digits}"})
    if user:
        user.pop("_id", None)
    return user


@api.post("/auth/login")
async def login(body: LoginBody, request: Request, response: Response):
    ident = body.identifier.strip()
    xff = request.headers.get("x-forwarded-for", "")
    ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")
    lock_key = f"{ip}:{ident.lower()}"
    cutoff = now_utc() - timedelta(minutes=15)
    ip_attempts = await db.login_attempts.count_documents({"identifier": lock_key, "created_at": {"$gt": cutoff}})
    id_attempts = await db.login_attempts.count_documents({"email": ident.lower(), "created_at": {"$gt": cutoff}})
    if ip_attempts >= 5 or id_attempts >= 10:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    user = await find_user_by_identifier(ident)
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.insert_one({"identifier": lock_key, "email": ident.lower(), "created_at": now_utc()})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("status") == "disabled":
        raise HTTPException(status_code=403, detail="This account has been disabled.")
    await db.login_attempts.delete_many({"$or": [{"identifier": lock_key}, {"email": ident.lower()}]})
    set_auth_cookies(response, user)
    return {"user": public_user(user)}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user or payload.get("ver", 0) != user.get("token_version", 0):
        raise HTTPException(status_code=401, detail="Session expired")
    response.set_cookie("access_token", create_access_token(user), httponly=True, secure=True, samesite="none", max_age=1800, path="/")
    return {"message": "refreshed"}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    org = None
    outlets = []
    if user.get("organisation_id"):
        org = await db.organisations.find_one({"id": user["organisation_id"]})
        outlets = await db.outlets.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).to_list(50)
    return {
        "user": public_user(user),
        "organisation": org_public(org) if org else None,
        "outlets": outlets,
        "subscription": derive_subscription(org, await get_plan_price()),
    }


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotBody, request: Request, background_tasks: BackgroundTasks):
    generic = {"message": "If that email is registered, a reset link has been sent."}
    email = body.email.lower().strip()
    xff = request.headers.get("x-forwarded-for", "")
    ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")
    cutoff = now_utc() - timedelta(minutes=15)
    email_recent = await db.password_reset_requests.count_documents({"email": email, "created_at": {"$gt": cutoff}})
    ip_recent = await db.password_reset_requests.count_documents({"ip": ip, "created_at": {"$gt": cutoff}})
    if email_recent >= 5 or ip_recent >= 15:
        return generic
    await db.password_reset_requests.insert_one({"email": email, "ip": ip, "created_at": now_utc()})
    user = await db.users.find_one({"email": email})
    if not user:
        return generic
    token = secrets.token_urlsafe(32)
    await db.password_reset_tokens.insert_one({
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "user_id": user["id"],
        "email": email,
        "expires_at": now_utc() + timedelta(hours=1),
        "used": False,
    })
    background_tasks.add_task(send_password_reset_email, user["email"], token)
    return generic


@api.post("/auth/reset-password")
async def reset_password(body: ResetBody):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    doc = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": token_hash, "used": False, "expires_at": {"$gt": now_utc()}},
        {"$set": {"used": True}},
    )
    if not doc:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    await db.users.update_one({"id": doc["user_id"]}, {"$set": {"password_hash": hash_password(body.password)}, "$inc": {"token_version": 1}})
    await db.password_reset_tokens.delete_many({"user_id": doc["user_id"], "used": False})
    await db.login_attempts.delete_many({"email": doc["email"]})
    return {"message": "Password updated. You can now log in."}


# ---------------- Public config ----------------

@api.get("/public/config")
async def public_config():
    settings = await db.settings.find_one({"id": "platform"}) or {}
    return {
        "whatsapp_number": settings.get("whatsapp_number") or os.environ.get("SUPPORT_WHATSAPP", ""),
        "support_email": settings.get("support_email") or os.environ.get("SUPPORT_EMAIL", ""),
        "play_store_url": settings.get("play_store_url") or "",
        "app_store_url": settings.get("app_store_url") or "",
        "trial_days": TRIAL_DAYS,
        "plan_price_inr": await get_plan_price(),
    }


# ---------------- App: outlets / onboarding ----------------

@api.get("/outlets")
async def list_outlets(user: dict = Depends(get_org_user)):
    return await db.outlets.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).to_list(50)


@api.get("/onboarding")
async def get_onboarding(user: dict = Depends(get_org_user)):
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    return (org or {}).get("onboarding", {})


@api.put("/onboarding")
async def update_onboarding(body: OnboardingBody, user: dict = Depends(get_org_user)):
    updates = {f"onboarding.{k}": v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.organisations.update_one({"id": user["organisation_id"]}, {"$set": updates})
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    return (org or {}).get("onboarding", {})


# ---------------- Dashboard ----------------

def day_bounds(d: date):
    from deps import IST
    start = datetime(d.year, d.month, d.day, tzinfo=IST)
    return start, start + timedelta(days=1)


@api.get("/dashboard/summary")
async def dashboard_summary(outlet_id: Optional[str] = None, user: dict = Depends(get_org_user)):
    org_id = user["organisation_id"]
    member_q = {"organisation_id": org_id, "deleted_at": None}
    pay_q = {"organisation_id": org_id}
    att_q = {"organisation_id": org_id}
    enq_q = {"organisation_id": org_id}
    if outlet_id:
        member_q["outlet_id"] = outlet_id
        pay_q["outlet_id"] = outlet_id
        att_q["outlet_id"] = outlet_id
        enq_q["outlet_id"] = outlet_id

    today = today_ist()
    start, end = day_bounds(today)

    payments_today = await db.payments.find({**pay_q, "created_at": {"$gte": start, "$lt": end}}).to_list(1000)
    today_collection = sum(p.get("amount", 0) for p in payments_today)
    today_online = sum(p.get("amount", 0) for p in payments_today if p.get("method") != "Cash")
    today_cash = sum(p.get("amount", 0) for p in payments_today if p.get("method") == "Cash")
    today_admissions = sum(1 for p in payments_today if p.get("type") == "admission")
    today_renewals = sum(1 for p in payments_today if p.get("type") == "renewal")
    due_paid_today = sum(p.get("amount", 0) for p in payments_today if p.get("type") == "due")
    today_enquiries = await db.enquiries.count_documents({**enq_q, "created_at": {"$gte": start, "$lt": end}})
    attendance_today = await db.attendance.count_documents({**att_q, "check_in": {"$gte": start, "$lt": end}})

    members = await db.members.find(member_q).to_list(10000)
    total_members = len(members)
    active = expiring_today = expiring_soon = due_members = birthdays = 0
    for m in members:
        expiry = m.get("membership_expiry")
        if isinstance(expiry, str):
            expiry = date.fromisoformat(expiry[:10])
        frozen_until = m.get("frozen_until")
        if isinstance(frozen_until, str):
            frozen_until = date.fromisoformat(frozen_until[:10])
        frozen = bool(frozen_until and frozen_until >= today)
        if not frozen and expiry and expiry >= today:
            active += 1
        if expiry == today:
            expiring_today += 1
        elif expiry and today < expiry <= today + timedelta(days=3):
            expiring_soon += 1
        if m.get("due_amount", 0) > 0:
            due_members += 1
        dob = m.get("dob")
        if isinstance(dob, str):
            try:
                dob = date.fromisoformat(dob[:10])
            except ValueError:
                dob = None
        if dob and dob.month == today.month and dob.day == today.day:
            birthdays += 1

    return {
        "today_collection": today_collection,
        "today_online": today_online,
        "today_cash": today_cash,
        "today_admissions": today_admissions,
        "today_renewals": today_renewals,
        "due_paid_today": due_paid_today,
        "today_enquiries": today_enquiries,
        "today_pt": 0,
        "today_service": 0,
        "today_product": 0,
        "active_members": active,
        "total_members": total_members,
        "due_members": due_members,
        "expiring_today": expiring_today,
        "expiring_1_3_days": expiring_soon,
        "birthdays_today": birthdays,
        "attendance_today": attendance_today,
    }


@api.get("/dashboard/recent-transactions")
async def recent_transactions(outlet_id: Optional[str] = None, user: dict = Depends(get_org_user)):
    q = {"organisation_id": user["organisation_id"]}
    if outlet_id:
        q["outlet_id"] = outlet_id
    return await db.payments.find(q, {"_id": 0}).sort("created_at", -1).to_list(10)


# ---------------- Seeding ----------------

DEMO_MEMBERS = [
    ("Aarav Sharma", "9876543201", "Male", "1994-03-12"),
    ("Priya Nair", "9876543202", "Female", "1996-07-24"),
    ("Rohan Verma", "9876543203", "Male", "1990-11-05"),
    ("Sneha Kulkarni", "9876543204", "Female", "1998-01-17"),
    ("Arjun Mehta", "9876543205", "Male", "1992-06-30"),
    ("Ishita Reddy", "9876543206", "Female", "1995-09-09"),
    ("Vikram Singh Rathore", "9876543207", "Male", "1988-12-01"),
    ("Ananya Iyer", "9876543208", "Female", "1997-04-21"),
    ("Kabir Malhotra", "9876543209", "Male", "1993-08-14"),
    ("Meera Joshi", "9876543210", "Female", "1999-02-28"),
    ("Aditya Deshmukh", "9876543211", "Male", "1991-10-11"),
    ("Kavya Pillai", "9876543212", "Female", "1996-05-06"),
    ("Nikhil Bansal", "9876543213", "Male", "1989-03-19"),
    ("Riya Chawla", "9876543214", "Female", "2000-07-07"),
    ("Sahil Khan", "9876543215", "Male", "1994-09-27"),
    ("Tanvi Bhatt", "9876543216", "Female", "1998-11-23"),
    ("Harsh Vardhan", "9876543217", "Male", "1992-01-15"),
    ("Divya Menon", "9876543218", "Female", "1995-06-02"),
    ("Manish Tiwari", "9876543219", "Male", "1987-08-25"),
    ("Pooja Hegde", "9876543220", "Female", "1997-12-13"),
    ("Rahul Naidu", "9876543221", "Male", "1993-04-04"),
    ("Shreya Saxena", "9876543222", "Female", "1999-10-29"),
    ("Varun Kapoor", "9876543223", "Male", "1990-02-16"),
    ("Nisha Rane", "9876543224", "Female", "1996-08-08"),
    ("Dev Patil", "9876543225", "Male", "1991-05-21"),
    ("Lakshmi Narayan", "9876543226", "Female", "1994-01-09"),
]


async def seed_super_admin():
    username = os.environ.get("SUPER_ADMIN_USERNAME", "GymBoss")
    password = os.environ.get("SUPER_ADMIN_PASSWORD", "GymBoss@2026")
    email = os.environ.get("SUPER_ADMIN_EMAIL", "").lower()
    existing = await db.users.find_one({"username": username})
    if not existing:
        await db.users.insert_one({
            "id": new_id(),
            "username": username,
            "email": email or None,
            "full_name": "BuildVVO Super Admin",
            "role": "super_admin",
            "organisation_id": None,
            "password_hash": hash_password(password),
            "token_version": 0,
            "status": "active",
            "created_at": now_utc(),
        })
        logger.info("Seeded super admin '%s'", username)
    elif not verify_password(password, existing["password_hash"]):
        await db.users.update_one({"username": username}, {"$set": {"password_hash": hash_password(password)}})


async def seed_demo():
    email = os.environ.get("DEMO_OWNER_EMAIL", "demo@gymbossvvo.in").lower()
    if await db.users.find_one({"email": email}):
        return
    password = os.environ.get("DEMO_OWNER_PASSWORD", "Demo@2026")
    ts = now_utc()
    today = today_ist()
    org_id = new_id()
    outlet1, outlet2 = new_id(), new_id()
    org = {
        "id": org_id,
        "name": "Iron Paradise Fitness",
        "city": "Bengaluru",
        "is_demo": True,
        "subscription": {"status": "trial", "trial_started_at": ts - timedelta(days=1), "trial_ends_at": ts + timedelta(days=TRIAL_DAYS - 1)},
        "onboarding": {"plan": True, "member": True, "staff": True, "payment": True, "dismissed": False},
        "created_at": ts - timedelta(days=1),
    }
    outlets = [
        {"id": outlet1, "organisation_id": org_id, "name": "Indiranagar", "city": "Bengaluru", "is_primary": True, "status": "active", "created_at": ts},
        {"id": outlet2, "organisation_id": org_id, "name": "HSR Layout", "city": "Bengaluru", "is_primary": False, "status": "active", "created_at": ts},
    ]
    owner = {
        "id": new_id(),
        "full_name": "Demo Owner",
        "email": email,
        "phone": "+919876500001",
        "role": "owner",
        "organisation_id": org_id,
        "password_hash": hash_password(password),
        "token_version": 0,
        "status": "active",
        "created_at": ts,
    }
    plans = [
        {"id": new_id(), "organisation_id": org_id, "name": "Monthly", "type": "membership", "category": "General", "duration_type": "months", "duration": 1, "price": 1500, "status": "active", "created_at": ts},
        {"id": new_id(), "organisation_id": org_id, "name": "Quarterly", "type": "membership", "category": "General", "duration_type": "months", "duration": 3, "price": 4000, "status": "active", "created_at": ts},
        {"id": new_id(), "organisation_id": org_id, "name": "Half-Yearly", "type": "membership", "category": "General", "duration_type": "months", "duration": 6, "price": 7000, "status": "active", "created_at": ts},
        {"id": new_id(), "organisation_id": org_id, "name": "Annual", "type": "membership", "category": "Premium", "duration_type": "months", "duration": 12, "price": 12000, "status": "active", "created_at": ts},
        {"id": new_id(), "organisation_id": org_id, "name": "PT — 12 Sessions", "type": "pt", "category": "Personal Training", "duration_type": "months", "duration": 1, "sessions": 12, "price": 6000, "status": "active", "created_at": ts},
        {"id": new_id(), "organisation_id": org_id, "name": "Steam & Sauna", "type": "service", "category": "Recovery", "price": 800, "status": "active", "created_at": ts},
        {"id": new_id(), "organisation_id": org_id, "name": "Whey Protein 1kg", "type": "product", "category": "Supplements", "price": 2400, "inventory": 15, "status": "active", "created_at": ts},
    ]
    rng = random.Random(42)
    members, payments, attendance = [], [], []
    receipt = 1000
    for i, (name, phone, gender, dob) in enumerate(DEMO_MEMBERS):
        outlet = outlet1 if i % 3 else outlet2
        plan = plans[i % 4]
        joined_days_ago = rng.randint(20, 300)
        joined = ts - timedelta(days=joined_days_ago)
        scenario = i % 10
        if scenario in (0, 1, 2, 3, 4, 5):
            expiry = today + timedelta(days=rng.randint(5, 90))
        elif scenario == 6:
            expiry = today
        elif scenario == 7:
            expiry = today + timedelta(days=rng.randint(1, 3))
        elif scenario == 8:
            expiry = today - timedelta(days=rng.randint(3, 40))
        else:
            expiry = today + timedelta(days=30)
        due = rng.choice([0, 0, 0, 500, 1000, plan["price"]]) if scenario in (7, 8) else rng.choice([0, 0, 0, 500])
        mid = new_id()
        members.append({
            "id": mid,
            "organisation_id": org_id,
            "outlet_id": outlet,
            "member_code": f"IPF-{1001 + i}",
            "full_name": name,
            "phone": f"+91{phone}",
            "email": f"{name.split()[0].lower()}{i}@example.in",
            "gender": gender,
            "dob": dob,
            "joining_date": (joined.date()).isoformat(),
            "plan_id": plan["id"],
            "plan_name": plan["name"],
            "plan_price": plan["price"],
            "membership_start": (expiry - timedelta(days=plan["duration"] * 30)).isoformat(),
            "membership_expiry": expiry.isoformat(),
            "due_amount": due,
            "frozen_until": (today + timedelta(days=10)).isoformat() if scenario == 9 else None,
            "freeze_history": [],
            "whatsapp_opt_in": True,
            "created_at": joined,
            "deleted_at": None,
        })
        n_payments = rng.randint(1, 3)
        for j in range(n_payments):
            receipt += 1
            pay_date = ts - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 10))
            payments.append({
                "id": new_id(),
                "organisation_id": org_id,
                "outlet_id": outlet,
                "member_id": mid,
                "member_name": name,
                "type": "admission" if j == 0 else rng.choice(["renewal", "renewal", "due"]),
                "plan_name": plan["name"],
                "amount": plan["price"] if j == 0 else rng.choice([plan["price"], due or 500, 1000]),
                "method": rng.choice(["Cash", "UPI", "UPI", "Card", "Bank Transfer"]),
                "receipt_no": f"RCPT-{receipt}",
                "created_at": pay_date,
            })
        if i < 12:
            attendance.append({
                "id": new_id(),
                "organisation_id": org_id,
                "outlet_id": outlet,
                "member_id": mid,
                "member_name": name,
                "member_code": f"IPF-{1001 + i}",
                "check_in": datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6 + i % 6, minutes=rng.randint(0, 59)) - timedelta(hours=5, minutes=30),
                "check_out": None,
            })
    for k, (name, method, amount, ptype) in enumerate([
        ("Aarav Sharma", "UPI", 1500, "renewal"),
        ("Riya Chawla", "Cash", 4000, "admission"),
        ("Sahil Khan", "UPI", 500, "due"),
    ]):
        receipt += 1
        m = next((x for x in members if x["full_name"] == name), members[0])
        payments.append({
            "id": new_id(),
            "organisation_id": org_id,
            "outlet_id": m["outlet_id"],
            "member_id": m["id"],
            "member_name": name,
            "type": ptype,
            "plan_name": m["plan_name"],
            "amount": amount,
            "method": method,
            "receipt_no": f"RCPT-{receipt}",
            "created_at": ts - timedelta(hours=2 + k),
        })
    enquiries = [
        {"name": "Kunal Thakur", "phone": "+919812345001", "category": "Membership", "status": "New", "source": "Walk-In"},
        {"name": "Aishwarya Rao", "phone": "+919812345002", "category": "PT", "status": "Follow-Up", "source": "Instagram"},
        {"name": "Farhan Sheikh", "phone": "+919812345003", "category": "Membership", "status": "Contacted", "source": "Google"},
        {"name": "Gauri Kadam", "phone": "+919812345004", "category": "Membership", "status": "Interested", "source": "Referral"},
        {"name": "Yash Chauhan", "phone": "+919812345005", "category": "Service", "status": "New", "source": "WhatsApp"},
        {"name": "Neha Kulkarni", "phone": "+919812345006", "category": "Membership", "status": "New", "source": "Website"},
    ]
    enquiry_docs = [{
        "id": new_id(),
        "organisation_id": org_id,
        "outlet_id": outlet1 if i % 2 == 0 else outlet2,
        **e,
        "follow_up_date": (today + timedelta(days=i + 1)).isoformat(),
        "notes": "",
        "follow_ups": [],
        "created_at": ts - timedelta(hours=i * 5) if i == 0 else ts - timedelta(days=i, hours=3),
    } for i, e in enumerate(enquiries)]
    enquiry_docs[0]["created_at"] = ts - timedelta(hours=4)
    enquiry_docs[1]["created_at"] = ts - timedelta(hours=7)
    expenses = [
        {"name": "Electricity Bill", "category": "Utilities", "amount": 8500, "method": "Bank Transfer"},
        {"name": "Equipment Maintenance", "category": "Maintenance", "amount": 4200, "method": "Cash"},
        {"name": "Cleaning Supplies", "category": "Housekeeping", "amount": 1500, "method": "UPI"},
        {"name": "Rent — Indiranagar", "category": "Rent", "amount": 65000, "method": "Bank Transfer"},
    ]
    expense_docs = [{
        "id": new_id(),
        "organisation_id": org_id,
        "outlet_id": outlet1,
        **e,
        "date": (today - timedelta(days=i * 4)).isoformat(),
        "notes": "",
        "created_at": ts - timedelta(days=i * 4),
    } for i, e in enumerate(expenses)]
    staff = [
        {"name": "Suresh Yadav", "role": "Trainer", "phone": "+919845000101", "email": "suresh@example.in", "outlet_id": outlet1},
        {"name": "Anita Desai", "role": "Receptionist", "phone": "+919845000102", "email": "anita@example.in", "outlet_id": outlet1},
        {"name": "Imran Ali", "role": "Manager", "phone": "+919845000103", "email": "imran@example.in", "outlet_id": outlet2},
    ]
    staff_docs = [{"id": new_id(), "organisation_id": org_id, **s, "status": "active", "joining_date": (today - timedelta(days=180)).isoformat(), "has_login": False, "created_at": ts} for s in staff]

    await db.organisations.insert_one(org)
    await db.outlets.insert_many(outlets)
    await db.users.insert_one(owner)
    await db.plans.insert_many(plans)
    await db.members.insert_many(members)
    await db.payments.insert_many(payments)
    await db.attendance.insert_many(attendance)
    await db.enquiries.insert_many(enquiry_docs)
    await db.expenses.insert_many(expense_docs)
    await db.staff.insert_many(staff_docs)
    await db.counters.update_one({"_id": f"member:{org_id}"}, {"$set": {"seq": len(members)}}, upsert=True)
    await db.counters.update_one({"_id": f"receipt:{org_id}"}, {"$set": {"seq": receipt}}, upsert=True)
    logger.info("Seeded demo organisation with %d members", len(members))


async def seed_settings():
    if not await db.settings.find_one({"id": "platform"}):
        await db.settings.insert_one({"id": "platform", "whatsapp_number": "", "support_email": "", "play_store_url": "", "app_store_url": ""})


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True, sparse=True)
    await db.users.create_index("username", unique=True, sparse=True)
    await db.users.create_index("organisation_id")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("email")
    await db.password_reset_requests.create_index("email")
    await db.password_reset_requests.create_index("created_at", expireAfterSeconds=900)
    await db.members.create_index([("organisation_id", 1), ("outlet_id", 1)])
    await db.payments.create_index([("organisation_id", 1), ("created_at", -1)])
    await db.attendance.create_index([("organisation_id", 1), ("check_in", -1)])
    await db.enquiries.create_index("organisation_id")
    await db.expenses.create_index("organisation_id")
    await db.plans.create_index("organisation_id")
    await db.announcements.create_index("organisation_id")
    await db.subscription_payments.create_index("organisation_id")
    await db.audit_logs.create_index("created_at")
    await db.plans.update_many({"type": {"$exists": False}}, [{"$set": {"type": {"$ifNull": ["$category", "membership"]}}}])
    await db.staff.update_many({}, [{"$set": {"role": {"$toLower": "$role"}}}])
    async for org in db.organisations.find({}, {"id": 1, "name": 1}):
        org_id = org["id"]
        prefix = "".join(w[0] for w in (org.get("name") or "GB").split())[:3].upper() or "GB"
        max_code = 0
        async for m in db.members.find({"organisation_id": org_id}, {"member_code": 1}):
            tail = str(m.get("member_code", "")).split("-")[-1]
            if tail.isdigit():
                max_code = max(max_code, int(tail))
        if max_code:
            await db.counters.update_one({"_id": f"member:{org_id}"}, {"$max": {"seq": max_code - 1000}}, upsert=True)
        max_rcpt = 0
        async for p in db.payments.find({"organisation_id": org_id}, {"receipt_no": 1}):
            tail = str(p.get("receipt_no", "")).split("-")[-1]
            if tail.isdigit():
                max_rcpt = max(max_rcpt, int(tail))
        if max_rcpt:
            await db.counters.update_one({"_id": f"receipt:{org_id}"}, {"$max": {"seq": max_rcpt}}, upsert=True)
    try:
        await db.members.create_index([("organisation_id", 1), ("member_code", 1)], unique=True)
    except Exception as e:
        logger.error("member_code unique index creation failed: %s", e)
    demo_org = await db.organisations.find_one({"is_demo": True})
    if demo_org and not await db.plans.find_one({"organisation_id": demo_org["id"], "type": "pt"}):
        ts = now_utc()
        await db.plans.insert_many([
            {"id": new_id(), "organisation_id": demo_org["id"], "name": "PT — 12 Sessions", "type": "pt", "category": "Personal Training", "duration_type": "months", "duration": 1, "sessions": 12, "price": 6000, "status": "active", "created_at": ts},
            {"id": new_id(), "organisation_id": demo_org["id"], "name": "Steam & Sauna", "type": "service", "category": "Recovery", "price": 800, "status": "active", "created_at": ts},
            {"id": new_id(), "organisation_id": demo_org["id"], "name": "Whey Protein 1kg", "type": "product", "category": "Supplements", "price": 2400, "inventory": 15, "status": "active", "created_at": ts},
        ])
    if demo_org and not await db.batches.find_one({"organisation_id": demo_org["id"]}):
        batch_names = ["Morning (6–8 AM)", "Afternoon (12–2 PM)", "Evening (5–8 PM)"]
        await db.batches.insert_many([
            {"id": new_id(), "organisation_id": demo_org["id"], "name": n, "created_at": now_utc()} for n in batch_names
        ])
        demo_members = await db.members.find({"organisation_id": demo_org["id"]}, {"id": 1}).to_list(10000)
        for i, m in enumerate(demo_members):
            await db.members.update_one({"id": m["id"]}, {"$set": {"batch": batch_names[i % 3]}})
    try:
        await init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error("Object storage init failed: %s", e)
    await seed_settings()
    await seed_super_admin()
    await seed_demo()


app.include_router(api)
app.include_router(members_router, prefix="/api")
app.include_router(ops_router, prefix="/api")
app.include_router(comms_router, prefix="/api")
app.include_router(finance_router, prefix="/api")
app.include_router(billing_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

frontend_origin = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    from deps import client
    client.close()
