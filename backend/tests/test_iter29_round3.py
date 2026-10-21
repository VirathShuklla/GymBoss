"""Iter29 (Round 3): monthly finance PDF, outlet filtering on reports, report pagination, dashboard active count via
member_status (future freezes), hardened uploads (dimension/megapixel/bomb/corrupt/PDF structure, photo re-encode),
idempotency status endpoint + tenant isolation.
In-process against ISOLATED db gymboss_r3_tests. Run: pytest -n 0 tests/test_iter29_round3.py"""
import paths  # noqa: F401
import os

os.environ["DB_NAME"] = "gymboss_r3_tests"

import io  # noqa: E402
import uuid  # noqa: E402
import zlib  # noqa: E402
import struct  # noqa: E402
import random  # noqa: E402
import asyncio  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
import httpx  # noqa: E402
from PIL import Image  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

import deps  # noqa: E402
import server  # noqa: E402
import members  # noqa: E402
from receipt_pdf import _inr  # noqa: E402

db = deps.db
assert db.name == "gymboss_r3_tests"
LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)
PW = "R3Test@2026"


def run(coro):
    return LOOP.run_until_complete(coro)


@pytest.fixture(scope="module", autouse=True)
def isolated_db():
    run(deps.client.drop_database("gymboss_r3_tests"))
    run(server.ensure_indexes())
    yield
    run(deps.client.drop_database("gymboss_r3_tests"))


def phone():
    return "9" + "".join(random.choice("0123456789") for _ in range(9))


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app, raise_app_exceptions=False), base_url="https://test", timeout=300)


async def tenant():
    c = client()
    email = f"r3_{uuid.uuid4().hex[:10]}@example.com"
    r = await c.post("/api/auth/register", json={"full_name": "R3 Owner", "email": email, "phone": phone(), "password": PW,
                                                 "gym_name": "R3 Gym", "outlet_name": "Main"})
    assert r.status_code == 200, r.text
    org_id = r.json()["organisation"]["id"]
    r2 = await c.post("/api/plans", json={"name": "Monthly", "type": "membership", "duration_type": "months", "duration": 1, "price": 1000})
    assert r2.status_code == 200, r2.text
    return c, org_id, r2.json()["id"]


async def two_outlets(c, org_id):
    a = (await db.outlets.find_one({"organisation_id": org_id}))["id"]
    r = await c.post("/api/outlets", json={"name": "Second Branch"})
    assert r.status_code == 200, r.text
    return a, r.json()["id"]


# ---------------- Monthly PDF ----------------
def pdf_text(b: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)


def test_monthly_pdf_totals_outlets_and_access():
    async def go():
        c, org_id, _ = await tenant()
        A, B = await two_outlets(c, org_id)
        base = {"organisation_id": org_id, "member_id": "x", "type": "membership", "method": "Cash", "status": "active"}
        await db.payments.insert_many([
            # IST boundary: created 2026-08-31 18:45Z == 2026-09-01 00:15 IST -> September
            {**base, "id": "s1", "outlet_id": A, "amount": 1234.5, "payment_date": "2026-09-01", "created_at": datetime(2026, 8, 31, 18, 45, tzinfo=timezone.utc)},
            {**base, "id": "s2", "outlet_id": B, "amount": 2000, "payment_date": "2026-09-30", "created_at": datetime(2026, 9, 30, 18, 20, tzinfo=timezone.utc)},
            # excluded: Oct 1 IST / Aug 31 IST
            {**base, "id": "s3", "outlet_id": A, "amount": 7777, "payment_date": "2026-10-01", "created_at": datetime(2026, 9, 30, 18, 45, tzinfo=timezone.utc)},
            {**base, "id": "s4", "outlet_id": A, "amount": 8888, "payment_date": "2026-08-31", "created_at": datetime(2026, 8, 31, 18, 15, tzinfo=timezone.utc)},
            # reversal pair in September (original + negative entry)
            {**base, "id": "s5", "outlet_id": A, "amount": 500, "payment_date": "2026-09-10", "status": "reversed", "created_at": datetime(2026, 9, 10, tzinfo=timezone.utc)},
            {**base, "id": "s6", "outlet_id": A, "amount": -500, "type": "reversal", "reversal_of": "s5", "payment_date": "2026-09-20", "created_at": datetime(2026, 9, 20, tzinfo=timezone.utc)},
            {**base, "id": "s7", "outlet_id": A, "amount": 300, "method": "UPI", "payment_date": "2026-09-15", "created_at": datetime(2026, 9, 15, tzinfo=timezone.utc)},
        ])
        await db.expenses.insert_many([
            {"id": "x1", "organisation_id": org_id, "outlet_id": A, "name": "TEST_Rent", "category": "Rent", "amount": 900, "date": "2026-09-05"},
            {"id": "x2", "organisation_id": org_id, "outlet_id": B, "name": "TEST_Power", "category": "Power", "amount": 250.25, "date": "2026-09-30"},
            {"id": "x3", "organisation_id": org_id, "outlet_id": A, "name": "TEST_Oct", "category": "Rent", "amount": 5555, "date": "2026-10-01"},
        ])
        await db.members.insert_many([
            {"id": "dm1", "organisation_id": org_id, "outlet_id": A, "full_name": "TEST_Due1", "member_code": "DM1", "deleted_at": None, "due_amount": 400},
            {"id": "dm2", "organisation_id": org_id, "outlet_id": B, "full_name": "TEST_Due2", "member_code": "DM2", "deleted_at": None, "due_amount": 150},
            {"id": "dm3", "organisation_id": org_id, "outlet_id": B, "full_name": "TEST_Del", "member_code": "DM3", "deleted_at": deps.now_utc(), "due_amount": 999},
        ])
        cases = {
            None: dict(rev=1234.5 + 2000 + 500 - 500 + 300, exp=900 + 250.25, out=550),
            A: dict(rev=1234.5 + 500 - 500 + 300, exp=900, out=400),
            B: dict(rev=2000, exp=250.25, out=150),
        }
        for outlet, want in cases.items():
            params = {"month": "2026-09", **({"outlet_id": outlet} if outlet else {})}
            r = await c.get("/api/reports/monthly.pdf", params=params)
            assert r.status_code == 200, r.text
            assert r.headers["content-type"] == "application/pdf"
            assert r.content[:5] == b"%PDF-"
            txt = pdf_text(r.content)
            assert "September 2026" in txt, txt[:400]
            net = round(want["rev"] - want["exp"], 2)
            for label, v in (("collections", want["rev"]), ("expenses", want["exp"]), ("outstanding", want["out"])):
                assert _inr(v) in txt, (outlet, label, _inr(v), txt[:800])
            assert (_inr(net) if net >= 0 else f"- {_inr(abs(net))}") in txt or _inr(net) in txt, (outlet, net, txt[:800])
            assert ("Second Branch" in txt) == (outlet == B)
            # cross-check with JSON summary
            s = (await c.get("/api/finance/summary", params={"range": "custom", "date_from": "2026-09-01", "date_to": "2026-09-30",
                                                             **({"outlet_id": outlet} if outlet else {})})).json()
            assert s["revenue"] == round(want["rev"], 2) and s["expenses"] == round(want["exp"], 2) and s["outstanding"] == want["out"], s
        # invalid month
        for bad in ("2026-13", "abc", "2026-9", "2026-09-01x"):
            assert (await c.get("/api/reports/monthly.pdf", params={"month": bad})).status_code == 422, bad
        # unknown / foreign outlet
        assert (await c.get("/api/reports/monthly.pdf", params={"month": "2026-09", "outlet_id": "nope"})).status_code == 404
        c2, org2, _ = await tenant()
        foreign = (await db.outlets.find_one({"organisation_id": org2}))["id"]
        assert (await c.get("/api/reports/monthly.pdf", params={"month": "2026-09", "outlet_id": foreign})).status_code == 404
        # default month works
        assert (await c.get("/api/reports/monthly.pdf")).status_code == 200
        # view-only staff without finance -> 403
        se = f"r3s_{uuid.uuid4().hex[:8]}@example.com"
        r = await c.post("/api/staff", json={"name": "TEST View", "role": "receptionist", "email": se, "phone": phone(), "password": PW, "permission": "view"})
        assert r.status_code == 200, r.text
        s = client()
        assert (await s.post("/api/auth/login", json={"identifier": se, "password": PW})).status_code == 200
        r = await s.get("/api/reports/monthly.pdf", params={"month": "2026-09"})
        assert r.status_code == 403, r.status_code
        # unauthenticated
        assert (await client().get("/api/reports/monthly.pdf")).status_code == 401
        for x in (c, c2, s):
            await x.aclose()
    run(go())


# ---------------- Outlet filtering on reports + pagination ----------------
def test_reports_outlet_filtering_and_pagination():
    async def go():
        c, org_id, _ = await tenant()
        A, B = await two_outlets(c, org_id)
        today = deps.today_ist()
        cur = today.replace(day=1).isoformat()
        mems = []
        for i in range(260):
            o = A if i % 2 == 0 else B
            mems.append({"id": f"pm{i:04d}", "organisation_id": org_id, "outlet_id": o, "full_name": f"TEST_P{i}", "member_code": f"P{i:04d}",
                         "phone": f"91000{i:05d}", "deleted_at": None, "due_amount": 10 + (i % 7), "joining_date": cur,
                         "membership_expiry": (today + timedelta(days=1 + i % 20)).isoformat()})
        await db.members.insert_many(mems)
        await db.payments.insert_many([
            {"id": "op1", "organisation_id": org_id, "outlet_id": A, "member_id": "x", "amount": 111, "payment_date": today.isoformat(), "type": "due", "method": "Cash"},
            {"id": "op2", "organisation_id": org_id, "outlet_id": B, "member_id": "x", "amount": 222, "payment_date": today.isoformat(), "type": "due", "method": "Cash"},
        ])
        await db.expenses.insert_many([
            {"id": "oe1", "organisation_id": org_id, "outlet_id": A, "name": "TEST_e", "category": "Rent", "amount": 11, "date": today.isoformat()},
            {"id": "oe2", "organisation_id": org_id, "outlet_id": B, "name": "TEST_e", "category": "Rent", "amount": 22, "date": today.isoformat()},
        ])
        await db.enquiries.insert_many([
            {"id": "q1", "organisation_id": org_id, "outlet_id": A, "name": "TEST_q", "status": "Converted", "source": "Walk-In"},
            {"id": "q2", "organisation_id": org_id, "outlet_id": B, "name": "TEST_q", "status": "New", "source": "Instagram"},
            {"id": "q3", "organisation_id": org_id, "outlet_id": B, "name": "TEST_q", "status": "New", "source": "Instagram"},
        ])
        exp = {None: mems, A: [m for m in mems if m["outlet_id"] == A], B: [m for m in mems if m["outlet_id"] == B]}
        rev = {None: (333, 33), A: (111, 11), B: (222, 22)}
        enq = {None: (3, 1), A: (1, 1), B: (2, 0)}
        for o, M in exp.items():
            p = {"outlet_id": o} if o else {}
            t = (await c.get("/api/reports/revenue-trend", params={"months": 3, **p})).json()["points"][-1]
            assert (t["revenue"], t["expenses"]) == rev[o], (o, t)
            g = (await c.get("/api/reports/member-growth", params={"months": 2, **p})).json()["points"][-1]
            assert g["joined"] == len(M) and g["total"] == len(M), (o, g)
            e = (await c.get("/api/reports/enquiry-conversion", params=p)).json()
            assert (e["total"], e["converted"]) == enq[o], (o, e)
            for path, extra in (("/api/reports/outstanding-dues", {}), ("/api/reports/membership-expiry", {"days": 30})):
                ids, page = [], 1
                while True:
                    d = (await c.get(path, params={"page": page, "limit": 100, **extra, **p})).json()
                    assert d["count"] == len(M), (path, o, d["count"])
                    if path.endswith("dues"):
                        assert d["total"] == sum(m["due_amount"] for m in M)
                    if not d["items"]:
                        break
                    ids += [i["id"] for i in d["items"]]
                    page += 1
                assert len(ids) == len(set(ids)) == len(M), (path, o, len(ids), len(set(ids)))
                assert set(ids) == {m["id"] for m in M}
        await c.aclose()
    run(go())


# ---------------- Dashboard active count ----------------
def test_dashboard_active_members_respects_future_freeze():
    async def go():
        c, org_id, _ = await tenant()
        today = deps.today_ist()
        o = (await db.outlets.find_one({"organisation_id": org_id}))["id"]
        exp = (today + timedelta(days=60)).isoformat()
        nw, nw2 = (today + timedelta(days=7)).isoformat(), (today + timedelta(days=14)).isoformat()
        tf, tu = today.isoformat(), (today + timedelta(days=5)).isoformat()
        docs = [
            {"id": "fz_future", "frozen_from": nw, "frozen_until": nw2, "freeze_history": [{"id": "h1", "freeze_from": nw, "freeze_until": nw2, "days": 7}]},
            {"id": "fz_today", "frozen_from": tf, "frozen_until": tu, "freeze_history": [{"id": "h2", "freeze_from": tf, "freeze_until": tu, "days": 5}]},
            {"id": "plain_active"},
            {"id": "expired", "membership_expiry": (today - timedelta(days=1)).isoformat()},
        ]
        for d in docs:
            await db.members.insert_one({"organisation_id": org_id, "outlet_id": o, "full_name": f"TEST_{d['id']}", "member_code": d["id"],
                                         "deleted_at": None, "due_amount": 0, "membership_expiry": exp, **d})
        expected = sum(1 for m in [await db.members.find_one({"id": d["id"]}) for d in docs] if deps.member_status(m, today) in ("active", "expiring_soon"))
        assert deps.member_status(await db.members.find_one({"id": "fz_future"}), today) == "active"
        assert deps.member_status(await db.members.find_one({"id": "fz_today"}), today) == "frozen"
        d = (await c.get("/api/dashboard/summary")).json()
        assert d["active_members"] == expected == 2, (d["active_members"], expected)
        assert d["total_members"] == 4
        # via real freeze API: schedule a future freeze on a new member -> still active
        await db.members.insert_one({"id": "api_fz", "organisation_id": org_id, "outlet_id": o, "full_name": "TEST_api_fz", "member_code": "AF",
                                     "deleted_at": None, "due_amount": 0, "membership_expiry": exp, "freeze_history": []})
        r = await c.post("/api/members/api_fz/freeze", json={"freeze_from": nw, "freeze_until": nw2, "reason": "travel"})
        assert r.status_code == 200, r.text
        d = (await c.get("/api/dashboard/summary")).json()
        assert d["active_members"] == 3, d["active_members"]
        await c.aclose()
    run(go())


# ---------------- Uploads ----------------
def img_bytes(w, h, fmt="PNG", color=(200, 30, 30), **kw):
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, format=fmt, **kw)
    return b.getvalue()


def png_bomb(w=100_000, h=100_000) -> bytes:
    """Valid PNG signature + IHDR claiming huge dimensions, tiny compressed IDAT."""
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00" * 1024 * 64, 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def reportlab_pdf() -> bytes:
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    cv = canvas.Canvas(b)
    cv.drawString(100, 750, "TEST attachment")
    cv.save()
    return b.getvalue()


def encrypted_pdf() -> bytes:
    w = PdfWriter()
    w.append(PdfReader(io.BytesIO(reportlab_pdf())))
    w.encrypt("secret")
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


def empty_pdf() -> bytes:
    b = io.BytesIO()
    PdfWriter().write(b)
    return b.getvalue()


def test_upload_validation_and_photo_processing(monkeypatch):
    store = {}

    async def put_object(path, data, ct):
        store[path] = data
        return {"path": path}

    async def get_object(path):
        return store[path], "application/octet-stream"
    monkeypatch.setattr(members, "put_object", put_object)
    monkeypatch.setattr(members, "get_object", get_object)

    async def up(c, name, data, kind="attachment"):
        return await c.post("/api/uploads", files={"file": (name, data, "application/octet-stream")}, data={"kind": kind})

    async def stored(c, r):
        assert r.status_code == 200, r.text[:300]
        g = await c.get(f"/api/files/{r.json()['id']}")
        assert g.status_code == 200
        return g.content

    async def go():
        c, org_id, _ = await tenant()
        jpg = img_bytes(400, 300, "JPEG")
        big = img_bytes(6000, 6000)
        assert len(big) <= 5 * 1024 * 1024, len(big)
        bad = [
            ("prefix.jpg", b"\xff\xd8\xff", "attachment"),
            ("text.pdf", b"%PDF-hello this is text", "attachment"),
            ("trunc.jpg", jpg[: len(jpg) // 2], "attachment"),
            ("trunc_photo.jpg", jpg[: len(jpg) // 2], "photo"),
            ("corrupt.jpg", jpg[:200] + os.urandom(800), "attachment"),
            ("wide.png", img_bytes(7000, 10), "attachment"),
            ("tall.png", img_bytes(10, 7000), "photo"),
            ("7000x6000.png", img_bytes(7000, 6000), "attachment"),
            ("bomb.png", png_bomb(), "attachment"),
            ("bomb2.png", png_bomb(6000, 6001), "photo"),
            ("enc.pdf", encrypted_pdf(), "attachment"),
            ("empty.pdf", empty_pdf(), "attachment"),
        ]
        fails = []
        for name, data, kind in bad:
            r = await up(c, name, data, kind)
            if r.status_code != 422:
                fails.append((name, r.status_code, r.text[:150]))
        assert not fails, fails
        # 6000x6000 = 36 MP within 5 MB accepted (attachment byte-identical; photo downscaled)
        assert await stored(c, await up(c, "36mp.png", big)) == big
        ph = Image.open(io.BytesIO(await stored(c, await up(c, "36mp_photo.png", big, "photo"))))
        assert max(ph.size) == 1024
        # valid PDF accepted, byte-identical
        pdf = reportlab_pdf()
        assert await stored(c, await up(c, "ok.pdf", pdf)) == pdf
        # EXIF-rotated photo -> 1024 long edge, portrait, no EXIF
        ex = Image.Exif()
        ex[0x0112] = 6
        ex[0x010F] = "TEST_CameraMaker"
        src = io.BytesIO()
        Image.new("RGB", (3000, 2000), (10, 120, 200)).save(src, format="JPEG", exif=ex.tobytes(), quality=80)
        src = src.getvalue()
        assert len(src) < 5 * 1024 * 1024
        out = await stored(c, await up(c, "rot.jpg", src, "photo"))
        im = Image.open(io.BytesIO(out))
        assert im.size == (683, 1024) or (max(im.size) == 1024 and im.size[1] > im.size[0]), im.size
        assert len(im.getexif()) == 0 and b"Exif" not in out[:2000] and b"TEST_CameraMaker" not in out, dict(im.getexif())
        # small photo not upscaled
        im2 = Image.open(io.BytesIO(await stored(c, await up(c, "small.jpg", img_bytes(300, 200, "JPEG"), "photo"))))
        assert im2.size == (300, 200)
        # attachment image stored byte-identical (EXIF kept, not rotated)
        assert await stored(c, await up(c, "att.jpg", src)) == src
        # legacy record with raw (non-validated) bytes still served
        store["legacy/old.jpg"] = b"\xff\xd8\xff\xe0" + b"\x00" * 50
        await db.files.insert_one({"id": "legacy-r3", "organisation_id": org_id, "storage_path": "legacy/old.jpg", "original_filename": "old.jpg",
                                   "content_type": "image/jpeg", "is_deleted": False, "created_at": deps.now_utc()})
        g = await c.get("/api/files/legacy-r3")
        assert g.status_code == 200 and g.headers["content-type"] == "image/jpeg" and g.content == store["legacy/old.jpg"]
        await c.aclose()
    run(go())


# ---------------- Idempotency status ----------------
def test_idempotency_status_and_isolation():
    async def go():
        c, org_id, plan_id = await tenant()
        r = await c.post("/api/members", json={"full_name": "TEST_R3 Idem", "phone": phone(), "plan_id": plan_id, "amount_paid": 0})
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        key = "r3-" + uuid.uuid4().hex
        assert (await c.get(f"/api/idempotency/{key}")).json() == {"status": "unknown"}
        r = await c.post("/api/payments", json={"member_id": mid, "amount": 50}, headers={"Idempotency-Key": key})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        d = (await c.get(f"/api/idempotency/{key}")).json()
        assert d["status"] == "completed" and d["ref"] == pid and d["scope"] == "payment.record", d
        # retry same key -> same payment, no duplicate
        r2 = await c.post("/api/payments", json={"member_id": mid, "amount": 50}, headers={"Idempotency-Key": key})
        assert r2.json()["id"] == pid
        assert await db.payments.count_documents({"member_id": mid, "amount": 50}) == 1
        # stored record has no member details
        doc = await db.idempotency_keys.find_one({"key": key}, {"_id": 0})
        assert "TEST_R3" not in str(doc) and mid not in str({k: v for k, v in doc.items() if k != "ref"}), doc
        c2, _, _ = await tenant()
        assert (await c2.get(f"/api/idempotency/{key}")).json() == {"status": "unknown"}
        assert (await client().get(f"/api/idempotency/{key}")).status_code == 401
        await c.aclose()
        await c2.aclose()
    run(go())
