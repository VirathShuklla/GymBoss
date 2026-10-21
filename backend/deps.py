"""Shared backend core: Mongo client, JWT/password auth, tenancy + permission dependencies
(get_org_user, require_write, require_manager, require_finance_access, require_super_admin),
subscription/member derivations, counters, object storage, and settings (price + Razorpay) lookup."""
from dotenv import load_dotenv
load_dotenv()

import os
import re
import uuid
import logging
from datetime import datetime, timezone, timedelta, date

import bcrypt
import jwt
import httpx
from fastapi import HTTPException, Request, Response, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True, tzinfo=timezone.utc)
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


COOKIE_KW = {"domain": os.environ.get("COOKIE_DOMAIN") or None}
NATIVE_PLATFORMS = ("android_store", "ios_store")


TRUSTED_PROXIES = {p.strip() for p in os.environ.get("TRUSTED_PROXIES", "").split(",") if p.strip()}
TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "1"))
REAL_IP_HEADER = os.environ.get("REAL_IP_HEADER", "").strip()


def client_ip(request: Request) -> str:
    """Client IP behind trusted proxies. Uses REAL_IP_HEADER (e.g. CF-Connecting-IP / X-Real-IP set by your edge)
    if configured; otherwise the X-Forwarded-For entry appended by the outermost trusted hop, counted from the RIGHT
    (left-most entries are client-controlled and never trusted)."""
    peer = request.client.host if request.client else "unknown"
    if not ("*" in TRUSTED_PROXIES or peer in TRUSTED_PROXIES):
        return peer
    if REAL_IP_HEADER and request.headers.get(REAL_IP_HEADER):
        return request.headers[REAL_IP_HEADER].strip()
    parts = [p.strip() for p in (request.headers.get("x-forwarded-for") or "").split(",") if p.strip()]
    if not parts:
        return peer
    return parts[-min(TRUSTED_PROXY_HOPS, len(parts))]


def set_auth_cookies(response: Response, user: dict):
    response.set_cookie("access_token", create_access_token(user), httponly=True, secure=True, samesite="none", max_age=1800, path="/", **COOKIE_KW)
    response.set_cookie("refresh_token", create_refresh_token(user), httponly=True, secure=True, samesite="none", max_age=604800, path="/", **COOKIE_KW)


def issue_native_tokens(request: Request, user: dict, refresh: bool = True) -> dict:
    """Store apps (Capacitor) can't rely on cross-site cookies, so they get Bearer tokens in the body."""
    if request.headers.get("X-Client-Platform", "").lower() not in NATIVE_PLATFORMS:
        return {}
    tokens = {"access_token": create_access_token(user)}
    if refresh:
        tokens["refresh_token"] = create_refresh_token(user)
    return {"tokens": tokens}


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


WRITE_ALLOWED_WHEN_EXPIRED = ("/api/subscription", "/api/auth", "/api/support", "/api/events", "/api/onboarding")


async def get_org_user(request: Request, user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") == "super_admin" or not user.get("organisation_id"):
        raise HTTPException(status_code=403, detail="Organisation account required")
    org = await db.organisations.find_one({"id": user["organisation_id"]})
    if org and org.get("disabled"):
        raise HTTPException(status_code=403, detail="This gym account has been disabled. Contact BuildVVO support.")
    if (request.method not in ("GET", "HEAD", "OPTIONS") and not request.url.path.startswith(WRITE_ALLOWED_WHEN_EXPIRED)
            and derive_subscription(org)["status"] in RESTRICTED_SUB_STATES):
        raise HTTPException(status_code=402, detail="Your trial has ended, so GymBoss is in view-only mode. Your data is safe. Reactivate GymBoss to add or edit again.")
    user["org_doc"] = org
    return user


RESTRICTED_SUB_STATES = ("expired", "payment_due", "cancelled", "none")

# Permission matrix (single source of truth, mirrored in frontend/src/lib/permissions.js):
#   owner/admin  : everything (only the owner changes roles, login emails/passwords, deletes the account)
#   permission "full"   : create/edit + delete/reverse + manage staff, outlets, settings
#   permission "manage" : create/edit only
#   permission "view"   : read only
#   finance pages: owner, admin, or finance_enabled


def perm_level(user: dict) -> str:
    if user.get("role") in ("owner", "admin"):
        return "full"
    return user.get("permission") if user.get("permission") in ("view", "manage", "full") else "view"


async def require_manager(user: dict = Depends(get_org_user)) -> dict:
    if user.get("role") not in ("owner", "admin", "manager") or perm_level(user) != "full":
        raise HTTPException(status_code=403, detail="You do not have permission for this action")
    return user


async def require_full(user: dict = Depends(get_org_user)) -> dict:
    if perm_level(user) != "full":
        raise HTTPException(status_code=403, detail="Only full-access users can delete or reverse records")
    return user


async def require_write(user: dict = Depends(get_org_user)) -> dict:
    if perm_level(user) == "view":
        raise HTTPException(status_code=403, detail="Your role has view-only access")
    return user


async def require_finance_access(user: dict = Depends(get_org_user)) -> dict:
    if user.get("role") in ("owner", "admin") or user.get("finance_enabled"):
        return user
    raise HTTPException(status_code=403, detail="You do not have access to finance")


async def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


def derive_subscription(org: dict | None, plan_price: int | None = None) -> dict:
    if not org:
        return {"status": "none", "trial_days_left": 0, "plan_price_inr": plan_price or PLAN_PRICE_INR}
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
        "plan_price_inr": plan_price or PLAN_PRICE_INR,
        "plan": sub.get("plan"),
        "plan_months": sub.get("plan_months") or 1,
        "amount": sub.get("amount"),
    }


def org_mrr(sub: dict, monthly_price: int) -> int:
    """Monthly recurring value of an active subscription (multi-month plans spread per month)."""
    if sub.get("status") != "active":
        return 0
    return round((sub.get("amount") or monthly_price) / (sub.get("plan_months") or 1))


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user.get("role"),
        "permission": user.get("permission"),
        "finance_enabled": bool(user.get("finance_enabled")),
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


FAULTS: set[str] = set()


async def checkpoint(name: str):
    """Test-only fault injection: tests add a name to FAULTS to crash once at that point."""
    if name in FAULTS:
        FAULTS.discard(name)
        raise RuntimeError(f"Injected fault at {name}")


async def run_txn(fn):
    """Run `await fn(session)` in a MongoDB transaction (retried on transient conflicts)."""
    async with await client.start_session() as s:
        return await s.with_transaction(fn, read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))


async def best_effort(coro):
    """Side effects (audit/analytics) after a commit must never undo or repeat the committed work."""
    try:
        await coro
    except Exception as e:
        logger.error("Post-commit side effect failed: %s", e)


def idem_key(request: Request) -> str | None:
    key = (request.headers.get("Idempotency-Key") or "").strip()
    if len(key) > 100:
        raise HTTPException(422, "Idempotency-Key is too long")
    return key or None


async def idem_lookup(org_id: str, key: str | None, scope: str, fp: str | None = None) -> dict | None:
    if not key:
        return None
    doc = await db.idempotency_keys.find_one({"organisation_id": org_id, "key": key})
    if doc and (doc["scope"] != scope or (fp and doc.get("fp") and doc["fp"] != fp)):
        raise HTTPException(422, "This Idempotency-Key was already used for a different request")
    return doc


def fingerprint(body) -> str:
    import hashlib
    return hashlib.sha256((body.model_dump_json() if body is not None else "").encode()).hexdigest()


async def idem_save(s, org_id: str, key: str | None, scope: str, ref: str, fp: str | None = None):
    if key:
        await db.idempotency_keys.insert_one({"organisation_id": org_id, "key": key, "scope": scope, "ref": ref, "fp": fp, "created_at": now_utc()}, session=s)


def add_duration(start: date, dtype: str, duration: int) -> date:
    if dtype == "days":
        return start + timedelta(days=duration)
    import calendar
    months = duration * 12 if dtype == "years" else (duration if dtype == "months" else 1)
    total = (start.year * 12 + start.month - 1) + months
    y, m = divmod(total, 12)
    return date(y, m + 1, min(start.day, calendar.monthrange(y, m + 1)[1]))


def member_status(m: dict, today: date | None = None) -> str:
    today = today or today_ist()
    frozen_until = m.get("frozen_until")
    if isinstance(frozen_until, str):
        frozen_until = date.fromisoformat(frozen_until[:10])
    frozen_from = m.get("frozen_from")
    if isinstance(frozen_from, str):
        frozen_from = date.fromisoformat(frozen_from[:10])
    if frozen_until and frozen_until >= today and (not frozen_from or frozen_from <= today):
        return "frozen"
    t = today.isoformat()
    for h in m.get("freeze_history") or []:
        if not h.get("cancelled") and h.get("freeze_from", "9999") <= t <= (h.get("ended_on") or h.get("freeze_until", "")):
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


async def next_receipt_no(org_id: str, session=None) -> str:
    doc = await db.counters.find_one_and_update({"_id": f"receipt:{org_id}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True, session=session)
    return f"RCPT-{doc['seq']}"


PLAN_SLOTS = [("monthly", "Monthly", 1), ("quarterly", "Quarterly", 3), ("yearly", "Yearly", 12)]


def _price_plans(settings: dict) -> list:
    """Admin-managed SaaS plans; each gets an effective price (offer price when set and lower)."""
    stored = {p.get("id"): p for p in settings.get("pricing_plans") or []}
    try:
        base_monthly = int(settings.get("plan_price_inr") or PLAN_PRICE_INR)
    except (TypeError, ValueError):
        base_monthly = PLAN_PRICE_INR
    plans = []
    for pid, name, months in PLAN_SLOTS:
        s = stored.get(pid, {})
        price = int(s.get("price") or (base_monthly * months))
        offer = s.get("offer_price")
        offer = int(offer) if offer not in (None, "", 0) and int(offer) < price else None
        effective = offer or price
        plans.append({
            "id": pid, "name": s.get("name") or name, "months": months, "price": price,
            "offer_price": offer, "offer_label": (s.get("offer_label") or "").strip(),
            "active": s.get("active", True) if pid != "monthly" else True,
            "effective_price": effective, "per_month": round(effective / months),
            "save_pct": round(100 * (price - effective) / price) if offer else 0,
        })
    return plans


async def get_pricing_plans(active_only: bool = False) -> list:
    settings = await db.settings.find_one({"id": "platform"}) or {}
    plans = _price_plans(settings)
    return [p for p in plans if p["active"]] if active_only else plans


async def get_pricing_plan(plan_id: str | None) -> dict:
    plans = await get_pricing_plans(active_only=True)
    return next((p for p in plans if p["id"] == (plan_id or "monthly")), plans[0])


async def get_plan_price() -> int:
    """Effective monthly plan price (used for MRR and 'from ₹X/month' copy)."""
    return (await get_pricing_plan("monthly"))["effective_price"]


async def get_razorpay_keys() -> tuple:
    settings = await db.settings.find_one({"id": "platform"}) or {}
    return (
        settings.get("razorpay_key_id") or os.environ.get("RAZORPAY_KEY_ID", ""),
        settings.get("razorpay_key_secret") or os.environ.get("RAZORPAY_KEY_SECRET", ""),
    )


STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "emergent").lower()
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
_storage_key = None


async def init_storage(force: bool = False) -> str:
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    key = os.environ.get("EMERGENT_LLM_KEY")
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(f"{STORAGE_URL}/init", json={"emergent_key": key})
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _s3():
    import boto3
    return boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None, region_name=os.environ.get("S3_REGION") or None,
                        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    import asyncio
    if STORAGE_BACKEND == "s3":
        await asyncio.to_thread(_s3().put_object, Bucket=os.environ["S3_BUCKET"], Key=path, Body=data, ContentType=content_type)
        return {"path": path, "size": len(data)}
    key = await init_storage()
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, content=data)
        if resp.status_code == 404:
            key = await init_storage(force=True)
            resp = await http.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, content=data)
    resp.raise_for_status()
    return resp.json()


async def get_object(path: str) -> tuple:
    import asyncio
    if STORAGE_BACKEND == "s3":
        try:
            obj = await asyncio.to_thread(_s3().get_object, Bucket=os.environ["S3_BUCKET"], Key=path)
        except Exception:
            raise HTTPException(404, "File not found")
        return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")
    key = await init_storage()
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key})
        if resp.status_code == 404 and _storage_key:
            key = await init_storage(force=True)
            resp = await http.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key})
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


async def next_member_code(org_id: str, org_name: str, session=None) -> str:
    prefix = "".join(w[0] for w in (org_name or "GB").split())[:3].upper() or "GB"
    doc = await db.counters.find_one_and_update({"_id": f"member:{org_id}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True, session=session)
    return f"{prefix}-{1000 + doc['seq']}"
