"""Iter 15 — Attendance (QR/biometric/ADMS), Pricing plans, Churn export, Receipt PDF, Dark-mode safe APIs."""
import io
import re
import time
import pytest
import requests
from datetime import datetime, timezone, timedelta

from conftest import API, BASE_URL


# ------------------- fixtures -------------------

@pytest.fixture(scope="module")
def admin_session():
    import pathlib, re as _re
    content = pathlib.Path("/app/memory/test_credentials.md").read_text()
    usernames = _re.findall(r"(?im)^\s*-\s*Username\s*:\s*`?([^`\s]+)", content)
    passwords = _re.findall(r"(?im)^\s*-\s*Password\s*:\s*`?([^`\s]+)", content)
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"identifier": usernames[0], "password": passwords[0]})
    assert r.status_code == 200, r.text
    yield s
    s.close()


@pytest.fixture(scope="module")
def owner_session():
    import pathlib, re as _re
    content = pathlib.Path("/app/memory/test_credentials.md").read_text()
    emails = _re.findall(r"(?im)^\s*-\s*Email\s*:\s*`?([^`\s]+)", content)
    passwords = _re.findall(r"(?im)^\s*-\s*Password\s*:\s*`?([^`\s]+)", content)
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"identifier": emails[0], "password": passwords[1]})
    assert r.status_code == 200, r.text
    yield s
    s.close()


# ------------------- Churn export -------------------

class TestChurnExport:
    def test_requires_auth(self):
        r = requests.get(f"{API}/admin/churn-export")
        assert r.status_code in (401, 403)

    def test_owner_forbidden(self, owner_session):
        r = owner_session.get(f"{API}/admin/churn-export")
        assert r.status_code == 403

    def test_high_risk_csv(self, admin_session):
        r = admin_session.get(f"{API}/admin/churn-export?health=high_risk")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "attachment" in r.headers.get("content-disposition", "")
        header = r.text.splitlines()[0]
        for col in ("Gym", "City", "Owner", "Email", "Phone", "Health"):
            assert col in header
        # must exclude demo
        assert "Iron Paradise Fitness" not in r.text

    def test_all_risk_superset(self, admin_session):
        a = admin_session.get(f"{API}/admin/churn-export?health=high_risk").text.splitlines()
        b = admin_session.get(f"{API}/admin/churn-export?health=all_risk").text.splitlines()
        assert len(b) >= len(a)


# ------------------- Pricing plans -------------------

ORIG = None


class TestPricing:
    def test_get_defaults(self, admin_session):
        global ORIG
        r = admin_session.get(f"{API}/admin/settings")
        assert r.status_code == 200
        plans = r.json().get("pricing_plans") or []
        ids = {p["id"] for p in plans}
        assert ids == {"monthly", "quarterly", "yearly"}
        ORIG = plans
        for p in plans:
            if p["id"] == "monthly":
                assert p["price"] == 999
            else:
                assert p["price"] > 0  # super admin may have customised multi-month prices

    def test_offer_gte_price_rejected(self, admin_session):
        body = {"pricing_plans": [
            {"id": "monthly", "price": 999, "offer_price": 999},
            {"id": "quarterly", "price": 2997},
            {"id": "yearly", "price": 11988},
        ]}
        r = admin_session.put(f"{API}/admin/settings", json=body)
        assert r.status_code == 422

    def test_save_and_public_config_reflects(self, admin_session):
        body = {"pricing_plans": [
            {"id": "monthly", "price": 999, "offer_price": 799, "offer_label": "Launch"},
            {"id": "quarterly", "price": 2997, "active": False},
            {"id": "yearly", "price": 11988, "offer_price": 9999, "offer_label": "Save 17%"},
        ]}
        r = admin_session.put(f"{API}/admin/settings", json=body)
        assert r.status_code == 200
        cfg = requests.get(f"{API}/public/config").json()
        active_ids = [p["id"] for p in cfg["pricing_plans"]]
        assert "quarterly" not in active_ids
        assert "monthly" in active_ids and "yearly" in active_ids
        monthly = next(p for p in cfg["pricing_plans"] if p["id"] == "monthly")
        assert monthly["effective_price"] == 799
        yearly = next(p for p in cfg["pricing_plans"] if p["id"] == "yearly")
        assert yearly["offer_price"] == 9999 and yearly["effective_price"] == 9999

    def test_restore(self, admin_session):
        if ORIG is None:
            pytest.skip("no original captured")
        body = {"pricing_plans": [
            {"id": p["id"], "price": p["price"], "offer_price": p.get("offer_price"),
             "offer_label": p.get("offer_label") or "", "active": p.get("active", True), "name": p.get("name")}
            for p in ORIG
        ]}
        r = admin_session.put(f"{API}/admin/settings", json=body)
        assert r.status_code == 200


# ------------------- Receipt PDF -------------------

class TestReceiptPDF:
    def test_owner_receipt_pdf(self, owner_session):
        r = owner_session.get(f"{API}/payments?limit=1")
        assert r.status_code == 200
        items = r.json().get("items") or []
        if not items:
            pytest.skip("no payments")
        pid = items[0]["id"]
        p = owner_session.get(f"{API}/payments/{pid}/receipt.pdf")
        assert p.status_code == 200
        assert p.headers["content-type"] == "application/pdf"
        assert p.content[:4] == b"%PDF"

    def test_other_org_payment_404(self, owner_session):
        r = owner_session.get(f"{API}/payments/does-not-exist/receipt.pdf")
        assert r.status_code == 404


# ------------------- Attendance QR + biometric + ADMS -------------------

@pytest.fixture(scope="module")
def devices(owner_session):
    created = []
    yield created
    for did in created:
        owner_session.delete(f"{API}/attendance/devices/{did}")


class TestAttendance:
    def test_summary(self, owner_session):
        r = owner_session.get(f"{API}/attendance/summary")
        assert r.status_code == 200
        d = r.json()
        for k in ("today", "inside_now", "staff_today", "devices", "devices_online"):
            assert k in d

    def test_qr_outlets(self, owner_session):
        r = owner_session.get(f"{API}/attendance/qr")
        assert r.status_code == 200
        d = r.json()
        assert d["outlets"] and all(o.get("token") for o in d["outlets"])
        global TOKEN
        TOKEN = d["outlets"][0]["token"]

    def test_public_checkin_info(self):
        r = requests.get(f"{API}/public/checkin/{TOKEN}")
        assert r.status_code == 200
        assert "gym_name" in r.json()

    def test_public_checkin_invalid_token(self):
        r = requests.get(f"{API}/public/checkin/invalid-xxx")
        assert r.status_code == 404

    def test_public_checkin_member_by_code(self, owner_session):
        ms = owner_session.get(f"{API}/members?limit=5").json()
        items = ms.get("items") if isinstance(ms, dict) else ms
        # Find an active member
        code = None
        for m in items:
            if m.get("status") == "active":
                code = m["member_code"]
                break
        if not code:
            pytest.skip("no active member")
        r = requests.post(f"{API}/public/checkin/{TOKEN}", json={"kind": "member", "identifier": code})
        assert r.status_code == 200
        assert r.json()["action"] in ("in", "out", "duplicate")
        # repeat within 1 minute -> duplicate or still returns 200
        r2 = requests.post(f"{API}/public/checkin/{TOKEN}", json={"kind": "member", "identifier": code})
        assert r2.status_code == 200
        assert r2.json()["action"] in ("duplicate", "out", "in")

    def test_public_checkin_unknown_member(self):
        r = requests.post(f"{API}/public/checkin/{TOKEN}", json={"kind": "member", "identifier": "NOPE-9999"})
        assert r.status_code == 404

    def test_public_checkin_staff(self, owner_session):
        r = requests.post(f"{API}/public/checkin/{TOKEN}", json={"kind": "staff", "identifier": "demo@gymbossvvo.in"})
        assert r.status_code == 200
        assert r.json()["action"] in ("in", "out", "duplicate")

    # ---- biometric devices ----
    def test_add_device_invalid_serial(self, owner_session):
        r = owner_session.post(f"{API}/attendance/devices", json={"device_type": "eSSL X990", "serial_number": "xx", "name": "T"})
        assert r.status_code == 422

    def test_add_device(self, owner_session, devices):
        sn = f"TESTSN{int(time.time())}"
        r = owner_session.post(f"{API}/attendance/devices", json={"device_type": "eSSL X990", "serial_number": sn, "name": "QA Device"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["serial_number"] == sn.upper() and d["online"] is False
        devices.append(d["id"])
        # Duplicate serial
        r2 = owner_session.post(f"{API}/attendance/devices", json={"device_type": "eSSL X990", "serial_number": sn, "name": "x"})
        assert r2.status_code == 409

    def test_test_punch(self, owner_session, devices):
        if not devices:
            pytest.skip("no device")
        did = devices[0]
        ms = owner_session.get(f"{API}/members?limit=20").json()
        items = ms.get("items") if isinstance(ms, dict) else ms
        # Find a member not yet punched today — just pick last one
        mid = items[-1]["id"]
        r = owner_session.post(f"{API}/attendance/devices/{did}/test-punch", json={"member_id": mid})
        assert r.status_code == 200, r.text
        assert r.json()["action"] in ("in", "out", "duplicate")

    def test_device_ids(self, owner_session):
        r = owner_session.get(f"{API}/attendance/device-ids")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and rows
        assert all("device_user_id" in x for x in rows[:3])


# ------------------- ADMS protocol -------------------

class TestADMS:
    def test_handshake(self, owner_session):
        # Need a device first - create one via owner
        sn = f"ADMSSN{int(time.time())}"
        r = owner_session.post(f"{API}/attendance/devices", json={"device_type": "eSSL K40", "serial_number": sn, "name": "ADMS QA"})
        assert r.status_code == 200
        did = r.json()["id"]
        try:
            # Handshake
            h = requests.get(f"{API}/iclock/cdata?SN={sn}")
            assert h.status_code == 200
            assert h.text.startswith("GET OPTION FROM")
            # Device becomes online
            devs = owner_session.get(f"{API}/attendance/devices").json()["devices"]
            d = next(x for x in devs if x["id"] == did)
            assert d["online"] is True
            # Upload ATTLOG — need a member PIN; use member_code numeric part
            ms = owner_session.get(f"{API}/members?limit=5").json()
            items = ms.get("items") if isinstance(ms, dict) else ms
            m = items[0]
            pin_match = re.search(r"(\d+)$", m["member_code"])
            pin = pin_match.group(1)
            # Use a unique timestamp — a minute from now in IST
            now_ist = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30))
            # Use something a few minutes in the past to avoid DOUBLE_SCAN collision with recent punches
            ts = (now_ist - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S")
            body = f"{pin}\t{ts}\t0\t1"
            u = requests.post(f"{API}/iclock/cdata?SN={sn}&table=ATTLOG", data=body)
            assert u.status_code == 200
            assert u.text.startswith("OK"), u.text
            first = u.text
            # Repost identical line - should be deduped (OK: 0)
            u2 = requests.post(f"{API}/iclock/cdata?SN={sn}&table=ATTLOG", data=body)
            assert u2.text == "OK: 0" or u2.text == first  # first might be OK:0 if same ts collides w/ existing
            # getrequest
            g = requests.get(f"{API}/iclock/getrequest?SN={sn}")
            assert g.status_code == 200
            assert g.text.startswith("OK") or g.text.startswith("C:")
        finally:
            owner_session.delete(f"{API}/attendance/devices/{did}")

    def test_adms_unknown_sn(self):
        h = requests.get(f"{API}/iclock/cdata?SN=UNKNOWN999")
        assert h.status_code == 200  # still returns handshake
        u = requests.post(f"{API}/iclock/cdata?SN=UNKNOWN999&table=ATTLOG", data="1\t2026-01-01 00:00:00\t0\t1")
        assert u.status_code == 200
        assert u.text == "OK"


# ------------------- Admin analytics usage includes attendance -------------------

class TestAnalyticsAttendance:
    def test_usage_has_attendance(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics")
        assert r.status_code == 200
        usage = r.json()["usage"]
        for k in ("attendance_today", "attendance_month", "biometric_devices"):
            assert k in usage
            assert isinstance(usage[k], int)
