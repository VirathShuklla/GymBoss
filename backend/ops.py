import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from deps import db, now_utc, today_ist, new_id, get_org_user, require_manager, audit, hash_password, normalize_phone

router = APIRouter(tags=["operations"])


# ---------------- Enquiries ----------------

class EnquiryBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=10, max_length=15)
    email: Optional[str] = None
    address: Optional[str] = None
    follow_up_date: Optional[str] = None
    category: Optional[str] = None
    status: str = "New"
    assigned_staff: Optional[str] = None
    source: Optional[str] = "Walk-In"
    notes: Optional[str] = None
    outlet_id: Optional[str] = None


@router.get("/enquiries")
async def list_enquiries(search: Optional[str] = None, status: Optional[str] = None, outlet_id: Optional[str] = None, user: dict = Depends(get_org_user)):
    q = {"organisation_id": user["organisation_id"]}
    if outlet_id:
        q["outlet_id"] = outlet_id
    if status and status != "all":
        q["status"] = status
    if search:
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        q["$or"] = [{"name": rx}, {"phone": rx}]
    return await db.enquiries.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)


@router.post("/enquiries")
async def create_enquiry(body: EnquiryBody, user: dict = Depends(get_org_user)):
    phone = normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(422, "Enter a valid 10-digit mobile number")
    outlet_id = body.outlet_id
    if not outlet_id:
        outlet_doc = await db.outlets.find_one({"organisation_id": user["organisation_id"], "is_primary": True}) or await db.outlets.find_one({"organisation_id": user["organisation_id"]})
        outlet_id = outlet_doc["id"]
    doc = {"id": new_id(), "organisation_id": user["organisation_id"], **body.model_dump(), "phone": f"+91{phone}", "outlet_id": outlet_id, "follow_ups": [], "created_at": now_utc()}
    await db.enquiries.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/enquiries/{enquiry_id}")
async def update_enquiry(enquiry_id: str, body: EnquiryBody, user: dict = Depends(get_org_user)):
    res = await db.enquiries.update_one(
        {"id": enquiry_id, "organisation_id": user["organisation_id"]},
        {"$set": {**body.model_dump(), "updated_at": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Enquiry not found")
    return await db.enquiries.find_one({"id": enquiry_id}, {"_id": 0})


class FollowUpBody(BaseModel):
    date: str
    note: Optional[str] = None


@router.post("/enquiries/{enquiry_id}/follow-ups")
async def add_follow_up(enquiry_id: str, body: FollowUpBody, user: dict = Depends(get_org_user)):
    entry = {"date": body.date, "note": body.note, "created_at": now_utc().isoformat(), "created_by": user["id"]}
    res = await db.enquiries.update_one(
        {"id": enquiry_id, "organisation_id": user["organisation_id"]},
        {"$push": {"follow_ups": entry}, "$set": {"follow_up_date": body.date}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Enquiry not found")
    return await db.enquiries.find_one({"id": enquiry_id}, {"_id": 0})


# ---------------- Expenses ----------------

class ExpenseBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = "General"
    date: str
    amount: float = Field(gt=0)
    method: str = "Cash"
    notes: Optional[str] = None
    outlet_id: Optional[str] = None


@router.get("/expenses")
async def list_expenses(month: Optional[int] = None, year: Optional[int] = None, category: Optional[str] = None, outlet_id: Optional[str] = None, user: dict = Depends(get_org_user)):
    q = {"organisation_id": user["organisation_id"]}
    if outlet_id:
        q["outlet_id"] = outlet_id
    if category and category != "all":
        q["category"] = category
    items = await db.expenses.find(q, {"_id": 0}).sort("date", -1).to_list(2000)
    if month and year:
        prefix = f"{year}-{month:02d}"
        items = [e for e in items if str(e.get("date", "")).startswith(prefix)]
    total = sum(e.get("amount", 0) for e in items)
    return {"items": items, "total_amount": total}


@router.post("/expenses")
async def create_expense(body: ExpenseBody, user: dict = Depends(get_org_user)):
    outlet_id = body.outlet_id
    if not outlet_id:
        outlet_doc = await db.outlets.find_one({"organisation_id": user["organisation_id"], "is_primary": True}) or await db.outlets.find_one({"organisation_id": user["organisation_id"]})
        outlet_id = outlet_doc["id"]
    doc = {"id": new_id(), "organisation_id": user["organisation_id"], **body.model_dump(), "outlet_id": outlet_id, "created_at": now_utc()}
    await db.expenses.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/expenses/{expense_id}")
async def update_expense(expense_id: str, body: ExpenseBody, user: dict = Depends(get_org_user)):
    res = await db.expenses.update_one(
        {"id": expense_id, "organisation_id": user["organisation_id"]},
        {"$set": {**body.model_dump(), "updated_at": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Expense not found")
    return await db.expenses.find_one({"id": expense_id}, {"_id": 0})


@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, user: dict = Depends(get_org_user)):
    res = await db.expenses.delete_one({"id": expense_id, "organisation_id": user["organisation_id"]})
    if not res.deleted_count:
        raise HTTPException(404, "Expense not found")
    await audit(user["id"], "expense.deleted", expense_id, org_id=user["organisation_id"])
    return {"message": "Expense deleted"}


# ---------------- Outlets ----------------

class OutletBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    manager: Optional[str] = None


@router.post("/outlets")
async def create_outlet(body: OutletBody, user: dict = Depends(require_manager)):
    doc = {"id": new_id(), "organisation_id": user["organisation_id"], **body.model_dump(), "is_primary": False, "status": "active", "created_at": now_utc()}
    await db.outlets.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/outlets/{outlet_id}")
async def update_outlet(outlet_id: str, body: OutletBody, user: dict = Depends(require_manager)):
    res = await db.outlets.update_one(
        {"id": outlet_id, "organisation_id": user["organisation_id"]},
        {"$set": {**body.model_dump(), "updated_at": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Outlet not found")
    return await db.outlets.find_one({"id": outlet_id}, {"_id": 0})


@router.post("/outlets/{outlet_id}/toggle")
async def toggle_outlet(outlet_id: str, user: dict = Depends(require_manager)):
    outlet = await db.outlets.find_one({"id": outlet_id, "organisation_id": user["organisation_id"]})
    if not outlet:
        raise HTTPException(404, "Outlet not found")
    if outlet.get("is_primary") and outlet.get("status") == "active":
        raise HTTPException(409, "The primary outlet cannot be disabled")
    new_status = "disabled" if outlet.get("status") == "active" else "active"
    await db.outlets.update_one({"id": outlet_id}, {"$set": {"status": new_status}})
    await audit(user["id"], f"outlet.{new_status}", outlet_id, org_id=user["organisation_id"])
    return await db.outlets.find_one({"id": outlet_id}, {"_id": 0})


# ---------------- Staff ----------------

class StaffBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    role: str
    email: Optional[str] = None
    phone: str = Field(min_length=10, max_length=15)
    address: Optional[str] = None
    joining_date: Optional[str] = None
    outlet_id: Optional[str] = None
    salary: Optional[float] = None
    gender: Optional[str] = None
    password: Optional[str] = None


STAFF_ROLES = {"admin", "manager", "receptionist", "trainer", "sales"}


@router.get("/staff")
async def list_staff(user: dict = Depends(get_org_user)):
    return await db.staff.find({"organisation_id": user["organisation_id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("/staff")
async def create_staff(body: StaffBody, user: dict = Depends(require_manager)):
    role = body.role.lower()
    if role not in STAFF_ROLES:
        raise HTTPException(422, "Invalid role")
    phone = normalize_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(422, "Enter a valid 10-digit mobile number")
    email = (body.email or "").strip().lower() or None
    user_id = None
    if body.password:
        if not email:
            raise HTTPException(422, "Email is required to create a login account")
        if len(body.password) < 8:
            raise HTTPException(422, "Password must be at least 8 characters")
        if await db.users.find_one({"email": email}):
            raise HTTPException(409, "A user with this email already exists")
        user_id = new_id()
    outlet_id = body.outlet_id
    if not outlet_id:
        outlet_doc = await db.outlets.find_one({"organisation_id": user["organisation_id"], "is_primary": True}) or await db.outlets.find_one({"organisation_id": user["organisation_id"]})
        outlet_id = outlet_doc["id"]
    doc = {
        "id": new_id(), "organisation_id": user["organisation_id"], "name": body.name.strip(),
        "role": role, "email": email, "phone": f"+91{phone}", "address": body.address,
        "joining_date": body.joining_date or today_ist().isoformat(), "outlet_id": outlet_id,
        "salary": body.salary, "gender": body.gender, "status": "active", "user_id": user_id,
        "has_login": bool(user_id), "created_at": now_utc(),
    }
    if user_id:
        await db.users.insert_one({
            "id": user_id, "full_name": body.name.strip(), "email": email, "phone": f"+91{phone}",
            "role": role, "organisation_id": user["organisation_id"], "staff_id": doc["id"],
            "password_hash": hash_password(body.password), "token_version": 0, "status": "active", "created_at": now_utc(),
        })
    await db.staff.insert_one(doc)
    await db.organisations.update_one({"id": user["organisation_id"]}, {"$set": {"onboarding.staff": True}})
    await audit(user["id"], "staff.created", doc["id"], {"name": doc["name"], "role": doc["role"]}, user["organisation_id"])
    doc.pop("_id", None)
    return doc


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, body: StaffBody, user: dict = Depends(require_manager)):
    data = body.model_dump(exclude={"password"})
    data["role"] = body.role.lower()
    if body.phone:
        data["phone"] = f"+91{normalize_phone(body.phone)}"
    res = await db.staff.update_one(
        {"id": staff_id, "organisation_id": user["organisation_id"]},
        {"$set": {**data, "updated_at": now_utc()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Staff member not found")
    return await db.staff.find_one({"id": staff_id}, {"_id": 0})


@router.post("/staff/{staff_id}/toggle")
async def toggle_staff(staff_id: str, user: dict = Depends(require_manager)):
    staff = await db.staff.find_one({"id": staff_id, "organisation_id": user["organisation_id"]})
    if not staff:
        raise HTTPException(404, "Staff member not found")
    new_status = "disabled" if staff.get("status") == "active" else "active"
    await db.staff.update_one({"id": staff_id}, {"$set": {"status": new_status}})
    if staff.get("user_id"):
        await db.users.update_one({"id": staff["user_id"]}, {"$set": {"status": new_status}})
    await audit(user["id"], f"staff.{new_status}", staff_id, org_id=user["organisation_id"])
    return await db.staff.find_one({"id": staff_id}, {"_id": 0})


# ---------------- Gym profile / settings ----------------

class GymProfileBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    city: Optional[str] = None


@router.put("/gym/profile")
async def update_gym_profile(body: GymProfileBody, user: dict = Depends(require_manager)):
    await db.organisations.update_one({"id": user["organisation_id"]}, {"$set": {"name": body.name.strip(), "city": body.city}})
    return {"message": "Gym profile updated"}


class ProfileBody(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: Optional[str] = None


@router.put("/profile")
async def update_profile(body: ProfileBody, user: dict = Depends(get_org_user)):
    updates = {"full_name": body.full_name.strip()}
    if body.phone:
        p = normalize_phone(body.phone)
        if len(p) == 10:
            updates["phone"] = f"+91{p}"
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {"message": "Profile updated"}


# ---------------- Support requests ----------------

class SupportBody(BaseModel):
    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=5, max_length=2000)


@router.post("/support/requests")
async def create_support_request(body: SupportBody, user: dict = Depends(get_org_user)):
    doc = {
        "id": new_id(),
        "organisation_id": user["organisation_id"],
        "user_id": user["id"],
        "user_name": user.get("full_name"),
        "user_email": user.get("email"),
        "subject": body.subject.strip(),
        "message": body.message.strip(),
        "status": "open",
        "created_at": now_utc(),
    }
    await db.support_requests.insert_one(doc)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc
