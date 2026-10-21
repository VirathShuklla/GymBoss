"""Seed a TEST_ member in demo org with a reversed ₹100 payment for iter26 UI checks."""
import os
import random
import json
import requests

BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/")
s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
r.raise_for_status()
plans = s.get(f"{BASE}/api/plans", params={"type": "membership"}).json()
ph = "9" + "".join(random.choice("0123456789") for _ in range(9))
m = s.post(f"{BASE}/api/members", json={"full_name": "TEST_Iter26 Reversal", "phone": ph, "plan_id": plans[0]["id"], "amount_paid": 0})
m.raise_for_status()
mid = m.json()["id"]
p = s.post(f"{BASE}/api/payments", json={"member_id": mid, "amount": 100})
p.raise_for_status()
pid = p.json()["id"]
d = s.delete(f"{BASE}/api/payments/{pid}", json={"reason": "TEST iter26"})
print("reverse:", d.status_code, d.text[:200])
p2 = s.post(f"{BASE}/api/payments", json={"member_id": mid, "amount": 50})
pays = s.get(f"{BASE}/api/members/{mid}").json().get("payments", [])
out = {"member_id": mid, "phone": ph, "orig": pid, "normal": p2.json().get("id"),
       "payments": [{k: x.get(k) for k in ("id", "amount", "status", "type", "reversal_of")} for x in pays]}
print(json.dumps(out, indent=1))
