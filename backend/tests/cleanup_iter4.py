"""Iteration-4 QA data cleanup: remove TEST_ member + revert seeded-member payment."""
from pymongo import MongoClient
from dotenv import dotenv_values

e = dotenv_values("/app/backend/.env")
db = MongoClient(e["MONGO_URL"])[e["DB_NAME"]]

# 1. TEST_ members created via UI + their payments/attendance
tm = list(db.members.find({"full_name": {"$regex": "^TEST_"}}, {"id": 1, "full_name": 1}))
ids = [m["id"] for m in tm]
print("TEST_ members:", [m["full_name"] for m in tm])
print("payments removed:", db.payments.delete_many({"member_id": {"$in": ids}}).deleted_count)
print("attendance removed:", db.attendance.delete_many({"member_id": {"$in": ids}}).deleted_count)
print("members removed:", db.members.delete_many({"id": {"$in": ids}}).deleted_count)

# 2. revert the QA Rs.100 payment recorded on seeded member Shreya Saxena
s = db.members.find_one({"full_name": "Shreya Saxena"})
if s:
    qa = list(db.payments.find({"member_id": s["id"], "amount": 100}))
    for p in qa:
        db.payments.delete_one({"id": p["id"]})
    if qa:
        db.members.update_one({"id": s["id"]}, {"$inc": {"due_amount": 100 * len(qa)}})
    print("Shreya QA payments reverted:", len(qa), "due now:", db.members.find_one({"id": s["id"]})["due_amount"])

print("duplicate member_codes remaining:", list(db.members.aggregate([
    {"$match": {"deleted_at": None}},
    {"$group": {"_id": {"o": "$organisation_id", "c": "$member_code"}, "n": {"$sum": 1}}},
    {"$match": {"n": {"$gt": 1}}},
])))
print("total active members:", db.members.count_documents({"deleted_at": None}))
