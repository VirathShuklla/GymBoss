from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, now_utc, today_ist, new_id, get_org_user, audit, member_status

router = APIRouter(tags=["communications"])

AUDIENCES = {"all_active", "all", "outlet", "plan", "expiring_soon", "selected"}


async def resolve_recipients(org_id: str, audience: str, outlet_id: str | None, plan_id: str | None, member_ids: List[str] | None) -> list:
    q = {"organisation_id": org_id, "deleted_at": None}
    if audience == "selected":
        if not member_ids:
            return []
        q["id"] = {"$in": member_ids}
    if audience == "outlet" and outlet_id:
        q["outlet_id"] = outlet_id
    if audience == "plan" and plan_id:
        q["plan_id"] = plan_id
    members = await db.members.find(q).to_list(10000)
    today = today_ist()
    if audience == "all_active":
        members = [m for m in members if member_status(m, today) in ("active", "expiring_soon")]
    elif audience == "expiring_soon":
        members = [m for m in members if member_status(m, today) == "expiring_soon"]
    return [{"member_id": m["id"], "name": m["full_name"], "phone": m["phone"], "status": "pending"} for m in members]


class AudienceCountBody(BaseModel):
    audience: str
    outlet_id: Optional[str] = None
    plan_id: Optional[str] = None
    member_ids: Optional[List[str]] = None


@router.post("/announcements/audience-count")
async def audience_count(body: AudienceCountBody, user: dict = Depends(get_org_user)):
    if body.audience not in AUDIENCES:
        raise HTTPException(422, "Invalid audience")
    recipients = await resolve_recipients(user["organisation_id"], body.audience, body.outlet_id, body.plan_id, body.member_ids)
    return {"count": len(recipients)}


class AnnouncementBody(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=2, max_length=2000)
    audience: str
    outlet_id: Optional[str] = None
    plan_id: Optional[str] = None
    member_ids: Optional[List[str]] = None
    channel: str = "whatsapp"
    scheduled_at: Optional[str] = None


@router.post("/announcements")
async def create_announcement(body: AnnouncementBody, user: dict = Depends(get_org_user)):
    if body.audience not in AUDIENCES:
        raise HTTPException(422, "Invalid audience")
    if body.channel != "whatsapp":
        raise HTTPException(422, "Only WhatsApp is supported currently")
    org_id = user["organisation_id"]
    recipients = await resolve_recipients(org_id, body.audience, body.outlet_id, body.plan_id, body.member_ids)
    scheduled_at = None
    if body.scheduled_at:
        scheduled_at = datetime.fromisoformat(body.scheduled_at.replace("Z", "+00:00"))
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    waba = await db.integrations.find_one({"organisation_id": org_id, "provider": "whatsapp", "status": "connected"})
    if scheduled_at and scheduled_at > now_utc():
        status = "scheduled"
    elif waba:
        status = "queued"
    else:
        status = "integration_required"
    doc = {
        "id": new_id(), "organisation_id": org_id,
        "title": body.title, "message": body.message, "audience": body.audience,
        "outlet_id": body.outlet_id, "plan_id": body.plan_id, "channel": body.channel,
        "recipients": recipients, "recipient_count": len(recipients),
        "scheduled_at": scheduled_at, "status": status,
        "created_by": user["id"], "created_by_name": user.get("full_name"),
        "created_at": now_utc(),
    }
    await db.announcements.insert_one(doc)
    await audit(user["id"], "announcement.created", doc["id"], {"audience": body.audience, "recipients": len(recipients), "status": status}, org_id)
    doc.pop("_id", None)
    if isinstance(doc.get("scheduled_at"), datetime):
        doc["scheduled_at"] = doc["scheduled_at"].isoformat()
    doc["created_at"] = doc["created_at"].isoformat()
    return {"announcement": doc, "integration_configured": bool(waba)}


@router.get("/announcements")
async def list_announcements(user: dict = Depends(get_org_user)):
    items = await db.announcements.find({"organisation_id": user["organisation_id"]}, {"recipients": 0}).sort("created_at", -1).to_list(500)
    for a in items:
        a.pop("_id", None)
    return items


@router.get("/announcements/{announcement_id}")
async def get_announcement(announcement_id: str, user: dict = Depends(get_org_user)):
    doc = await db.announcements.find_one({"id": announcement_id, "organisation_id": user["organisation_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Announcement not found")
    return doc


@router.delete("/announcements/{announcement_id}")
async def cancel_announcement(announcement_id: str, user: dict = Depends(get_org_user)):
    res = await db.announcements.update_one(
        {"id": announcement_id, "organisation_id": user["organisation_id"], "status": {"$in": ["scheduled", "integration_required"]}},
        {"$set": {"status": "cancelled"}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Announcement not found or cannot be cancelled")
    await audit(user["id"], "announcement.cancelled", announcement_id, org_id=user["organisation_id"])
    return {"message": "Announcement cancelled"}
