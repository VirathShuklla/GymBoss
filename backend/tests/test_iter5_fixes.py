"""Iteration 5 verification: member_code counter, catalogue rows, report projections."""
import os
import requests
import pytest
from dotenv import dotenv_values

env = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or env.get("REACT_APP_BACKEND_URL")).rstrip("/")

DEMO = {"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=DEMO, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return s


# --- Catalogue rows for PT / Service / Product ---
@pytest.mark.parametrize("kind", ["membership", "pt", "service", "product"])
def test_catalogue_not_empty(client, kind):
    r = client.get(f"{BASE}/api/plans", params={"type": kind}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    rows = r.json()
    assert len(rows) > 0, f"no rows for {kind}"
    assert all("_id" not in x for x in rows)


# --- Report projections must include id (rowKey) ---
def test_reports_include_id(client):
    for path, params in [("/api/reports/outstanding-dues", None), ("/api/reports/membership-expiry", {"days": 30})]:
        r = client.get(f"{BASE}{path}", params=params, timeout=30)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        data = r.json()
        rows = data if isinstance(data, list) else data.get("rows", data.get("items", []))
        assert isinstance(rows, list)
        for row in rows:
            assert row.get("id"), f"{path} row missing id: {row}"
        ids = [row["id"] for row in rows]
        assert len(ids) == len(set(ids)), f"{path} duplicate ids"


# --- member_code uniqueness / no collision ---
def test_member_code_no_collision(client):
    r = client.get(f"{BASE}/api/plans", params={"type": "membership"}, timeout=30)
    plan = r.json()[0]
    codes = []
    ids = []
    try:
        for i in range(3):
            body = {
                "full_name": f"TEST_Iter5 Counter {i}",
                "phone": f"90000{i:05d}",
                "gender": "male",
                "plan_id": plan["id"],
                "join_date": "2026-07-01",
                "fee": plan.get("price", 1000),
            }
            resp = client.post(f"{BASE}/api/members", json=body, timeout=30)
            assert resp.status_code in (200, 201), resp.text[:400]
            m = resp.json()
            assert m.get("member_code"), m
            codes.append(m["member_code"])
            ids.append(m["id"])
            # verify persisted
            g = client.get(f"{BASE}/api/members/{m['id']}", timeout=30)
            assert g.status_code == 200
            assert g.json()["member"]["member_code"] == m["member_code"]
        assert len(set(codes)) == 3, codes
        nums = [int(c.split("-")[1]) for c in codes]
        assert nums == sorted(nums) and nums[-1] - nums[0] == 2, codes
        print("codes:", codes)
    finally:
        for mid in ids:
            client.delete(f"{BASE}/api/members/{mid}", timeout=30)
