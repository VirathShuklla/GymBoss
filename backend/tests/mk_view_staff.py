"""Create (or delete) a view-only staff login for frontend QA.
Usage: python mk_view_staff.py create | python mk_view_staff.py delete
"""
import sys
import requests
from conftest import API

EMAIL = "test_qa_viewonly@testgym.in"
PWD = "QaStaff@2026"


def demo():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
    assert r.status_code == 200, r.text[:200]
    return s


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "create"
    s = demo()
    staff = s.get(f"{API}/staff").json()
    existing = [x for x in staff if x.get("email") == EMAIL]
    if action == "delete":
        for x in existing:
            print("delete", x["id"], s.delete(f"{API}/staff/{x['id']}").status_code)
        return
    for x in existing:
        s.delete(f"{API}/staff/{x['id']}")
    outlet_id = s.get(f"{API}/outlets").json()[0]["id"]
    r = s.post(f"{API}/staff", json={
        "name": "TEST_QA ViewOnly", "phone": "9000012345", "email": EMAIL,
        "role": "receptionist", "outlet_id": outlet_id, "permission": "view",
        "enable_finance": False, "password": PWD,
    })
    print(r.status_code, r.json())
    print("settings:", s.get(f"{API}/public/config").json())


main()
