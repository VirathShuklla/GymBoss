# Seed a throwaway org for iteration-23 UI checks: one membership plan, one member with credit balance.
import json, uuid, requests
from dotenv import dotenv_values
FE = dotenv_values("/app/frontend/.env")
API = FE["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
s = requests.Session()
tag = uuid.uuid4().hex[:6]
email = f"test_iter23_ui_{tag}@example.com"
r = s.post(f"{API}/auth/register", json={"full_name": "TEST UI Owner", "email": email, "phone": "9" + str(uuid.uuid4().int)[:9],
                                          "password": "TestPass@2026", "gym_name": f"TEST UI Gym {tag}", "outlet_name": "Main"})
r.raise_for_status()
org_id = r.json()["organisation"]["id"]
plan = s.post(f"{API}/plans", json={"name": "TEST Solo Plan", "price": 1000, "duration_type": "months", "duration": 1}).json()
m = s.post(f"{API}/members", json={"full_name": f"TEST Credit {tag}", "phone": "9" + str(uuid.uuid4().int)[:9], "plan_id": plan["id"], "amount_paid": 1000}).json()
p = s.post(f"{API}/members/{m['id']}/payments", json={"amount": 300, "payment_method": "Cash"})
if p.status_code >= 400:
    p = s.post(f"{API}/payments", json={"member_id": m["id"], "amount": 300, "payment_method": "Cash"})
print("payment", p.status_code, p.text[:200])
g = s.get(f"{API}/members/{m['id']}").json()
mm = g.get("member") or g
print(json.dumps({"email": email, "org_id": org_id, "plan_id": plan["id"], "member_id": m["id"], "name": mm["full_name"],
                  "credit": mm.get("credit_balance"), "due": mm.get("due_amount")}))
