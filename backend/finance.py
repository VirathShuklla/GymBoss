import csv
import io
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from deps import db, IST, today_ist, require_finance_access, member_status

router = APIRouter(tags=["finance"])


def range_bounds(range_name: str, date_from: Optional[str], date_to: Optional[str]):
    today = today_ist()
    if range_name == "today":
        start_d = today
    elif range_name == "week":
        start_d = today - timedelta(days=today.weekday())
    elif range_name == "year":
        start_d = today.replace(month=1, day=1)
    elif range_name == "custom" and date_from:
        start_d = datetime.fromisoformat(date_from).date()
    else:
        start_d = today.replace(day=1)
    end_d = datetime.fromisoformat(date_to).date() if (range_name == "custom" and date_to) else today
    start = datetime.combine(start_d, datetime.min.time(), tzinfo=IST)
    end = datetime.combine(end_d + timedelta(days=1), datetime.min.time(), tzinfo=IST)
    return start, end


@router.get("/finance/summary")
async def finance_summary(range: str = "month", date_from: Optional[str] = None, date_to: Optional[str] = None, outlet_id: Optional[str] = None, user: dict = Depends(require_finance_access)):
    org_id = user["organisation_id"]
    start, end = range_bounds(range, date_from, date_to)
    pay_q = {"organisation_id": org_id, "created_at": {"$gte": start, "$lt": end}}
    exp_q = {"organisation_id": org_id, "created_at": {"$gte": start, "$lt": end}}
    if outlet_id:
        pay_q["outlet_id"] = outlet_id
        exp_q["outlet_id"] = outlet_id
    payments = await db.payments.find(pay_q).to_list(5000)
    expenses = await db.expenses.find(exp_q).to_list(2000)

    revenue = sum(p.get("amount", 0) for p in payments)
    expense_total = sum(e.get("amount", 0) for e in expenses)
    by_method, by_type, by_category = {}, {}, {}
    for p in payments:
        by_method[p.get("method", "Other")] = by_method.get(p.get("method", "Other"), 0) + p.get("amount", 0)
        by_type[p.get("type", "other")] = by_type.get(p.get("type", "other"), 0) + p.get("amount", 0)
    for e in expenses:
        by_category[e.get("category", "General")] = by_category.get(e.get("category", "General"), 0) + e.get("amount", 0)

    due_q = {"organisation_id": org_id, "deleted_at": None, "due_amount": {"$gt": 0}}
    if outlet_id:
        due_q["outlet_id"] = outlet_id
    due_members = await db.members.find(due_q, {"due_amount": 1}).to_list(10000)
    outstanding = sum(m.get("due_amount", 0) for m in due_members)

    return {
        "revenue": revenue,
        "expenses": expense_total,
        "net": revenue - expense_total,
        "outstanding": outstanding,
        "due_member_count": len(due_members),
        "by_method": by_method,
        "by_type": by_type,
        "expense_by_category": by_category,
        "transaction_count": len(payments),
    }


@router.get("/finance/transactions")
async def finance_transactions(range: str = "month", date_from: Optional[str] = None, date_to: Optional[str] = None, outlet_id: Optional[str] = None, user: dict = Depends(require_finance_access)):
    start, end = range_bounds(range, date_from, date_to)
    q = {"organisation_id": user["organisation_id"], "created_at": {"$gte": start, "$lt": end}}
    if outlet_id:
        q["outlet_id"] = outlet_id
    return await db.payments.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


# ---------------- Reports ----------------

@router.get("/reports/revenue-trend")
async def report_revenue_trend(months: int = 6, user: dict = Depends(require_finance_access)):
    org_id = user["organisation_id"]
    today = today_ist()
    points = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1, tzinfo=IST)
        end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=IST)
        rev = sum(p.get("amount", 0) for p in await db.payments.find({"organisation_id": org_id, "created_at": {"$gte": start, "$lt": end}}, {"amount": 1}).to_list(5000))
        exp = sum(e.get("amount", 0) for e in await db.expenses.find({"organisation_id": org_id, "created_at": {"$gte": start, "$lt": end}}, {"amount": 1}).to_list(2000))
        points.append({"month": start.strftime("%b %Y"), "revenue": rev, "expenses": exp, "net": rev - exp})
    return {"points": points}


@router.get("/reports/outstanding-dues")
async def report_outstanding_dues(user: dict = Depends(require_finance_access)):
    members = await db.members.find(
        {"organisation_id": user["organisation_id"], "deleted_at": None, "due_amount": {"$gt": 0}},
        {"_id": 0, "id": 1, "full_name": 1, "phone": 1, "member_code": 1, "plan_name": 1, "due_amount": 1, "membership_expiry": 1},
    ).sort("due_amount", -1).to_list(5000)
    return {"items": members, "total": sum(m.get("due_amount", 0) for m in members)}


@router.get("/reports/membership-expiry")
async def report_membership_expiry(days: int = 30, user: dict = Depends(require_finance_access)):
    today = today_ist()
    limit = (today + timedelta(days=days)).isoformat()
    members = await db.members.find(
        {"organisation_id": user["organisation_id"], "deleted_at": None, "membership_expiry": {"$gte": today.isoformat(), "$lte": limit}},
        {"_id": 0, "id": 1, "full_name": 1, "phone": 1, "member_code": 1, "plan_name": 1, "membership_expiry": 1, "due_amount": 1},
    ).sort("membership_expiry", 1).to_list(5000)
    for m in members:
        m["days_left"] = (datetime.fromisoformat(str(m["membership_expiry"])[:10]).date() - today).days
    return {"items": members}


@router.get("/reports/enquiry-conversion")
async def report_enquiry_conversion(user: dict = Depends(require_finance_access)):
    items = await db.enquiries.find({"organisation_id": user["organisation_id"]}, {"_id": 0, "status": 1, "source": 1, "name": 1, "phone": 1, "created_at": 1}).to_list(5000)
    by_status, by_source = {}, {}
    for e in items:
        by_status[e.get("status", "New")] = by_status.get(e.get("status", "New"), 0) + 1
        by_source[e.get("source", "Other")] = by_source.get(e.get("source", "Other"), 0) + 1
    converted = by_status.get("Converted", 0)
    return {"total": len(items), "converted": converted, "rate": round(100 * converted / len(items), 1) if items else 0, "by_status": by_status, "by_source": by_source}


@router.get("/reports/member-growth")
async def report_member_growth(months: int = 6, user: dict = Depends(require_finance_access)):
    org_id = user["organisation_id"]
    today = today_ist()
    points = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1, tzinfo=IST)
        end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=IST)
        joined = await db.members.count_documents({"organisation_id": org_id, "created_at": {"$gte": start, "$lt": end}})
        total = await db.members.count_documents({"organisation_id": org_id, "created_at": {"$lt": end}, "deleted_at": None})
        points.append({"month": start.strftime("%b %Y"), "joined": joined, "total": total})
    return {"points": points}


# ---------------- Export Center ----------------

EXPORTS = {
    "members": ("members", {"_id": 0, "member_code": 1, "full_name": 1, "phone": 1, "email": 1, "gender": 1, "plan_name": 1, "joining_date": 1, "membership_expiry": 1, "due_amount": 1, "batch": 1, "trainer": 1}),
    "payments": ("payments", {"_id": 0, "receipt_no": 1, "member_name": 1, "type": 1, "plan_name": 1, "amount": 1, "method": 1, "created_at": 1}),
    "attendance": ("attendance", {"_id": 0, "member_name": 1, "member_code": 1, "check_in": 1, "check_out": 1}),
    "expenses": ("expenses", {"_id": 0, "name": 1, "category": 1, "date": 1, "amount": 1, "method": 1, "notes": 1}),
    "enquiries": ("enquiries", {"_id": 0, "name": 1, "phone": 1, "email": 1, "status": 1, "source": 1, "category": 1, "follow_up_date": 1, "created_at": 1}),
    "staff": ("staff", {"_id": 0, "name": 1, "role": 1, "email": 1, "phone": 1, "joining_date": 1, "status": 1, "salary": 1}),
    "plans": ("plans", {"_id": 0, "name": 1, "type": 1, "category": 1, "duration_type": 1, "duration": 1, "price": 1, "status": 1}),
}


@router.get("/export/{dataset}")
async def export_dataset(dataset: str, outlet_id: Optional[str] = None, user: dict = Depends(require_finance_access)):
    if dataset not in EXPORTS:
        raise HTTPException(404, "Unknown dataset")
    collection, projection = EXPORTS[dataset]
    q = {"organisation_id": user["organisation_id"]}
    if outlet_id:
        q["outlet_id"] = outlet_id
    if dataset == "members":
        q["deleted_at"] = None
    rows = await db[collection].find(q, projection).to_list(20000)
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(projection.keys())[1:])
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items() if k in projection})
    else:
        buf.write("no data\n")
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="gymboss_{dataset}_{today_ist().isoformat()}.csv"'},
    )
