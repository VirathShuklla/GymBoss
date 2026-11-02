import random
import uuid
from datetime import date, timedelta

import httpx

API = "http://localhost:8002/api"
random.seed(11)
c = httpx.Client(base_url=API, timeout=30, headers={"X-Client-Platform": "android_store"})


def post(path, body):
    r = c.post(path, json=body, headers={"Idempotency-Key": str(uuid.uuid4())})
    if r.status_code >= 400:
        print("ERR", path, r.status_code, r.text[:200])
    return r.json() if r.status_code < 400 else None


r = post("/auth/register", {"full_name": "Rohan Mehta", "email": "store@gymboss-sample.in", "phone": "9876500011", "password": "StoreShots@2026",
                            "gym_name": "Peak Fitness Studio", "outlet_name": "Main Branch", "city": "Pune"})
if r is None:
    r = post("/auth/login", {"identifier": "store@gymboss-sample.in", "password": "StoreShots@2026"})
c.headers["Authorization"] = "Bearer " + r["tokens"]["access_token"]

plans = {}
for name, months, price in [("Monthly", 1, 1500), ("Quarterly", 3, 4000), ("Half-Yearly", 6, 7500), ("Annual", 12, 13000)]:
    p = post("/plans", {"name": name, "duration_type": "months", "duration": months, "price": price, "category": "General"})
    plans[name] = p
for name, price in [("Personal Training · 12 sessions", 6000)]:
    post("/plans", {"name": name, "type": "pt", "duration_type": "months", "duration": 1, "price": price, "sessions": 12})

names = ["Aarav Sharma", "Priya Nair", "Kabir Malhotra", "Ananya Iyer", "Vikram Singh", "Sneha Kulkarni", "Rahul Verma", "Meera Joshi",
         "Arjun Reddy", "Ishita Kapoor", "Karan Gill", "Pooja Desai", "Siddharth Rao", "Neha Gupta", "Aditya Patil", "Riya Chawla",
         "Manish Tiwari", "Kavya Menon", "Nikhil Jain", "Tanvi Shah", "Yash Pandey", "Diya Bose", "Harsh Agarwal", "Lakshmi Narayan",
         "Rohit Saxena", "Simran Kaur", "Varun Kapoor", "Nisha Rane", "Dev Khanna", "Aisha Khan", "Om Prakash", "Zoya Mirza"]
today = date.today()
members = []
for i, n in enumerate(names):
    plan = random.choice(["Monthly", "Monthly", "Quarterly", "Half-Yearly", "Annual"])
    months = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Annual": 12}[plan]
    start = today - timedelta(days=random.randint(2, months * 30 - 1))
    price = plans[plan]["price"]
    paid = price if i % 4 else price - random.choice([500, 1000, 1500])
    paid_today = i < 9
    m = post("/members", {"full_name": n, "phone": f"98{random.randint(10000000, 99999999)}", "gender": "Male" if i % 2 == 0 else "Female",
                          "plan_id": plans[plan]["id"], "membership_start": (today if paid_today else start).isoformat(),
                          "joining_date": (today if paid_today else start).isoformat(),
                          "admission_amount": 500 if paid_today else 0, "amount_paid": paid + (500 if paid_today else 0),
                          "payment_method": random.choice(["UPI", "UPI", "Cash", "Card"]),
                          "payment_date": (today if paid_today else start).isoformat()})
    if m:
        members.append(m)

for m in members[9:14]:
    if m.get("due_amount", 0) > 0:
        post("/payments", {"member_id": m["id"], "amount": m["due_amount"], "method": "UPI", "payment_date": today.isoformat()})

for m in random.sample(members, 17):
    post("/attendance/check-in", {"member_id": m["id"]})

for name, role, phone in [("Sameer Khan", "manager", "9811100021"), ("Anjali Pillai", "trainer", "9811100022"), ("Ravi Kumar", "receptionist", "9811100023"), ("Fatima Sheikh", "trainer", "9811100024")]:
    post("/staff", {"name": name, "role": role, "phone": phone, "joining_date": (today - timedelta(days=200)).isoformat()})

for name, cat, amt, d in [("Electricity bill", "Utilities", 6200, 2), ("Equipment servicing", "Maintenance", 3500, 5), ("Cleaning supplies", "General", 1200, 1)]:
    post("/expenses", {"name": name, "category": cat, "amount": amt, "date": (today - timedelta(days=min(d, today.day - 1))).isoformat(), "method": "UPI"})

for n, src in [("Gaurav Mishra", "Instagram"), ("Shreya Patel", "Walk-in"), ("Imran Ali", "Referral")]:
    post("/enquiries", {"name": n, "phone": f"97{random.randint(10000000, 99999999)}", "source": src, "interested_in": "Quarterly"})
print("seeded", len(members), "members")
