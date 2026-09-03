from dotenv import load_dotenv
load_dotenv()

import os
import re
import uuid
import logging
from datetime import datetime, timezone, timedelta, date

import bcrypt
import jwt
from fastapi import HTTPException, Request, Response, Depends
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
TRIAL_DAYS = 10
PLAN_PRICE_INR = 999
IST = timezone(timedelta(hours=5, minutes=30))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_ist() -> date:
    return now_utc().astimezone(IST).date()


def new_id() -> str:
    return str(uuid.uuid4())


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "email": user.get("email", ""),
        "ver": user.get("token_version", 0),
        "org": user.get("organisation_id"),
        "role": user.get("role"),
        "exp": now_utc() + timedelta(minutes=30),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user: dict) -> str:
    payload = {"sub": user["id"], "ver": user.get("token_version", 0), "exp": now_utc() + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, user: dict):
    response.set_cookie("access_token", create_access_token(user), httponly=True, secure=True, samesite="none", max_age=1800, path="/")
    response.set_cookie("refresh_token", create_refresh_token(user), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if payload.get("ver", 0) != user.get("token_version", 0):
        raise HTTPException(status_code=401, detail="Session expired")
    if user.get("status") == "disabled":
        raise HTTPException(status_code=403, detail="This account has been disabled.")
    user.pop("password_hash", None)
    user.pop("_id", None)
    return user


async def get_org_user(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") == "super_admin" or not user.get("organisation_id"):
        raise HTTPException(status_code=403, detail="Organisation account required")
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    if org and org.get("disabled"):
        raise HTTPException(status_code=403, detail="This gym account has been disabled. Contact BuildVVO support.")
    user["org_doc"] = org
    return user


async def require_manager(user: dict = Depends(get_org_user)) -> dict:
    if user.get("role") not in ("owner", "admin", "manager"):
        raise HTTPException(status_code=403, detail="You do not have permission for this action")
    return user


async def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


def derive_subscription(org: dict | None) -> dict:
    if not org:
        return {"status": "none", "trial_days_left": 0, "plan_price_inr": PLAN_PRICE_INR}
    sub = org.get("subscription", {})
    status = sub.get("status", "trial")
    trial_ends = sub.get("trial_ends_at")
    if isinstance(trial_ends, str):
        trial_ends = datetime.fromisoformat(trial_ends)
    if isinstance(trial_ends, datetime) and trial_ends.tzinfo is None:
        trial_ends = trial_ends.replace(tzinfo=timezone.utc)
    days_left = 0
    if trial_ends:
        days_left = max(0, (trial_ends.date() - today_ist()).days)
    effective = status
    if status == "trial" and trial_ends and now_utc() > trial_ends:
        effective = "expired"
    sub_ends = sub.get("subscription_ends_at")
    if isinstance(sub_ends, datetime) and sub_ends.tzinfo is None:
        sub_ends = sub_ends.replace(tzinfo=timezone.utc)
    if status == "active" and sub_ends and now_utc() > sub_ends:
        effective = "payment_due"
    return {
        "status": effective,
        "trial_days_left": days_left,
        "trial_ends_at": trial_ends.isoformat() if trial_ends else None,
        "subscription_ends_at": sub_ends.isoformat() if sub_ends else None,
        "plan_price_inr": PLAN_PRICE_INR,
    }


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user.get("role"),
        "organisation_id": user.get("organisation_id"),
    }


def org_public(org: dict) -> dict:
    return {"id": org["id"], "name": org.get("name"), "city": org.get("city"), "onboarding": org.get("onboarding", {}), "disabled": bool(org.get("disabled"))}


async def audit(actor: str, action: str, target: str = "", meta: dict | None = None, org_id: str | None = None):
    await db.audit_logs.insert_one({
        "id": new_id(),
        "actor": actor,
        "action": action,
        "target": target,
        "meta": meta or {},
        "organisation_id": org_id,
        "created_at": now_utc(),
    })


def add_duration(start: date, dtype: str, duration: int) -> date:
    if dtype == "days":
        return start + timedelta(days=duration)
    if dtype == "years":
        return date(start.year + duration, start.month, min(start.day, 28))
    months = duration if dtype == "months" else 1
    total = (start.year * 12 + start.month - 1) + months
    y, m = divmod(total, 12)
    return date(y, m + 1, min(start.day, 28))


def member_status(m: dict, today: date | None = None) -> str:
    today = today or today_ist()
    frozen_until = m.get("frozen_until")
    if isinstance(frozen_until, str):
        frozen_until = date.fromisoformat(frozen_until[:10])
    if frozen_until and frozen_until >= today:
        return "frozen"
    expiry = m.get("membership_expiry")
    if isinstance(expiry, str):
        expiry = date.fromisoformat(expiry[:10])
    if not expiry:
        return "active"
    if expiry < today:
        return "expired"
    if expiry <= today + timedelta(days=7):
        return "expiring_soon"
    return "active"


def days_left(m: dict, today: date | None = None) -> int | None:
    expiry = m.get("membership_expiry")
    if isinstance(expiry, str):
        expiry = date.fromisoformat(expiry[:10])
    if not expiry:
        return None
    return (expiry - (today or today_ist())).days


def member_public(m: dict) -> dict:
    m.pop("_id", None)
    t = today_ist()
    m["status"] = member_status(m, t)
    m["days_left"] = days_left(m, t)
    for k in ("joining_date", "membership_start", "membership_expiry", "frozen_until", "dob"):
        v = m.get(k)
        if isinstance(v, (datetime, date)):
            m[k] = v.isoformat()[:10]
    return m


async def next_receipt_no(org_id: str) -> str:
    doc = await db.counters.find_one_and_update({"_id": f"receipt:{org_id}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
    return f"RCPT-{doc['seq']}"


async def next_member_code(org_id: str, org_name: str) -> str:
    prefix = "".join(w[0] for w in (org_name or "GB").split())[:3].upper() or "GB"
    doc = await db.counters.find_one_and_update({"_id": f"member:{org_id}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
    return f"{prefix}-{1000 + doc['seq']}"
