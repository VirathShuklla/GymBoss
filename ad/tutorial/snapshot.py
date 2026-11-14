import asyncio
import os
import sys
from pathlib import Path

from bson import json_util
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
SNAP = Path(__file__).parent / "demo_snapshot.json"


async def main(cmd):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    org = await db.organisations.find_one({"name": "Iron Paradise Fitness"})
    oid = org["id"]
    names = await db.list_collection_names()
    if cmd == "save":
        data = {"organisations": [org]}
        for c in names:
            if c != "organisations":
                data[c] = await db[c].find({"organisation_id": oid}).to_list(None)
        SNAP.write_text(json_util.dumps(data))
        print("saved", {k: len(v) for k, v in data.items() if v})
    else:
        data = json_util.loads(SNAP.read_text())
        await db.organisations.replace_one({"id": oid}, data["organisations"][0])
        for c in names:
            if c == "organisations":
                continue
            await db[c].delete_many({"organisation_id": oid})
            if data.get(c):
                await db[c].insert_many(data[c])
        print("restored")

asyncio.run(main(sys.argv[1]))
