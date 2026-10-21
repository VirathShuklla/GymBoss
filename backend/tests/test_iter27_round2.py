"""Iter27 (Round 2): IST transaction-date reporting beyond old caps, IST boundaries, legacy backfill, reversals,
typed params, upload sniffing/limits, native token rotation on password change, subscription purchase snapshots, health.
In-process against ISOLATED db gymboss_r2_tests. Run: pytest -n 0 tests/test_iter27_round2.py"""
import os
import csv
import io
import uuid
import random
import asyncio
from datetime import datetime, timedelta, timezone, date
from types import SimpleNamespace

os.environ["DB_NAME"] = "gymboss_r2_tests"
import paths  # noqa: F401,E402

import pytest  # noqa: E402
import httpx  # noqa: E402

import deps  # noqa: E402
import server  # noqa: E402
import members  # noqa: E402
import billing  # noqa: E402
import billing_sync  # noqa: E402

db = deps.db
assert db.name == "gymboss_r2_tests"
LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)
PW = "R2Test@2026"


def run(coro):
    return LOOP.run_until_complete(coro)


@pytest.fixture(scope="module", autouse=True)
def isolated_db():
    run(deps.client.drop_database("gymboss_r2_tests"))
    run(server.ensure_indexes())
    yield
    run(deps.client.drop_database("gymboss_r2_tests"))


def phone():
    return "9" + "".join(random.choice("0123456789") for _ in range(9))


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app, raise_app_exceptions=False), base_url="https://test", timeout=300)


async def tenant(headers=None):
    c = client()
    email = f"r2_{uuid.uuid4().hex[:10]}@example.com"
    r = await c.post("/api/auth/register", json={"full_name": "R2 Owner", "email": email, "phone": phone(), "password": PW,
                                                 "gym_name": "R2 Gym", "outlet_name": "Main"}, headers=headers or {})
    assert r.status_code == 200, r.text
    org_id = r.json()["organisation"]["id"]
    r2 = await c.post("/api/plans", json={"name": "Monthly", "type": "membership", "duration_type": "months", "duration": 1, "price": 1000})
    assert r2.status_code == 200, r2.text
    return c, org_id, r2.json()["id"], email, r.json()


def month_firsts(n=6):
    first = deps.today_ist().replace(day=1)
    return [deps.add_duration(first, "months", -i) for i in range(n - 1, -1, -1)]


# ---------------- Bulk reports beyond old caps ----------------
BULK = {}


async def bulk_setup():
    if BULK:
        return BULK
    c, org_id, plan_id, _, _ = await tenant()
    today = deps.today_ist()
    firsts = month_firsts(6)
    base_ts = datetime(2026, 5, 1, tzinfo=timezone.utc)
    pays, exps, mems = [], [], []
    for i in range(6200):
        f = firsts[i % 6]
        day = 1 + (i * 7) % 28
        if f.month == today.month and f.year == today.year:
            day = min(day, today.day)
        pays.append({"id": f"p{i:05d}", "organisation_id": org_id, "member_id": "m", "member_name": f"TEST_M{i}", "receipt_no": f"R{i}",
                     "type": ["membership", "admission", "renewal"][i % 3], "method": ["Cash", "UPI", "Card", "Bank"][i % 4],
                     "amount": 100 + (i % 997), "payment_date": f.replace(day=day).isoformat(), "status": "active",
                     "created_at": base_ts + timedelta(minutes=i // 1000)})  # many identical created_at -> ties
    for i in range(2600):
        f = firsts[i % 6]
        day = 1 + (i * 5) % 28
        if f.month == today.month and f.year == today.year:
            day = min(day, today.day)
        exps.append({"id": f"e{i:05d}", "organisation_id": org_id, "name": f"TEST_E{i}", "category": ["Rent", "Salary", "Power", "Misc", "Gear"][i % 5],
                     "amount": 50 + (i % 311), "method": "Cash", "date": f.replace(day=day).isoformat(), "created_at": base_ts})
    for i in range(700):
        mems.append({"id": f"mem{i:04d}", "organisation_id": org_id, "full_name": f"TEST_D{i}", "member_code": f"D{i:04d}", "phone": f"90000{i:05d}",
                     "deleted_at": None, "due_amount": 10 + i % 50, "created_at": base_ts})
    await db.payments.insert_many([dict(p) for p in pays])
    await db.expenses.insert_many([dict(e) for e in exps])
    await db.members.insert_many([dict(m) for m in mems])
    BULK.update(c=c, org_id=org_id, pays=pays, exps=exps, mems=mems, firsts=firsts, today=today)
    return BULK


def _in(rows, field, s, e):
    return [r for r in rows if s <= r[field] <= e]


def _grp(rows, key):
    out = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + r["amount"]
    return out


def test_finance_summary_exact_beyond_caps():
    async def go():
        b = await bulk_setup()
        c, today = b["c"], b["today"]
        ranges = [(b["firsts"][0].isoformat(), today.isoformat()), (b["firsts"][2].isoformat(), (deps.add_duration(b["firsts"][2], "months", 1) - timedelta(days=1)).isoformat())]
        for s, e in ranges:
            r = await c.get("/api/finance/summary", params={"range": "custom", "date_from": s, "date_to": e})
            assert r.status_code == 200, r.text
            d = r.json()
            P, E = _in(b["pays"], "payment_date", s, e), _in(b["exps"], "date", s, e)
            assert d["revenue"] == sum(p["amount"] for p in P), (s, e, d["revenue"])
            assert d["transaction_count"] == len(P)
            assert d["expenses"] == sum(x["amount"] for x in E)
            assert d["by_method"] == _grp(P, "method")
            assert d["by_type"] == _grp(P, "type")
            assert d["expense_by_category"] == _grp(E, "category")
            assert d["outstanding"] == sum(m["due_amount"] for m in b["mems"]) and d["due_member_count"] == 700
        r = await c.get("/api/finance/summary", params={"range": "year"})
        d = r.json()
        P = _in(b["pays"], "payment_date", today.replace(month=1, day=1).isoformat(), today.isoformat())
        assert d["revenue"] == sum(p["amount"] for p in P) and d["transaction_count"] == len(P)
        assert len(P) > 5000
    run(go())


def test_finance_transactions_pagination_stable():
    async def go():
        b = await bulk_setup()
        c, s, e = b["c"], b["firsts"][0].isoformat(), b["today"].isoformat()
        P = _in(b["pays"], "payment_date", s, e)
        seen, last, page = [], None, 1
        while True:
            r = await c.get("/api/finance/transactions", params={"range": "custom", "date_from": s, "date_to": e, "page": page, "limit": 200})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["total"] == len(P) and d["amount_total"] == sum(p["amount"] for p in P)
            if not d["items"]:
                break
            for it in d["items"]:
                if last:
                    assert it["payment_date"] <= last
                last = it["payment_date"]
                seen.append(it["id"])
            page += 1
        dup = len(seen) - len(set(seen))
        assert dup == 0, f"{dup} duplicate rows across pages (unstable sort: ties on payment_date+created_at, no unique tiebreaker)"
        assert len(seen) == len(P)
    run(go())


def test_revenue_trend_and_dues_and_expenses_exact():
    async def go():
        b = await bulk_setup()
        c = b["c"]
        r = await c.get("/api/reports/revenue-trend", params={"months": 6})
        pts = r.json()["points"]
        assert len(pts) == 6
        for f, pt in zip(b["firsts"], pts):
            ym = f.isoformat()[:7]
            assert pt["revenue"] == sum(p["amount"] for p in b["pays"] if p["payment_date"][:7] == ym), pt
            assert pt["expenses"] == sum(x["amount"] for x in b["exps"] if x["date"][:7] == ym), pt
        ids = []
        for page in (1, 2, 3):
            d = (await c.get("/api/reports/outstanding-dues", params={"page": page, "limit": 300})).json()
            assert d["count"] == 700 and d["total"] == sum(m["due_amount"] for m in b["mems"])
            ids += [i["id"] for i in d["items"]]
        assert len(ids) == 700 == len(set(ids))
        f = b["firsts"][3]
        E = [x for x in b["exps"] if x["date"][:7] == f.isoformat()[:7]]
        got = []
        page = 1
        while True:
            d = (await c.get("/api/expenses", params={"month": f.month, "year": f.year, "page": page, "limit": 100})).json()
            assert d["total"] == len(E) and d["total_amount"] == sum(x["amount"] for x in E)
            if not d["items"]:
                break
            got += [x["id"] for x in d["items"]]
            page += 1
        assert len(got) == len(E) == len(set(got))
        # /api/payments list with date filter
        s, e = f.isoformat(), (deps.add_duration(f, "months", 1) - timedelta(days=1)).isoformat()
        d = (await c.get("/api/payments", params={"date_from": s, "date_to": e, "limit": 200})).json()
        assert d["total"] == len(_in(b["pays"], "payment_date", s, e))
    run(go())


def test_exports_all_rows_and_date_filters():
    async def go():
        b = await bulk_setup()
        c = b["c"]
        r = await c.get("/api/export/payments")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert len(rows) == len(b["pays"])
        r = await c.get("/api/export/expenses")
        assert len(list(csv.DictReader(io.StringIO(r.text)))) == len(b["exps"])
        f = b["firsts"][1]
        s, e = f.isoformat(), (deps.add_duration(f, "months", 1) - timedelta(days=1)).isoformat()
        rows = list(csv.DictReader(io.StringIO((await c.get("/api/export/payments", params={"date_from": s, "date_to": e})).text)))
        assert len(rows) == len(_in(b["pays"], "payment_date", s, e)) and all(s <= x["payment_date"] <= e for x in rows)
        rows = list(csv.DictReader(io.StringIO((await c.get("/api/export/expenses", params={"date_from": s, "date_to": e})).text)))
        assert len(rows) == len(_in(b["exps"], "date", s, e)) and all(s <= x["date"] <= e for x in rows)
        r = await c.get("/api/export/members")
        assert len(list(csv.DictReader(io.StringIO(r.text)))) == 700
        assert (await c.get("/api/export/payments", params={"date_from": "2026-1-5"})).status_code == 422
    run(go())


# ---------------- IST boundaries / backdated / dashboard ----------------
def test_ist_month_boundaries_and_backdated_and_dashboard():
    async def go():
        c, org_id, plan_id, _, _ = await tenant()
        base = {"organisation_id": org_id, "member_id": "x", "type": "membership", "method": "Cash", "status": "active"}
        await db.payments.insert_many([
            {**base, "id": "b1", "amount": 111, "payment_date": "2026-09-01", "created_at": datetime(2026, 8, 31, 18, 45, tzinfo=timezone.utc)},
            {**base, "id": "b2", "amount": 222, "payment_date": "2026-09-30", "created_at": datetime(2026, 9, 30, 18, 20, tzinfo=timezone.utc)},
            {**base, "id": "b3", "amount": 333, "created_at": datetime(2026, 8, 31, 18, 45, tzinfo=timezone.utc)},  # legacy -> 2026-09-01
            {**base, "id": "b4", "amount": 444, "created_at": datetime(2026, 8, 31, 18, 15, tzinfo=timezone.utc)},  # legacy -> 2026-08-31 (23:45 IST)
        ])
        await server.backfill_txn_dates()
        assert (await db.payments.find_one({"id": "b3"}))["payment_date"] == "2026-09-01"
        assert (await db.payments.find_one({"id": "b4"}))["payment_date"] == "2026-08-31"
        sep = (await c.get("/api/finance/summary", params={"range": "custom", "date_from": "2026-09-01", "date_to": "2026-09-30"})).json()
        aug = (await c.get("/api/finance/summary", params={"range": "custom", "date_from": "2026-08-01", "date_to": "2026-08-31"})).json()
        assert sep["revenue"] == 666 and sep["transaction_count"] == 3, sep
        assert aug["revenue"] == 444 and aug["transaction_count"] == 1, aug
        # back-dated payment via API
        r = await c.post("/api/members", json={"full_name": "TEST_R2 Member", "phone": phone(), "plan_id": plan_id, "amount_paid": 0})
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        r = await c.post("/api/payments", json={"member_id": mid, "amount": 75, "payment_date": "2026-07-15"})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        jul = (await c.get("/api/finance/summary", params={"range": "custom", "date_from": "2026-07-01", "date_to": "2026-07-31"})).json()
        assert jul["revenue"] == 75
        # dashboard today_collection: only payment_date == today IST
        before = (await c.get("/api/dashboard/summary")).json()["today_collection"]
        await db.payments.insert_one({**base, "id": "yday", "amount": 999, "payment_date": (deps.today_ist() - timedelta(days=1)).isoformat(), "created_at": deps.now_utc()})
        r = await c.post("/api/payments", json={"member_id": mid, "amount": 40})
        assert r.status_code == 200
        after = (await c.get("/api/dashboard/summary")).json()["today_collection"]
        assert round(after - before, 2) == 40, (before, after)
        # reversal: original stays on its date; negative entry on today IST
        r = await c.delete(f"/api/payments/{pid}")
        assert r.status_code == 200, r.text
        orig = await db.payments.find_one({"id": pid})
        assert orig["status"] == "reversed" and orig["payment_date"] == "2026-07-15" and orig["amount"] == 75
        rev = await db.payments.find_one({"reversal_of": pid})
        today = deps.today_ist().isoformat()
        assert rev["amount"] == -75 and rev["payment_date"] == today
        jul2 = (await c.get("/api/finance/summary", params={"range": "custom", "date_from": "2026-07-01", "date_to": "2026-07-31"})).json()
        assert jul2["revenue"] == 75
        tod = (await c.get("/api/finance/summary", params={"range": "custom", "date_from": today, "date_to": today})).json()
        assert tod["revenue"] == 40 - 75, tod
        await c.aclose()
    run(go())


def test_legacy_backfill_idempotent():
    async def go():
        org = f"legacy-{uuid.uuid4().hex[:6]}"
        ca = datetime(2026, 3, 31, 19, 0, tzinfo=timezone.utc)  # IST 2026-04-01 00:30
        await db.payments.insert_one({"id": "lp1", "organisation_id": org, "amount": 1, "created_at": ca})
        await db.payments.insert_one({"id": "lp2", "organisation_id": org, "amount": 1, "payment_date": None, "created_at": ca})
        await db.expenses.insert_many([
            {"id": "le1", "organisation_id": org, "amount": 1, "created_at": ca},
            {"id": "le2", "organisation_id": org, "amount": 1, "date": "2026-02-10T15:30:00+00:00", "created_at": ca},
            {"id": "le3", "organisation_id": org, "amount": 1, "date": "", "created_at": ca},
        ])
        await db.members.insert_one({"id": "lm1", "organisation_id": org, "full_name": "TEST_L", "member_code": "L1", "created_at": ca})
        await server.backfill_txn_dates()
        await server.backfill_txn_dates()
        assert (await db.payments.find_one({"id": "lp1"}))["payment_date"] == "2026-04-01"
        assert (await db.payments.find_one({"id": "lp2"}))["payment_date"] == "2026-04-01"
        assert (await db.expenses.find_one({"id": "le1"}))["date"] == "2026-04-01"
        assert (await db.expenses.find_one({"id": "le2"}))["date"] == "2026-02-10"
        assert (await db.expenses.find_one({"id": "le3"}))["date"] == "2026-04-01"
        assert (await db.members.find_one({"id": "lm1"}))["joining_date"] == "2026-04-01"
    run(go())


# ---------------- Typed params ----------------
def test_typed_params_422():
    async def go():
        c, _, _, _, _ = await tenant()
        bad = [
            ("/api/finance/summary", {"range": "custom", "date_from": "2026-13-01"}),
            ("/api/finance/summary", {"range": "custom", "date_from": "abc"}),
            ("/api/finance/summary", {"range": "custom", "date_from": "2026-1-5"}),
            ("/api/finance/summary", {"range": "custom", "date_from": "2026-05-10", "date_to": "2026-05-01"}),
            ("/api/finance/summary", {"range": "custom"}),
            ("/api/finance/summary", {"range": "bogus"}),
            ("/api/finance/transactions", {"limit": 0}),
            ("/api/finance/transactions", {"limit": 201}),
            ("/api/finance/transactions", {"page": 0}),
            ("/api/finance/transactions", {"range": "custom", "date_from": "2026-02-30"}),
            ("/api/reports/revenue-trend", {"months": 0}),
            ("/api/reports/revenue-trend", {"months": 37}),
            ("/api/reports/member-growth", {"months": 37}),
            ("/api/reports/membership-expiry", {"days": 0}),
            ("/api/reports/membership-expiry", {"days": 366}),
            ("/api/reports/outstanding-dues", {"limit": 501}),
            ("/api/expenses", {"month": 13, "year": 2026}),
            ("/api/expenses", {"month": 5}),
            ("/api/expenses", {"month": "x", "year": 2026}),
            ("/api/payments", {"date_from": "2026-13-01"}),
            ("/api/payments", {"limit": 201}),
            ("/api/export/expenses", {"date_to": "abc"}),
        ]
        fails = []
        for path, params in bad:
            r = await c.get(path, params=params)
            if r.status_code != 422:
                fails.append((path, params, r.status_code))
        for d in ("2026-13-01", "abc", "", None):
            r = await c.post("/api/expenses", json={"name": "TEST_Exp", "category": "Misc", "date": d, "amount": 10})
            if r.status_code != 422:
                fails.append(("POST /expenses", d, r.status_code))
        r = await c.post("/api/expenses", json={"name": "TEST_Exp", "category": "Misc", "date": "2026-05-01", "amount": 10})
        assert r.status_code == 200 and r.json()["date"] == "2026-05-01"
        eid = r.json()["id"]
        r = await c.put(f"/api/expenses/{eid}", json={"name": "TEST_Exp", "category": "Misc", "date": "2026-02-31", "amount": 10})
        if r.status_code != 422:
            fails.append(("PUT /expenses", r.status_code))
        r = await c.post("/api/payments", json={"member_id": "x", "amount": 1, "payment_date": "2026-13-01"})
        if r.status_code != 422:
            fails.append(("POST /payments bad date", r.status_code))
        assert not fails, fails
        await c.aclose()
    run(go())


# ---------------- Uploads ----------------
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 100
PDF = b"%PDF-1.4\n%test\n" + b"\x00" * 100
GIF = b"GIF89a" + b"\x00" * 100


def test_uploads_sniffing_limits_and_serving(monkeypatch):
    store = {}

    async def put_object(path, data, ct):
        store[path] = data
        return {"path": path}

    async def get_object(path):
        return store[path], "application/octet-stream"
    monkeypatch.setattr(members, "put_object", put_object)
    monkeypatch.setattr(members, "get_object", get_object)

    async def up(c, name, data, mime, kind=None):
        return await c.post("/api/uploads", files={"file": (name, data, mime)}, data={"kind": kind} if kind else {})

    async def go():
        c, org_id, _, _, _ = await tenant()
        ok = [("a.jpg", JPEG, "image/png", "photo", "image/jpeg"), ("b.txt", PNG, "text/plain", "photo", "image/png"),
              ("c.bin", WEBP, "application/octet-stream", "photo", "image/webp"), ("d.png", PDF, "image/png", "attachment", "application/pdf")]
        ids = {}
        for name, data, mime, kind, want in ok:
            r = await up(c, name, data, mime, kind)
            assert r.status_code == 200, (name, r.text)
            fid = r.json()["id"]
            ids[want] = fid
            assert (await db.files.find_one({"id": fid}))["content_type"] == want
            g = await c.get(f"/api/files/{fid}")
            assert g.status_code == 200 and g.headers["content-type"] == want and g.headers["x-content-type-options"] == "nosniff"
        bad = [("x.png", b"hello world, not an image", "image/png", "photo", 422), ("g.gif", GIF, "image/gif", "attachment", 422),
               ("p.pdf", PDF, "application/pdf", "photo", 422), ("e.png", b"", "image/png", "photo", 422),
               ("big.jpg", JPEG + b"\x00" * (5 * 1024 * 1024), "image/jpeg", "photo", 413),
               ("k.jpg", JPEG, "image/jpeg", "evil", 422)]
        for name, data, mime, kind, code in bad:
            r = await up(c, name, data, mime, kind)
            assert r.status_code == code, (name, r.status_code, r.text[:200])
        # exactly 5 MB accepted
        r = await up(c, "five.jpg", JPEG + b"\x00" * (5 * 1024 * 1024 - len(JPEG)), "image/jpeg", "photo")
        assert r.status_code == 200, r.text[:200]
        # huge declared Content-Length rejected before reading
        r = await c.post("/api/uploads", content=b"--x--\r\n", headers={"Content-Type": "multipart/form-data; boundary=x", "Content-Length": str(50 * 1024 * 1024)})
        assert r.status_code == 413, r.status_code
        # legacy file with unsafe stored bytes
        store["legacy/evil.html"] = b"<html><script>alert(1)</script></html>"
        await db.files.insert_one({"id": "legacy-f1", "organisation_id": org_id, "storage_path": "legacy/evil.html", "original_filename": "ev\"il.html",
                                   "content_type": "text/html", "is_deleted": False, "created_at": deps.now_utc()})
        g = await c.get("/api/files/legacy-f1")
        assert g.status_code == 200 and g.headers["content-type"] == "application/octet-stream"
        assert g.headers["content-disposition"].startswith("attachment") and g.headers["content-security-policy"] == "sandbox"
        assert g.headers["x-content-type-options"] == "nosniff"
        # tenant isolation
        c2, _, _, _, _ = await tenant()
        assert (await c2.get(f"/api/files/{ids['image/jpeg']}")).status_code == 403
        assert (await c2.get("/api/files/nonexistent")).status_code == 404
        await c.aclose()
        await c2.aclose()
    run(go())


# ---------------- Password change native tokens ----------------
def test_change_password_native_tokens_rotate():
    async def go():
        NAT = {"X-Client-Platform": "android_store"}
        c, _, _, email, _ = await tenant()
        n = client()
        r = await n.post("/api/auth/login", json={"identifier": email, "password": PW}, headers=NAT)
        assert r.status_code == 200, r.text
        old_rt = r.json()["tokens"]["refresh_token"]
        old_at = r.json()["tokens"]["access_token"]
        bearer = client()
        r = await bearer.post("/api/auth/change-password", json={"current_password": PW, "new_password": "R2New@2026x"},
                              headers={**NAT, "Authorization": f"Bearer {old_at}"})
        assert r.status_code == 200, r.text
        toks = r.json().get("tokens") or {}
        assert toks.get("access_token") and toks.get("refresh_token"), r.json()
        fresh = client()
        assert (await fresh.get("/api/auth/me", headers={"Authorization": f"Bearer {toks['access_token']}"})).status_code == 200
        fresh2 = client()
        assert (await fresh2.get("/api/auth/me", headers={"Authorization": f"Bearer {old_at}"})).status_code == 401
        fresh3 = client()
        r = await fresh3.post("/api/auth/refresh", json={"refresh_token": toks["refresh_token"]}, headers=NAT)
        assert r.status_code == 200 and r.json()["tokens"]["access_token"], r.text
        fresh4 = client()
        r = await fresh4.post("/api/auth/refresh", json={"refresh_token": old_rt}, headers=NAT)
        assert r.status_code == 401, r.text
        # web: no tokens in body, cookies set
        r = await c.post("/api/auth/change-password", json={"current_password": PW, "new_password": "R2Web@2026y"})
        # c's session was invalidated by previous change (token_version bumped) -> 401 expected; log in again on web
        if r.status_code == 401:
            w = client()
            r = await w.post("/api/auth/login", json={"identifier": email, "password": "R2New@2026x"})
            assert r.status_code == 200
            r = await w.post("/api/auth/change-password", json={"current_password": "R2New@2026x", "new_password": "R2Web@2026y"})
            await w.aclose()
        assert r.status_code == 200, r.text
        assert "tokens" not in r.json()
        sc = r.headers.get_list("set-cookie")
        assert any(s.startswith("access_token=") for s in sc) and any(s.startswith("refresh_token=") for s in sc)
        for x in (c, n, bearer, fresh, fresh2, fresh3, fresh4):
            await x.aclose()
    run(go())


# ---------------- Subscription purchase snapshot ----------------
class FakeHttp:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **k):
        return SimpleNamespace(status_code=200, json=lambda: {"id": f"order_{uuid.uuid4().hex[:10]}"})


def test_subscription_purchase_snapshot(monkeypatch):
    monkeypatch.setattr(billing, "httpx", SimpleNamespace(AsyncClient=FakeHttp))

    async def no_rzp(*a, **k):
        raise AssertionError("live Razorpay must not be called")
    monkeypatch.setattr(billing, "razorpay_request", no_rzp)

    async def go():
        await db.settings.update_one({"id": "platform"}, {"$set": {"id": "platform", "razorpay_key_id": "rzp_test_x", "razorpay_key_secret": "s",
                                                                   "pricing_plans": [{"id": "quarterly", "price": 3000}]}}, upsert=True)
        c, org_id, _, _, _ = await tenant()
        r = await c.post("/api/subscription/create-order", json={"plan_id": "quarterly"})
        assert r.status_code == 200, r.text
        oid = r.json()["order_id"]
        rec = await db.subscription_payments.find_one({"order_id": oid})
        p = rec["purchase"]
        assert p["plan_id"] == "quarterly" and p["months"] == 3 and p["amount"] == 3000 and p["plan_name"], p
        await db.settings.update_one({"id": "platform"}, {"$set": {"pricing_plans": [{"id": "quarterly", "price": 9999}]}})
        await billing_sync.apply_payment(org_id, "pay_snap1", purchase=await billing_sync.resolve_purchase(rec), order_id=oid)
        org = await db.organisations.find_one({"id": org_id})
        assert org["subscription"]["amount"] == 3000 and org["subscription"]["plan_months"] == 3, org["subscription"]
        assert (await db.subscription_payments.find_one({"order_id": oid}))["status"] == "paid"
        # legacy without purchase -> recorded amount
        c2, org2, _, _, _ = await tenant()
        legacy = {"id": "lg1", "organisation_id": org2, "order_id": "order_legacy", "amount": 2500, "plan_id": "quarterly", "status": "created"}
        await db.subscription_payments.insert_one(dict(legacy))
        await billing_sync.apply_payment(org2, "pay_legacy", purchase=await billing_sync.resolve_purchase(legacy), order_id="order_legacy")
        s2 = (await db.organisations.find_one({"id": org2}))["subscription"]
        assert s2["amount"] == 2500 and s2["plan_months"] == 3, s2
        # autodebit uses subscriptions.purchase
        c3, org3, _, _, _ = await tenant()
        local = {"id": "s1", "organisation_id": org3, "razorpay_subscription_id": "sub_snap",
                 "purchase": {"plan_id": "yearly", "plan_name": "Yearly", "months": 12, "amount": 11111}}
        await db.subscriptions.insert_one(dict(local))
        await billing_sync.record_autodebit_payment(local, "pay_auto1", None, "autodebit")
        s3 = (await db.organisations.find_one({"id": org3}))["subscription"]
        assert s3["amount"] == 11111 and s3["plan_months"] == 12, s3
        row = await db.subscription_payments.find_one({"payment_id": "pay_auto1"})
        assert row["purchase"]["amount"] == 11111 and row["amount"] == 11111
        # replay is a no-op
        assert await billing_sync.apply_payment(org_id, "pay_snap1", purchase=p, order_id=oid) is None
        for x in (c, c2, c3):
            await x.aclose()
    run(go())


def test_health():
    async def go():
        c = client()
        r = await c.get("/api/health")
        assert r.status_code == 200 and r.json() == {"status": "ok", "db": "ok", "transactions": True}
        await c.aclose()
    run(go())


def test_payments_and_expenses_list_pagination_stable():
    async def go():
        b = await bulk_setup()
        c = b["c"]
        res = {}
        for path, n, lim in (("/api/payments", len(b["pays"]), 200), ("/api/expenses", len(b["exps"]), 100)):
            seen, page = [], 1
            while True:
                d = (await c.get(path, params={"page": page, "limit": lim})).json()
                if not d["items"]:
                    break
                seen += [x["id"] for x in d["items"]]
                page += 1
            res[path] = (len(seen), len(set(seen)), n)
        assert all(a == u == n for a, u, n in res.values()), res
    run(go())
