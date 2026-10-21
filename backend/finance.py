"""Finance summaries, business reports, and the CSV export center (all finance-access gated).
All money totals are computed in MongoDB (no row caps) on the transaction date (IST calendar day):
payments.payment_date and expenses.date, both 'YYYY-MM-DD'."""
import csv
import io
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from deps import db, today_ist, require_finance_access, parse_day, page_params, add_duration

router = APIRouter(tags=["finance"])

RANGES = ("today", "week", "month", "year", "custom")


def range_days(range_name: str, date_from: Optional[str], date_to: Optional[str]) -> tuple[str, str]:
    """Inclusive IST day range as ISO strings."""
    if range_name not in RANGES:
        raise HTTPException(422, f"range must be one of {', '.join(RANGES)}")
    today = today_ist()
    start_d, end_d = {
        "today": today, "week": today - timedelta(days=today.weekday()),
        "year": today.replace(month=1, day=1), "month": today.replace(day=1),
    }.get(range_name), today
    if range_name == "custom":
        start_d = parse_day(date_from, "date_from")
        end_d = parse_day(date_to, "date_to") or today
        if not start_d:
            raise HTTPException(422, "date_from is required for a custom range")
    if end_d < start_d:
        raise HTTPException(422, "End date must be on or after start date")
    if (end_d - start_d).days > 3700:
        raise HTTPException(422, "Date range is too long (max 10 years)")
    return start_d.isoformat(), end_d.isoformat()


def _scope(org_id: str, outlet_id: Optional[str]) -> dict:
    return {"organisation_id": org_id, **({"outlet_id": outlet_id} if outlet_id else {})}


async def _group(coll, match: dict, key: str) -> dict:
    rows = await db[coll].aggregate([{"$match": match}, {"$group": {"_id": f"${key}", "t": {"$sum": "$amount"}}}]).to_list(None)
    return {(r["_id"] or "Other"): round(r["t"], 2) for r in rows}


async def _sum_count(coll, match: dict, field: str = "amount") -> tuple[float, int]:
    rows = await db[coll].aggregate([{"$match": match}, {"$group": {"_id": None, "t": {"$sum": f"${field}"}, "n": {"$sum": 1}}}]).to_list(1)
    return (round(rows[0]["t"], 2), rows[0]["n"]) if rows else (0, 0)


@router.get("/finance/summary")
async def finance_summary(range: str = "month", date_from: Optional[str] = None, date_to: Optional[str] = None, outlet_id: Optional[str] = None, user: dict = Depends(require_finance_access)):
    start, end = range_days(range, date_from, date_to)
    base = _scope(user["organisation_id"], outlet_id)
    pay_q = {**base, "payment_date": {"$gte": start, "$lte": end}}
    exp_q = {**base, "date": {"$gte": start, "$lte": end}}
    revenue, count = await _sum_count("payments", pay_q)
    expense_total, _ = await _sum_count("expenses", exp_q)
    outstanding, due_count = await _sum_count("members", {**base, "deleted_at": None, "due_amount": {"$gt": 0}}, "due_amount")
    return {
        "revenue": revenue, "expenses": expense_total, "net": round(revenue - expense_total, 2),
        "outstanding": outstanding, "due_member_count": due_count,
        "by_method": await _group("payments", pay_q, "method"),
        "by_type": await _group("payments", pay_q, "type"),
        "expense_by_category": await _group("expenses", exp_q, "category"),
        "transaction_count": count, "date_from": start, "date_to": end,
    }


@router.get("/finance/transactions")
async def finance_transactions(range: str = "month", date_from: Optional[str] = None, date_to: Optional[str] = None, outlet_id: Optional[str] = None,
                               page: int = 1, limit: int = 50, user: dict = Depends(require_finance_access)):
    page, limit = page_params(page, limit)
    start, end = range_days(range, date_from, date_to)
    q = {**_scope(user["organisation_id"], outlet_id), "payment_date": {"$gte": start, "$lte": end}}
    amount, total = await _sum_count("payments", q)
    items = await db.payments.find(q, {"_id": 0}).sort([("payment_date", -1), ("created_at", -1), ("id", -1)]).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": items, "total": total, "amount_total": amount, "page": page, "limit": limit}


# ---------------- Reports ----------------

def _month_windows(months: int) -> list[tuple[str, str, str]]:
    if not 1 <= months <= 36:
        raise HTTPException(422, "months must be between 1 and 36")
    first = today_ist().replace(day=1)
    out = []
    for i in range(months - 1, -1, -1):
        s = add_duration(first, "months", -i)
        e = add_duration(s, "months", 1) - timedelta(days=1)
        out.append((s.strftime("%b %Y"), s.isoformat(), e.isoformat()))
    return out


async def _by_month(coll: str, field: str, org_id: str, start: str, end: str) -> dict:
    rows = await db[coll].aggregate([
        {"$match": {"organisation_id": org_id, field: {"$gte": start, "$lte": end}}},
        {"$group": {"_id": {"$substrCP": [f"${field}", 0, 7]}, "t": {"$sum": "$amount"}}},
    ]).to_list(None)
    return {r["_id"]: round(r["t"], 2) for r in rows}


@router.get("/reports/revenue-trend")
async def report_revenue_trend(months: int = 6, user: dict = Depends(require_finance_access)):
    org_id = user["organisation_id"]
    wins = _month_windows(months)
    rev = await _by_month("payments", "payment_date", org_id, wins[0][1], wins[-1][2])
    exp = await _by_month("expenses", "date", org_id, wins[0][1], wins[-1][2])
    points = []
    for label, s, _ in wins:
        r, e = rev.get(s[:7], 0), exp.get(s[:7], 0)
        points.append({"month": label, "revenue": r, "expenses": e, "net": round(r - e, 2)})
    return {"points": points}


@router.get("/reports/outstanding-dues")
async def report_outstanding_dues(page: int = 1, limit: int = 100, user: dict = Depends(require_finance_access)):
    page, limit = page_params(page, limit, 500)
    q = {"organisation_id": user["organisation_id"], "deleted_at": None, "due_amount": {"$gt": 0}}
    total, count = await _sum_count("members", q, "due_amount")
    items = await db.members.find(
        q, {"_id": 0, "id": 1, "full_name": 1, "phone": 1, "member_code": 1, "plan_name": 1, "due_amount": 1, "membership_expiry": 1},
    ).sort([("due_amount", -1), ("id", 1)]).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": items, "total": total, "count": count, "page": page, "limit": limit}


@router.get("/reports/membership-expiry")
async def report_membership_expiry(days: int = 30, page: int = 1, limit: int = 100, user: dict = Depends(require_finance_access)):
    if not 1 <= days <= 365:
        raise HTTPException(422, "days must be between 1 and 365")
    page, limit = page_params(page, limit, 500)
    today = today_ist()
    q = {"organisation_id": user["organisation_id"], "deleted_at": None,
         "membership_expiry": {"$gte": today.isoformat(), "$lte": (today + timedelta(days=days)).isoformat()}}
    count = await db.members.count_documents(q)
    members = await db.members.find(
        q, {"_id": 0, "id": 1, "full_name": 1, "phone": 1, "member_code": 1, "plan_name": 1, "membership_expiry": 1, "due_amount": 1},
    ).sort([("membership_expiry", 1), ("id", 1)]).skip((page - 1) * limit).limit(limit).to_list(limit)
    for m in members:
        m["days_left"] = (datetime.fromisoformat(str(m["membership_expiry"])[:10]).date() - today).days
    return {"items": members, "count": count, "page": page, "limit": limit}


@router.get("/reports/enquiry-conversion")
async def report_enquiry_conversion(user: dict = Depends(require_finance_access)):
    q = {"organisation_id": user["organisation_id"]}

    async def counts(field: str, default: str) -> dict:
        rows = await db.enquiries.aggregate([{"$match": q}, {"$group": {"_id": f"${field}", "n": {"$sum": 1}}}]).to_list(None)
        return {(r["_id"] or default): r["n"] for r in rows}
    by_status, by_source = await counts("status", "New"), await counts("source", "Other")
    total = sum(by_status.values())
    converted = by_status.get("Converted", 0)
    return {"total": total, "converted": converted, "rate": round(100 * converted / total, 1) if total else 0, "by_status": by_status, "by_source": by_source}


@router.get("/reports/member-growth")
async def report_member_growth(months: int = 6, user: dict = Depends(require_finance_access)):
    org_id = user["organisation_id"]
    points = []
    for label, s, e in _month_windows(months):
        joined = await db.members.count_documents({"organisation_id": org_id, "joining_date": {"$gte": s, "$lte": e}})
        total = await db.members.count_documents({"organisation_id": org_id, "joining_date": {"$lte": e}, "deleted_at": None})
        points.append({"month": label, "joined": joined, "total": total})
    return {"points": points}


# ---------------- Export Center ----------------

EXPORTS = {
    "members": ("members", ["member_code", "full_name", "phone", "email", "gender", "plan_name", "joining_date", "membership_expiry", "due_amount", "credit_balance", "batch", "trainer"], None),
    "payments": ("payments", ["payment_date", "receipt_no", "member_name", "type", "status", "reversal_of", "plan_name", "amount", "method", "created_at"], "payment_date"),
    "attendance": ("attendance", ["member_name", "member_code", "check_in", "check_out"], None),
    "expenses": ("expenses", ["date", "name", "category", "amount", "method", "notes"], "date"),
    "enquiries": ("enquiries", ["name", "phone", "email", "status", "source", "category", "follow_up_date", "created_at"], None),
    "staff": ("staff", ["name", "role", "email", "phone", "joining_date", "status", "salary"], None),
    "plans": ("plans", ["name", "type", "category", "duration_type", "duration", "price", "status"], None),
}


def _cell(v):
    """CSV cell; text starting with = + - @ is prefixed with ' so spreadsheets don't run it as a formula."""
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


@router.get("/export/{dataset}")
async def export_dataset(dataset: str, outlet_id: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
                         user: dict = Depends(require_finance_access)):
    if dataset not in EXPORTS:
        raise HTTPException(404, "Unknown dataset")
    collection, fields, date_field = EXPORTS[dataset]
    q = _scope(user["organisation_id"], outlet_id)
    if dataset == "members":
        q["deleted_at"] = None
    d_from, d_to = parse_day(date_from, "date_from"), parse_day(date_to, "date_to")
    if d_from and d_to and d_to < d_from:
        raise HTTPException(422, "End date must be on or after start date")
    if date_field and (d_from or d_to):
        q[date_field] = {**({"$gte": d_from.isoformat()} if d_from else {}), **({"$lte": d_to.isoformat()} if d_to else {})}
    sort = [(date_field, 1)] if date_field else [("_id", 1)]

    async def rows():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        async for r in db[collection].find(q, {"_id": 0, **{f: 1 for f in fields}}).sort(sort):
            writer.writerow({k: _cell(v) for k, v in r.items()})
            if buf.tell() > 64_000:
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate()
        yield buf.getvalue()

    return StreamingResponse(rows(), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="gymboss_{dataset}_{today_ist().isoformat()}.csv"'})
