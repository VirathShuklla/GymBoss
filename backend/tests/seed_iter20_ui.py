# Seeds throwaway orgs for iteration-20 UI tests: paid+autodebit org, expired org, staff user. Writes /tmp/iter20_ui.json
import json
import uuid
from datetime import datetime, timezone, timedelta

import requests
from test_iter20_billing_sync import register, send, sub_event, mdb, API

out = {}
# 1. Active paid org with active autodebit
s, data, email = register()
org_id = data["organisation"]["id"]
rzp = f"sub_TESTUI{uuid.uuid4().hex[:8]}"
mdb.subscriptions.insert_one({"id": str(uuid.uuid4()), "organisation_id": org_id, "razorpay_subscription_id": rzp, "plan_key": "monthly",
                              "amount": 999, "status": "created", "created_at": datetime.now(timezone.utc)})
send(sub_event("activated", rzp, f"pay_TESTUI{uuid.uuid4().hex[:8]}"), f"evt_{uuid.uuid4().hex}")
out["paid"] = {"email": email, "org_id": org_id}
# staff (receptionist) in paid org
outlet_id = s.get(f"{API}/outlets").json()[0]["id"]
staff_email = f"test_staff_{uuid.uuid4().hex[:8]}@testgym.in"
r = s.post(f"{API}/staff", json={"name": "TEST Staff", "phone": "9" + str(uuid.uuid4().int)[:9], "email": staff_email, "role": "receptionist",
                                 "outlet_id": outlet_id, "permission": "edit", "enable_finance": False, "password": "QaStaff@2026"})
print("staff", r.status_code, r.text[:200])
out["staff"] = {"email": staff_email}
# 2. Expired trial org
s2, d2, e2 = register()
mdb.organisations.update_one({"id": d2["organisation"]["id"]}, {"$set": {"subscription.trial_ends_at": datetime.now(timezone.utc) - timedelta(days=1)}})
out["expired"] = {"email": e2, "org_id": d2["organisation"]["id"]}
# 3. Fresh trial org
s3, d3, e3 = register()
out["trial"] = {"email": e3, "org_id": d3["organisation"]["id"]}
json.dump(out, open("/tmp/iter20_ui.json", "w"), indent=1)
print(json.dumps(out, indent=1))
