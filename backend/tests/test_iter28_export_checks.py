# Iter28: export date-range validation + CSV formula-injection escaping (public URL)
import csv
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    return s


def test_export_invalid_range_422(client):
    r = client.get(f"{BASE_URL}/api/export/payments", params={"date_from": "2026-09-10", "date_to": "2026-09-01"})
    assert r.status_code == 422
    assert r.json()["detail"] == "End date must be on or after start date"


def test_export_valid_range_ok(client):
    r = client.get(f"{BASE_URL}/api/export/payments", params={"date_from": "2026-09-01", "date_to": "2026-09-10"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert r.text.splitlines()[0]


def test_export_same_day_ok(client):
    r = client.get(f"{BASE_URL}/api/export/payments", params={"date_from": "2026-09-01", "date_to": "2026-09-01"})
    assert r.status_code == 200


def test_members_csv_formula_escaped(client):
    outlets = client.get(f"{BASE_URL}/api/auth/me").json()
    payload = {"full_name": "=TEST_cmd", "phone": "9000012345", "gender": "male"}
    # pick an outlet if required
    o = (outlets.get("outlets") or [{}])[0].get("id") if isinstance(outlets, dict) else None
    if o:
        payload["outlet_id"] = o
    plans = client.get(f"{BASE_URL}/api/plans").json()
    plans = plans.get("items", plans) if isinstance(plans, dict) else plans
    payload["plan_id"] = plans[0]["id"]
    payload["amount_paid"] = 0
    r = client.post(f"{BASE_URL}/api/members", json=payload)
    assert r.status_code in (200, 201), r.text
    mid = r.json().get("id") or r.json().get("member", {}).get("id")
    try:
        e = client.get(f"{BASE_URL}/api/export/members")
        assert e.status_code == 200
        rows = list(csv.reader(io.StringIO(e.text)))
        cells = [c for row in rows for c in row if "TEST_cmd" in c]
        assert cells, "member not in export"
        assert all(c.startswith("'=") for c in cells), cells
        for row in rows[1:]:
            for c in row:
                if c and c[:1] in "=+-@":
                    try:
                        float(c)
                        continue
                    except ValueError:
                        pass
                    assert False, f"unescaped cell {c!r}"
    finally:
        d = client.delete(f"{BASE_URL}/api/members/{mid}")
        print("delete", d.status_code)
