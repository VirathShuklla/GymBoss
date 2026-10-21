"""Iteration 11 changeset tests: members filters (due/status) and payment receipt."""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


def test_members_all(client):
    r = client.get(f"{API}/members?limit=200")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and isinstance(data["items"], list)
    assert data["total"] >= 1


def test_members_status_active(client):
    r = client.get(f"{API}/members?status=active&limit=200")
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(m["status"].lower() == "active" for m in items), \
        f"non-active member returned: {[m['status'] for m in items]}"


def test_members_due_true(client):
    r = client.get(f"{API}/members?due=true&limit=200")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 0
    assert all((m.get("due_amount") or 0) > 0 for m in items), \
        f"member with no dues returned: {[(m['full_name'], m.get('due_amount')) for m in items]}"


def test_members_due_false_returns_all(client):
    r = client.get(f"{API}/members?due=false&limit=200")
    assert r.status_code == 200
    # due=false should NOT filter (only true filters)
    all_r = client.get(f"{API}/members?limit=200").json()
    assert r.json()["total"] == all_r["total"]


def test_payment_and_receipt(client):
    # find a member (or create); use existing
    r = client.get(f"{API}/members?limit=5")
    items = r.json()["items"]
    assert items, "no members seeded"
    member = items[0]

    # record a due-clearance payment (or a small amount)
    payload = {"member_id": member["id"], "amount": 1.0, "method": "Cash", "notes": "TEST_iter11"}
    r = client.post(f"{API}/payments", json=payload)
    assert r.status_code in (200, 201), f"payment failed: {r.status_code} {r.text}"
    p = r.json()
    assert p.get("receipt_no"), f"no receipt_no in payment response: {p}"
    payment_id = p["id"]

    # get receipt
    r = client.get(f"{API}/payments/{payment_id}/receipt")
    assert r.status_code == 200, f"receipt fetch failed: {r.status_code} {r.text}"
    body = r.json()
    assert set(["payment", "member", "gym", "outlet"]).issubset(body.keys()), f"missing keys: {body.keys()}"
    assert body["member"] and body["member"].get("phone"), "member.phone missing"
    assert body["payment"].get("receipt_no"), "payment.receipt_no missing"
    assert body["gym"].get("name")
