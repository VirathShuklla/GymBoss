"""Seed/cleanup a throwaway TEST_ tenant with 60 due members (55 expiring in 30 days) for mobile/web 'Load more' UI checks.
Usage: python tests/seed_iter29_pagination_tenant.py seed|cleanup"""
import sys
import uuid
import asyncio
import random
from datetime import timedelta

import paths  # noqa: F401
import requests
from dotenv import dotenv_values

import deps

FE = dotenv_values(paths.FRONTEND_ENV)["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
EMAIL, PW = "test_iter29_pg@example.com", "Iter29Pg@2026"


async def seed():
    s = requests.Session()
    r = s.post(f"{FE}/auth/login", json={"identifier": EMAIL, "password": PW})
    if r.status_code != 200:
        r = s.post(f"{FE}/auth/register", json={"full_name": "TEST Iter29", "email": EMAIL, "phone": "9" + "".join(random.choice("0123456789") for _ in range(9)),
                                               "password": PW, "gym_name": "TEST_Iter29 Gym", "outlet_name": "TEST Main"})
        assert r.status_code == 200, r.text
    org = r.json()["organisation"]["id"] if "organisation" in r.json() else (await deps.db.users.find_one({"email": EMAIL}))["organisation_id"]
    outlet = (await deps.db.outlets.find_one({"organisation_id": org}))["id"]
    await deps.db.members.delete_many({"organisation_id": org})
    today = deps.today_ist()
    docs = [{"id": str(uuid.uuid4()), "organisation_id": org, "outlet_id": outlet, "full_name": f"TEST_PG {i:03d}", "member_code": f"PG{i:03d}",
             "phone": f"+9190000{i:05d}", "deleted_at": None, "due_amount": 100 + i, "plan_name": "Monthly", "joining_date": today.isoformat(),
             "membership_expiry": (today + timedelta(days=1 + i % 25 if i < 55 else 90)).isoformat(), "freeze_history": []} for i in range(60)]
    await deps.db.members.insert_many(docs)
    print("seeded", org)


async def cleanup():
    u = await deps.db.users.find_one({"email": EMAIL})
    if not u:
        print("nothing to clean")
        return
    org = u["organisation_id"]
    for coll in await deps.db.list_collection_names():
        await deps.db[coll].delete_many({"organisation_id": org})
    await deps.db.organisations.delete_one({"id": org})
    await deps.db.users.delete_many({"email": EMAIL})
    print("cleaned", org)


asyncio.run(seed() if sys.argv[1:] == ["seed"] else cleanup())
