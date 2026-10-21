"""Ad-hoc retest: public-ingress lockout, bcrypt format, httpOnly cookies, IST day bounds."""
import asyncio
import os

import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
benv = dotenv_values("/app/backend/.env")
IDENT = "lockout_probe_retest@testgym.in"


def lockout():
    codes = []
    s = requests.Session()
    for _ in range(6):
        r = s.post(f"{BASE}/auth/login", json={"identifier": IDENT, "password": "WrongPass!1"}, timeout=30)
        codes.append(r.status_code)
    print("PUBLIC lockout codes:", codes)
    print("PASS: 401x5 then 429" if codes[:5] == [401] * 5 and codes[5] == 429 else "FAIL: lockout not enforced via public URL")


def cookies_and_login():
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"}, timeout=30)
    print("demo login status:", r.status_code)
    raw = r.headers.get("set-cookie", "")
    for name in ("access_token", "refresh_token"):
        present = name in raw
        print(f"{'PASS' if present else 'FAIL'}: {name} cookie set")
    print("PASS: HttpOnly present" if "HttpOnly" in raw or "httponly" in raw.lower() else "FAIL: HttpOnly missing")
    print("INFO set-cookie:", raw[:400])
    me = s.get(f"{BASE}/auth/me", timeout=30)
    print("GET /auth/me via cookies:", me.status_code)
    d = s.get(f"{BASE}/dashboard/summary", timeout=30).json()
    print("summary today_collection:", d.get("today_collection"), "active_members:", d.get("active_members"))


async def db_checks():
    cli = AsyncIOMotorClient(benv["MONGO_URL"])
    db = cli[benv["DB_NAME"]]
    u = await db.users.find_one({"email": "demo@gymbossvvo.in"})
    h = u["password_hash"]
    print(f"{'PASS' if h.startswith('$2b$') else 'FAIL'}: bcrypt prefix {h[:7]}")
    admin = await db.users.find_one({"username": "GymBoss"})
    print(f"{'PASS' if admin and admin['password_hash'].startswith('$2b$') else 'FAIL'}: admin bcrypt")
    tok = await db.password_reset_tokens.find_one({}, sort=[("expires_at", -1)])
    if tok:
        print(f"{'PASS' if 'token_hash' in tok and 'token' not in tok else 'FAIL'}: reset token stored hashed only (keys={list(tok.keys())})")
    # cleanup lockout probe rows
    res = await db.login_attempts.delete_many({"email": IDENT})
    print("cleaned login_attempts:", res.deleted_count)
    # cleanup QA test orgs from this run
    qa_users = await db.users.find({"email": {"$regex": "^qa_retest_"}}).to_list(50)
    for qu in qa_users:
        oid = qu.get("organisation_id")
        await db.outlets.delete_many({"organisation_id": oid})
        await db.organisations.delete_many({"id": oid})
        await db.subscriptions.delete_many({"organisation_id": oid})
        await db.users.delete_one({"id": qu["id"]})
    print("cleaned qa_retest orgs:", len(qa_users))
    # restore demo onboarding dismissed=false
    r = await db.organisations.update_one({"name": "Iron Paradise Fitness"}, {"$set": {"onboarding.dismissed": False}})
    print("restored demo onboarding.dismissed=False:", r.modified_count)
    cli.close()


if __name__ == "__main__":
    lockout()
    cookies_and_login()
    asyncio.run(db_checks())
