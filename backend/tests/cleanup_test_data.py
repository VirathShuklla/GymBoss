"""Purge QA-created TEST_* documents so seeded-data assertions in backend_test.py stay valid.
Run: python /app/backend/tests/cleanup_test_data.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values

be = dotenv_values("/app/backend/.env")
RX = {"$regex": "^TEST_", "$options": "i"}


async def main():
    c = AsyncIOMotorClient(be["MONGO_URL"])
    db = c[be["DB_NAME"]]
    report = {}

    # members created by tests (and their payments / attendance)
    mids = [m["id"] async for m in db.members.find({"full_name": RX}, {"id": 1})]
    if mids:
        report["attendance"] = (await db.attendance.delete_many({"member_id": {"$in": mids}})).deleted_count
        report["payments"] = (await db.payments.delete_many({"member_id": {"$in": mids}})).deleted_count
        report["members"] = (await db.members.delete_many({"id": {"$in": mids}})).deleted_count

    report["outlets"] = (await db.outlets.delete_many({"name": RX})).deleted_count
    report["plans"] = (await db.plans.delete_many({"name": RX})).deleted_count
    report["enquiries"] = (await db.enquiries.delete_many({"name": RX})).deleted_count
    report["expenses"] = (await db.expenses.delete_many({"name": RX})).deleted_count
    report["announcements"] = (await db.announcements.delete_many({"title": RX})).deleted_count
    report["support_requests"] = (await db.support_requests.delete_many({"subject": RX})).deleted_count

    staff_ids = [s["id"] async for s in db.staff.find({"name": RX}, {"id": 1})]
    if staff_ids:
        report["staff_users"] = (await db.users.delete_many({"staff_id": {"$in": staff_ids}})).deleted_count
        report["staff"] = (await db.staff.delete_many({"id": {"$in": staff_ids}})).deleted_count

    # throwaway orgs from tenant-isolation registration
    orgs = [o["id"] async for o in db.organisations.find({"name": RX}, {"id": 1})]
    for oid in orgs:
        for coll in ("users", "outlets", "plans", "members", "payments", "enquiries", "expenses",
                     "staff", "announcements", "subscriptions", "subscription_payments",
                     "attendance", "audit_logs", "support_requests"):
            await db[coll].delete_many({"organisation_id": oid})
        await db.organisations.delete_many({"id": oid})
    report["orgs"] = len(orgs)
    report["iso_users"] = (await db.users.delete_many({"email": {"$regex": "^test_(iso|staff|qa)_"}})).deleted_count
    report["login_attempts"] = (await db.login_attempts.delete_many({"email": {"$regex": "^test_|lockout_probe"}})).deleted_count

    c.close()
    print({k: v for k, v in report.items() if v})


asyncio.run(main())
