"""Attendance: QR self check-in (public, per-outlet token), biometric devices (eSSL/ZKTeco ADMS
push protocol), staff attendance, and a shared punch-in/punch-out engine."""
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from deps import db, now_utc, new_id, today_ist, get_org_user, require_write, member_status, normalize_phone, audit, IST

router = APIRouter(tags=["attendance"])
adms_router = APIRouter(tags=["adms"])

DEVICE_TYPES = ["eSSL X990", "eSSL K30", "eSSL K40", "eSSL MB20", "eSSL MB160", "eSSL MB460", "Other eSSL / ZKTeco (ADMS)"]
ONLINE_WINDOW = timedelta(minutes=5)
DOUBLE_SCAN = timedelta(minutes=1)


logger = logging.getLogger(__name__)


def day_start(d=None) -> datetime:
    d = d or today_ist()
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)


def device_pin(member: dict) -> str:
    """User ID to enrol on a biometric device: the number in the member code (IPF-1001 -> 1001)."""
    if member.get("biometric_id"):
        return str(member["biometric_id"])
    m = re.search(r"(\d+)$", member.get("member_code") or "")
    return str(int(m.group(1))) if m else ""


def assert_member_eligible(m: dict):
    """One eligibility rule for manual, QR and biometric check-ins."""
    st = member_status(m)
    if st == "expired":
        raise HTTPException(403, f"Membership expired on {str(m.get('membership_expiry'))[:10]}. Please renew at the front desk.")
    if st == "frozen":
        raise HTTPException(403, "This membership is currently frozen.")


async def punch(collection, key: str, person_id: str, base_doc: dict, at: datetime | None = None, checkin_only: bool = False) -> tuple[str, dict]:
    """First punch of the (event's IST) day = check-in, next = check-out. Ignores accidental double scans.
    Uses the punch's own timestamp, so delayed biometric uploads pair with the right day."""
    at = at or now_utc()
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    start = day_start(at.astimezone(IST).date())
    if await collection.find_one({key: person_id, "$or": [{"check_in": at}, {"check_out": at}]}):
        return "duplicate", {"check_in": at, "check_out": None}
    open_visit = await collection.find_one({key: person_id, "check_out": None, "check_in": {"$gte": start, "$lt": start + timedelta(days=1), "$lte": at}})
    if open_visit:
        ci = open_visit["check_in"].replace(tzinfo=timezone.utc) if open_visit["check_in"].tzinfo is None else open_visit["check_in"]
        if at - ci < DOUBLE_SCAN or checkin_only:
            open_visit.pop("_id", None)
            return "duplicate", open_visit
        await collection.update_one({"id": open_visit["id"]}, {"$set": {"check_out": at}})
        open_visit.pop("_id", None)
        open_visit["check_out"] = at
        return "out", open_visit
    doc = {"id": new_id(), **base_doc, key: person_id, "check_in": at, "check_out": None}
    await collection.insert_one(doc)
    doc.pop("_id", None)
    return "in", doc


async def punch_member(m: dict, source: str, at: datetime | None = None, device_id: str | None = None, outlet_id: str | None = None, checkin_only: bool = False):
    base = {
        "organisation_id": m["organisation_id"], "outlet_id": outlet_id or m.get("outlet_id"),
        "member_name": m["full_name"], "member_code": m["member_code"], "source": source, "device_id": device_id,
    }
    return await punch(db.attendance, "member_id", m["id"], base, at, checkin_only)


def _fmt(dt):
    return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).astimezone(IST).strftime("%I:%M %p")


# ---------------- Summary & staff list ----------------

@router.get("/attendance/summary")
async def attendance_summary(user: dict = Depends(get_org_user)):
    org_id = user["organisation_id"]
    q = {"organisation_id": org_id, "check_in": {"$gte": day_start()}}
    rows = await db.attendance.find(q, {"source": 1, "check_out": 1}).to_list(5000)
    staff_today = await db.staff_attendance.count_documents(q)
    devices = await db.biometric_devices.find({"organisation_id": org_id}, {"last_seen": 1}).to_list(100)
    cutoff = now_utc() - ONLINE_WINDOW
    online = sum(1 for d in devices if d.get("last_seen") and d["last_seen"].replace(tzinfo=timezone.utc) >= cutoff)
    by_source = {"qr": 0, "biometric": 0, "manual": 0}
    for r in rows:
        by_source[r.get("source") or "manual"] = by_source.get(r.get("source") or "manual", 0) + 1
    return {
        "today": len(rows), "inside_now": sum(1 for r in rows if not r.get("check_out")),
        "staff_today": staff_today, "by_source": by_source,
        "devices": len(devices), "devices_online": online,
    }


@router.get("/attendance/staff")
async def staff_attendance(user: dict = Depends(get_org_user)):
    return await db.staff_attendance.find(
        {"organisation_id": user["organisation_id"], "check_in": {"$gte": day_start()}}, {"_id": 0}
    ).sort("check_in", -1).to_list(500)


# ---------------- QR check-in ----------------

async def _ensure_token(outlet: dict) -> str:
    if outlet.get("checkin_token"):
        return outlet["checkin_token"]
    token = secrets.token_urlsafe(9)
    await db.outlets.update_one({"id": outlet["id"]}, {"$set": {"checkin_token": token}})
    return token


@router.get("/attendance/qr")
async def attendance_qr(user: dict = Depends(get_org_user)):
    org = await db.organisations.find_one({"id": user["organisation_id"]}, {"name": 1, "city": 1})
    outlets = await db.outlets.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).to_list(100)
    return {
        "gym_name": org.get("name"), "city": org.get("city"),
        "outlets": [{"outlet_id": o["id"], "outlet_name": o.get("name"), "address": o.get("address") or o.get("city") or org.get("city"),
                     "token": await _ensure_token(o)} for o in outlets],
    }


@router.post("/attendance/qr/{outlet_id}/rotate")
async def rotate_qr(outlet_id: str, user: dict = Depends(require_write)):
    token = secrets.token_urlsafe(9)
    res = await db.outlets.update_one({"id": outlet_id, "organisation_id": user["organisation_id"]}, {"$set": {"checkin_token": token}})
    if not res.matched_count:
        raise HTTPException(404, "Outlet not found")
    await audit(user["id"], "attendance.qr_rotated", outlet_id, {}, user["organisation_id"])
    return {"token": token}


async def _outlet_by_token(token: str) -> tuple[dict, dict]:
    outlet = await db.outlets.find_one({"checkin_token": token}, {"_id": 0})
    if not outlet:
        raise HTTPException(404, "This QR code is no longer valid. Please ask the front desk for the latest one.")
    org = await db.organisations.find_one({"id": outlet["organisation_id"]}, {"_id": 0, "name": 1, "city": 1, "disabled": 1})
    if not org or org.get("disabled"):
        raise HTTPException(404, "Check-in is unavailable for this gym.")
    return outlet, org


@router.get("/public/checkin/{token}")
async def public_checkin_info(token: str):
    outlet, org = await _outlet_by_token(token)
    return {"gym_name": org.get("name"), "outlet_name": outlet.get("name"), "city": org.get("city")}


class PublicCheckin(BaseModel):
    kind: str = "member"
    identifier: str


@router.post("/public/checkin/{token}")
async def public_checkin(token: str, body: PublicCheckin):
    outlet, org = await _outlet_by_token(token)
    org_id = outlet["organisation_id"]
    ident = body.identifier.strip()
    if len(ident) < 3:
        raise HTTPException(422, "Please enter your member ID or phone number")
    digits = re.sub(r"\D", "", ident)
    if body.kind == "staff":
        or_q = [{"email": ident.lower()}]
        if len(digits) >= 10:
            or_q.append({"phone": {"$regex": f"{digits[-10:]}$"}})
        u = await db.staff.find_one({"organisation_id": org_id, "$or": or_q})
        if not u:
            owner = await db.users.find_one({"organisation_id": org_id, "role": "owner", "status": {"$ne": "disabled"}, "$or": or_q})
            u = {"id": owner["id"], "user_id": owner["id"], "name": owner.get("full_name"), "role": "owner", "status": "active"} if owner else None
        if not u:
            raise HTTPException(404, "No staff member found with that phone or email.")
        if u.get("status", "active") != "active":
            raise HTTPException(403, "This staff account is disabled.")
        base = {"organisation_id": org_id, "outlet_id": outlet["id"], "staff_name": u.get("name"), "role": u.get("role"), "source": "qr"}
        action, doc = await punch(db.staff_attendance, "staff_id", u.get("user_id") or u["id"], base)
        name = u.get("name") or "there"
    else:
        or_q = [{"member_code": {"$regex": f"^{re.escape(ident)}$", "$options": "i"}}]
        if len(digits) >= 10:
            or_q.append({"phone": {"$regex": f"{digits[-10:]}$"}})
        elif digits:
            or_q.append({"member_code": {"$regex": f"-0*{int(digits)}$"}})
        m = await db.members.find_one({"organisation_id": org_id, "deleted_at": None, "$or": or_q})
        if not m:
            raise HTTPException(404, "We couldn't find you. Check your member ID or phone number, or ask the front desk.")
        assert_member_eligible(m)
        action, doc = await punch_member(m, "qr", outlet_id=outlet["id"])
        name = m["full_name"]
    t = doc["check_out"] if action == "out" else doc["check_in"]
    msg = {"in": f"Welcome, {name.split(' ')[0]}! Punched in at {_fmt(t)}.",
           "out": f"Bye, {name.split(' ')[0]}! Punched out at {_fmt(t)}.",
           "duplicate": f"You're already punched in at {_fmt(t)}. Scan again when you leave."}[action]
    return {"action": action, "name": name, "time": t.isoformat(), "message": msg, "gym_name": org.get("name")}


# ---------------- Biometric devices ----------------

def _device_public(d: dict) -> dict:
    ls = d.get("last_seen")
    if ls and ls.tzinfo is None:
        ls = ls.replace(tzinfo=timezone.utc)
    return {
        "id": d["id"], "name": d["name"], "device_type": d["device_type"], "serial_number": d["serial_number"],
        "outlet_id": d.get("outlet_id"), "auto_delete_on_expiry": bool(d.get("auto_delete_on_expiry")),
        "last_seen": ls.isoformat() if ls else None, "online": bool(ls and now_utc() - ls <= ONLINE_WINDOW),
        "punches": d.get("punches", 0), "created_at": d["created_at"].isoformat() if d.get("created_at") else None,
    }


@router.get("/attendance/devices")
async def list_devices(user: dict = Depends(get_org_user)):
    devices = await db.biometric_devices.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return {"devices": [_device_public(d) for d in devices], "device_types": DEVICE_TYPES}


class DeviceBody(BaseModel):
    device_type: str
    serial_number: str
    name: str
    outlet_id: Optional[str] = None


@router.post("/attendance/devices")
async def add_device(body: DeviceBody, user: dict = Depends(require_write)):
    sn = re.sub(r"\s", "", body.serial_number).upper()
    if not re.fullmatch(r"[A-Z0-9\-]{6,32}", sn):
        raise HTTPException(422, "Enter a valid serial number (letters and numbers, as printed on the device).")
    if body.device_type not in DEVICE_TYPES:
        raise HTTPException(422, "Choose a supported device type")
    if not body.name.strip():
        raise HTTPException(422, "Give the device a name, e.g. Front Desk")
    if await db.biometric_devices.find_one({"serial_number": sn}):
        raise HTTPException(409, "This device is already connected to a gym. Remove it there first or contact support.")
    outlet_id = body.outlet_id
    if not outlet_id:
        o = await db.outlets.find_one({"organisation_id": user["organisation_id"]}, sort=[("created_at", 1)])
        outlet_id = o["id"] if o else None
    doc = {"id": new_id(), "organisation_id": user["organisation_id"], "outlet_id": outlet_id, "name": body.name.strip()[:40],
           "device_type": body.device_type, "serial_number": sn, "auto_delete_on_expiry": False,
           "last_seen": None, "punches": 0, "deleted_pins": {}, "created_at": now_utc()}
    await db.biometric_devices.insert_one(doc)
    await audit(user["id"], "attendance.device_added", doc["id"], {"sn": sn}, user["organisation_id"])
    return _device_public(doc)


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    auto_delete_on_expiry: Optional[bool] = None
    allowed_ips: Optional[list[str]] = None


@router.put("/attendance/devices/{device_id}")
async def update_device(device_id: str, body: DeviceUpdate, user: dict = Depends(require_write)):
    data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "name" in data:
        data["name"] = data["name"].strip()[:40] or "Device"
    res = await db.biometric_devices.update_one({"id": device_id, "organisation_id": user["organisation_id"]}, {"$set": data})
    if not res.matched_count:
        raise HTTPException(404, "Device not found")
    return _device_public(await db.biometric_devices.find_one({"id": device_id}))


@router.delete("/attendance/devices/{device_id}")
async def delete_device(device_id: str, user: dict = Depends(require_write)):
    res = await db.biometric_devices.delete_one({"id": device_id, "organisation_id": user["organisation_id"]})
    if not res.deleted_count:
        raise HTTPException(404, "Device not found")
    await audit(user["id"], "attendance.device_removed", device_id, {}, user["organisation_id"])
    return {"ok": True}


class TestPunch(BaseModel):
    member_id: str


@router.post("/attendance/devices/{device_id}/test-punch")
async def test_punch(device_id: str, body: TestPunch, user: dict = Depends(require_write)):
    """Simulates a fingerprint punch from this device, through the same path as real ADMS punches."""
    d = await db.biometric_devices.find_one({"id": device_id, "organisation_id": user["organisation_id"]})
    if not d:
        raise HTTPException(404, "Device not found")
    m = await db.members.find_one({"id": body.member_id, "organisation_id": user["organisation_id"], "deleted_at": None})
    if not m:
        raise HTTPException(404, "Member not found")
    action, doc = await punch_member(m, "biometric", device_id=d["id"], outlet_id=d.get("outlet_id"))
    await db.biometric_devices.update_one({"id": d["id"]}, {"$inc": {"punches": 1}})
    return {"action": action, "attendance": doc, "member_name": m["full_name"], "device_user_id": device_pin(m)}


@router.get("/attendance/device-ids")
async def device_ids(user: dict = Depends(get_org_user)):
    """Device user IDs to enrol each member with on the biometric machine."""
    ms = await db.members.find({"organisation_id": user["organisation_id"], "deleted_at": None},
                               {"_id": 0, "id": 1, "full_name": 1, "member_code": 1, "biometric_id": 1}).sort("member_code", 1).to_list(5000)
    return [{"member_id": m["id"], "full_name": m["full_name"], "member_code": m["member_code"], "device_user_id": device_pin(m)} for m in ms]


# ---------------- ADMS push protocol (device -> server) ----------------

def _client_ip(request: Request) -> str:
    from deps import client_ip
    return client_ip(request)


async def _device_by_sn(sn: str | None, request: Request | None = None):
    """Devices are identified by serial number; if the owner set allowed IPs, the request must also come from one."""
    if not sn:
        return None
    d = await db.biometric_devices.find_one({"serial_number": sn.strip().upper()})
    if d and d.get("allowed_ips") and request is not None and _client_ip(request) not in d["allowed_ips"]:
        logger.warning("ADMS request for %s from unlisted IP %s rejected", sn, _client_ip(request))
        return None
    if d:
        await db.biometric_devices.update_one({"id": d["id"]}, {"$set": {"last_seen": now_utc()}})
    return d


async def _member_by_pin(org_id: str, pin: str):
    pin = pin.strip()
    if not pin.isdigit():
        return await db.members.find_one({"organisation_id": org_id, "deleted_at": None, "biometric_id": pin})
    return await db.members.find_one({"organisation_id": org_id, "deleted_at": None,
                                      "$or": [{"biometric_id": pin}, {"member_code": {"$regex": f"-0*{int(pin)}$"}}]})


@adms_router.get("/iclock/cdata", response_class=PlainTextResponse)
async def adms_handshake(request: Request, SN: str = "", options: str = ""):
    await _device_by_sn(SN, request)
    return "\n".join([
        f"GET OPTION FROM: {SN}", "ATTLOGStamp=None", "OPERLOGStamp=9999", "ATTPHOTOStamp=None",
        "ErrorDelay=30", "Delay=10", "TransTimes=00:00;14:05", "TransInterval=1",
        "TransFlag=TransData AttLog", "TimeZone=330", "Realtime=1", "Encrypt=None",
    ])


@adms_router.post("/iclock/cdata", response_class=PlainTextResponse)
async def adms_upload(request: Request, SN: str = "", table: str = ""):
    d = await _device_by_sn(SN, request)
    body = (await request.body()).decode("utf-8", errors="ignore")
    if not d or table.upper() != "ATTLOG":
        return "OK"
    count = 0
    for line in body.splitlines():
        parts = line.strip().split("\t")
        if len(parts) < 2:
            continue
        pin, ts = parts[0], parts[1]
        try:
            at = datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST).astimezone(timezone.utc)
        except ValueError:
            continue
        m = await _member_by_pin(d["organisation_id"], pin)
        if not m or member_status(m, at.astimezone(IST).date()) in ("expired", "frozen"):
            continue
        action, _ = await punch_member(m, "biometric", at=at, device_id=d["id"], outlet_id=d.get("outlet_id"))
        count += action != "duplicate"
    if count:
        await db.biometric_devices.update_one({"id": d["id"]}, {"$inc": {"punches": count}})
    return f"OK: {count}"


@adms_router.get("/iclock/getrequest", response_class=PlainTextResponse)
async def adms_getrequest(request: Request, SN: str = ""):
    """Device polls for commands. Commands stay queued until the device acknowledges them via /iclock/devicecmd;
    unacknowledged commands are re-sent after 5 minutes."""
    d = await _device_by_sn(SN, request)
    if not d:
        return "OK"
    if d.get("auto_delete_on_expiry"):
        today = today_ist().isoformat()
        async for m in db.members.find({"organisation_id": d["organisation_id"], "deleted_at": None, "membership_expiry": {"$lt": today}}).limit(200):
            pin, exp = device_pin(m), str(m.get("membership_expiry"))[:10]
            if pin:
                await db.device_commands.update_one(
                    {"device_id": d["id"], "pin": pin, "expiry": exp},
                    {"$setOnInsert": {"id": new_id(), "device_id": d["id"], "pin": pin, "expiry": exp, "cmd": f"DATA DELETE USERINFO PIN={pin}",
                                      "status": "queued", "created_at": now_utc()}}, upsert=True)
    resend = now_utc() - timedelta(minutes=5)
    q = {"device_id": d["id"], "$or": [{"status": "queued"}, {"status": "sent", "sent_at": {"$lt": resend}}]}
    cmds = await db.device_commands.find(q).sort("created_at", 1).limit(20).to_list(20)
    if not cmds:
        return "OK"
    lines = []
    for c in cmds:
        seq = await db.counters.find_one_and_update({"id": f"devcmd:{d['id']}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
        await db.device_commands.update_one({"id": c["id"]}, {"$set": {"status": "sent", "sent_at": now_utc(), "seq": seq["seq"]}})
        lines.append(f"C:{seq['seq']}:{c['cmd']}")
    return "\n".join(lines)


@adms_router.post("/iclock/devicecmd", response_class=PlainTextResponse)
async def adms_devicecmd(request: Request, SN: str = ""):
    """Device reports results as lines like ID=12&Return=0&CMD=DATA. Return=0 means success."""
    d = await _device_by_sn(SN, request)
    if not d:
        return "OK"
    body = (await request.body()).decode("utf-8", errors="ignore")
    for line in body.splitlines():
        kv = dict(p.split("=", 1) for p in line.strip().split("&") if "=" in p)
        if kv.get("ID", "").isdigit():
            status = "done" if kv.get("Return", "-1") in ("0", "") else "failed"
            await db.device_commands.update_one({"device_id": d["id"], "seq": int(kv["ID"])}, {"$set": {"status": status, "acked_at": now_utc(), "return": kv.get("Return")}})
    return "OK"
