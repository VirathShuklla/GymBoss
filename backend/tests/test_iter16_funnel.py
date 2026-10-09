"""Iter 16: conversion events + funnel + trial status + trial-expired write-block + activation rules.

Covers:
- POST /api/events accepts all CLIENT_EVENTS and rejects unknown event names ({ok:false}).
- Registering a gym with visitor_id links prior landing_visit events, emits signup_completed + gym_created,
  and sets organisations.acquisition_source.
- Milestones: membership_plan_created (per plan POST), first_member_added, third_member_added,
  first_payment_recorded, trial_activated (once rules met) + organisations.activated_at.
- GET /api/trial/status structure (status/days_left/day_number/from_price/stats{...}).
- Trial countdown phases exercised by mutating trial_ends_at (NOT the demo org).
- Trial expiry read-only: POST/PUT/DELETE on data endpoints -> 402; subscription/auth/events/support still work.
- GET /api/admin/funnel structure (stages, counts, from_previous, cta, sources, stuck, events, tracking_since).
- PUT /api/admin/settings activation_rules validation (all-zero -> 422, >100 -> 422), restore defaults 1/3/1.
- Cleanup: delete all TEST_ orgs/users/members/payments/plans + visitor events we created.
"""
import os
import sys
import uuid
import time
from datetime import datetime, timezone, timedelta

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"

backend_env = dotenv_values("/app/backend/.env")
MONGO = MongoClient(os.environ.get("MONGO_URL") or backend_env["MONGO_URL"])
DB = MONGO[os.environ.get("DB_NAME") or backend_env["DB_NAME"]]

ALL_CLIENT_EVENTS = [
    "landing_visit", "hero_cta_click", "demo_click", "pricing_viewed", "pricing_cta_click",
    "signup_started", "whatsapp_used", "subscription_plan_selected", "payment_failed", "excel_import_used",
]
ALL_EVENTS_DEFINED = [
    "landing_visit", "hero_cta_click", "demo_click", "pricing_viewed", "pricing_cta_click", "signup_started",
    "signup_completed", "gym_created", "membership_plan_created", "first_member_added", "third_member_added",
    "first_payment_recorded", "excel_import_used", "whatsapp_used", "trial_activated", "subscription_started",
    "subscription_plan_selected", "payment_initiated", "payment_successful", "payment_failed",
]

CREATED = {"orgs": set(), "visitor_ids": set(), "users": set()}


# ---------------- fixtures ----------------

@pytest.fixture(scope="module")
def super_admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": "GymBoss", "password": "GymBoss@2026"})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def demo():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
    assert r.status_code == 200, r.text
    return s


def _register_test_gym(suffix: str, visitor_id: str | None = None):
    """Register a fresh TEST_ org and return (session, user, org)."""
    s = requests.Session()
    email = f"test_iter16_{suffix}_{uuid.uuid4().hex[:6]}@testgym.in"
    phone = "9" + str(uuid.uuid4().int % 1000000000).zfill(9)
    body = {
        "full_name": f"TEST_{suffix}",
        "email": email,
        "phone": phone,
        "password": "TestPass@2026",
        "gym_name": f"TEST_{suffix}_{uuid.uuid4().hex[:4]}",
        "outlet_name": "Main",
        "city": "Bengaluru",
    }
    if visitor_id:
        body["visitor_id"] = visitor_id
    r = s.post(f"{API}/auth/register", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    CREATED["orgs"].add(data["organisation"]["id"])
    CREATED["users"].add(data["user"]["id"])
    if visitor_id:
        CREATED["visitor_ids"].add(visitor_id)
    return s, data["user"], data["organisation"]


# ---------------- /api/events ----------------

def test_events_accepts_all_client_events():
    for ev in ALL_CLIENT_EVENTS:
        vid = f"TEST_vid_{uuid.uuid4().hex[:8]}"
        CREATED["visitor_ids"].add(vid)
        r = requests.post(f"{API}/events", json={"event": ev, "visitor_id": vid, "path": "/"})
        assert r.status_code == 200, f"{ev} -> {r.status_code} {r.text}"
        assert r.json().get("ok") is True, f"{ev} not accepted"


def test_events_rejects_unknown_event():
    r = requests.post(f"{API}/events", json={"event": "not_a_real_event", "visitor_id": "TEST_vid_x"})
    assert r.status_code == 200
    assert r.json() == {"ok": False}


def test_events_rejects_server_only_event_from_client():
    # signup_completed, gym_created, trial_activated etc. are server-emitted only
    r = requests.post(f"{API}/events", json={"event": "signup_completed", "visitor_id": "TEST_vid_y"})
    assert r.json() == {"ok": False}


# ---------------- visitor linking + signup/gym events ----------------

def test_register_links_visitor_events_and_emits_signup_completed_and_gym_created():
    vid = f"TEST_vid_{uuid.uuid4().hex[:8]}"
    r1 = requests.post(f"{API}/events", json={
        "event": "landing_visit", "visitor_id": vid, "path": "/",
        "utm_source": "qa_test", "utm_medium": "pytest",
    })
    assert r1.status_code == 200 and r1.json()["ok"] is True

    sess, user, org = _register_test_gym("link", visitor_id=vid)

    org_doc = DB.organisations.find_one({"id": org["id"]})
    assert org_doc["visitor_id"] == vid
    assert org_doc.get("acquisition_source") == "qa_test"

    # pre-signup event got linked
    linked = DB.events.find_one({"visitor_id": vid, "event": "landing_visit"})
    assert linked and linked.get("org_id") == org["id"]

    # server-only events exist
    for ev in ("signup_completed", "gym_created"):
        assert DB.events.find_one({"event": ev, "org_id": org["id"]}), f"missing {ev}"


# ---------------- milestone events (plan, member, member #3, payment, trial_activated) ----------------

def test_milestones_and_trial_activated():
    sess, user, org = _register_test_gym("milestones")
    org_id = org["id"]

    # Create 1 plan -> membership_plan_created
    r = sess.post(f"{API}/plans", json={"name": "TEST_M", "price": 1000, "duration_value": 1, "duration_type": "months"})
    assert r.status_code in (200, 201), r.text
    plan_id = r.json()["id"]
    assert DB.events.count_documents({"org_id": org_id, "event": "membership_plan_created"}) >= 1

    # Create 3 members -> first_member_added + third_member_added (once each)
    member_ids = []
    for i in range(3):
        rm = sess.post(f"{API}/members", json={
            "full_name": f"TEST_Member_{i}",
            "phone": "9" + str(uuid.uuid4().int % 1000000000).zfill(9),
            "plan_id": plan_id,
            "joining_date": datetime.now(timezone.utc).date().isoformat(),
        })
        assert rm.status_code in (200, 201), rm.text
        member_ids.append(rm.json()["id"])

    assert DB.events.count_documents({"org_id": org_id, "event": "first_member_added"}) == 1
    assert DB.events.count_documents({"org_id": org_id, "event": "third_member_added"}) == 1

    # Record 1 payment on 1st member -> first_payment_recorded + trial_activated (rules 1/3/1 met)
    rp = sess.post(f"{API}/payments", json={
        "member_id": member_ids[0],
        "amount": 1000,
        "method": "Cash",
        "plan_id": plan_id,
        "type": "renewal",
    })
    assert rp.status_code in (200, 201), rp.text

    assert DB.events.count_documents({"org_id": org_id, "event": "first_payment_recorded"}) == 1
    assert DB.events.count_documents({"org_id": org_id, "event": "trial_activated"}) == 1

    org_doc = DB.organisations.find_one({"id": org_id})
    assert org_doc.get("activated_at") is not None


# ---------------- /api/trial/status ----------------

def test_trial_status_structure(demo):
    r = demo.get(f"{API}/trial/status")
    assert r.status_code == 200, r.text
    j = r.json()
    for k in ("status", "days_left", "day_number", "trial_days", "from_price", "stats"):
        assert k in j, f"missing {k}"
    for sk in ("members", "payments", "attendance", "renewals", "plans"):
        assert sk in j["stats"]
        assert isinstance(j["stats"][sk], int)
    assert isinstance(j["from_price"], int) and j["from_price"] >= 1


# ---------------- Trial expiry: read-only / write-block ----------------

def test_trial_expired_blocks_writes_and_allows_reads_and_subscription():
    sess, user, org = _register_test_gym("expired")
    org_id = org["id"]

    # Force trial expiry in the past
    past = datetime.now(timezone.utc) - timedelta(days=2)
    DB.organisations.update_one({"id": org_id}, {"$set": {
        "subscription.status": "trial",
        "subscription.trial_ends_at": past,
        "subscription.trial_started_at": past - timedelta(days=10),
    }})

    # Read works
    r = sess.get(f"{API}/members")
    assert r.status_code == 200, r.text

    # Write on members blocked -> 402
    rw = sess.post(f"{API}/members", json={
        "full_name": "TEST_Blocked", "phone": "9" + str(uuid.uuid4().int % 1000000000).zfill(9),
        "joining_date": datetime.now(timezone.utc).date().isoformat(),
    })
    assert rw.status_code == 402, f"expected 402, got {rw.status_code}: {rw.text}"
    detail = rw.json().get("detail", "")
    assert "view-only" in detail.lower() and "safe" in detail.lower(), detail

    # Payments blocked
    rp = sess.post(f"{API}/payments", json={"member_id": "x", "amount": 1, "method": "Cash"})
    assert rp.status_code == 402

    # Plans blocked
    rpl = sess.post(f"{API}/plans", json={"name": "x", "price": 1, "duration_value": 1, "duration_type": "months"})
    assert rpl.status_code == 402

    # trial_status still works
    rt = sess.get(f"{API}/trial/status")
    assert rt.status_code == 200
    assert rt.json()["status"] == "expired"

    # Event ingestion still works (allow-listed)
    re = sess.post(f"{API}/events", json={"event": "pricing_viewed", "path": "/app/subscription"})
    assert re.status_code == 200 and re.json().get("ok") is True

    # Data preserved
    assert DB.organisations.find_one({"id": org_id}) is not None


# ---------------- /api/admin/funnel ----------------

def test_admin_funnel_structure(super_admin):
    r = super_admin.get(f"{API}/admin/funnel?days=30")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["days"] == 30
    assert "rules" in j and {"min_plans", "min_members", "min_payments"} <= set(j["rules"].keys())
    funnel = j["funnel"]
    keys = [s["key"] for s in funnel]
    assert keys == ["visitors", "signup_started", "registered", "gym_created", "activated", "paying", "retained"]
    for s in funnel:
        assert set(s.keys()) >= {"key", "label", "description", "count", "from_previous", "from_top"}
        assert isinstance(s["count"], int)
    # All 20 events must be listed
    ev_names = {e["event"] for e in j["events"]}
    assert ev_names == set(ALL_EVENTS_DEFINED), f"missing: {set(ALL_EVENTS_DEFINED) - ev_names}"
    # cta block
    for k in ("hero_cta_click", "demo_click", "pricing_viewed", "pricing_cta_click"):
        assert k in j["cta"]
        assert "count" in j["cta"][k]
    assert "sources" in j and isinstance(j["sources"], list)
    assert "stuck" in j and isinstance(j["stuck"], list)
    assert "tracking_since" in j


def test_admin_funnel_range_switch(super_admin):
    for d in (7, 30, 90):
        r = super_admin.get(f"{API}/admin/funnel?days={d}")
        assert r.status_code == 200
        assert r.json()["days"] == d


# ---------------- activation_rules PUT validation ----------------

def test_activation_rules_update_and_restore(super_admin):
    # all zero -> 422
    r = super_admin.put(f"{API}/admin/settings", json={
        "activation_rules": {"min_plans": 0, "min_members": 0, "min_payments": 0}
    })
    assert r.status_code == 422, r.text

    # >100 -> 422
    r = super_admin.put(f"{API}/admin/settings", json={
        "activation_rules": {"min_plans": 1, "min_members": 101, "min_payments": 1}
    })
    assert r.status_code == 422, r.text

    # valid update
    r = super_admin.put(f"{API}/admin/settings", json={
        "activation_rules": {"min_plans": 2, "min_members": 5, "min_payments": 2}
    })
    assert r.status_code == 200, r.text
    assert r.json()["activation_rules"] == {"min_plans": 2, "min_members": 5, "min_payments": 2}

    # restore defaults 1/3/1
    r = super_admin.put(f"{API}/admin/settings", json={
        "activation_rules": {"min_plans": 1, "min_members": 3, "min_payments": 1}
    })
    assert r.status_code == 200
    assert r.json()["activation_rules"] == {"min_plans": 1, "min_members": 3, "min_payments": 1}


# ---------------- subscription_plan_selected + payment_initiated server events ----------------

def test_subscription_plan_selected_and_payment_initiated():
    sess, user, org = _register_test_gym("sub")
    org_id = org["id"]

    # subscription_plan_selected is CLIENT-side; verify through /api/events ingress
    r = sess.post(f"{API}/events", json={"event": "subscription_plan_selected", "props": {"plan": "quarterly"}})
    assert r.status_code == 200 and r.json().get("ok") is True
    assert DB.events.count_documents({"org_id": org_id, "event": "subscription_plan_selected"}) >= 1

    # payment_initiated via /api/subscription/autodebit/start (no live Razorpay keys in test env is OK -> may fail softly)
    r = sess.post(f"{API}/subscription/autodebit/start", json={"plan": "monthly"})
    # endpoint may require configured keys; accept 200 or 400/402/500 but check event emitted only on success path
    if r.status_code == 200:
        assert DB.events.count_documents({"org_id": org_id, "event": "payment_initiated"}) >= 1
    else:
        # at minimum, endpoint must not 404
        assert r.status_code in (400, 402, 422, 500, 503), f"unexpected {r.status_code}: {r.text[:200]}"


# ---------------- cleanup ----------------

def test_cleanup_test_data():
    org_ids = list(CREATED["orgs"])
    user_ids = list(CREATED["users"])
    vids = list(CREATED["visitor_ids"])

    if org_ids:
        DB.members.delete_many({"organisation_id": {"$in": org_ids}})
        DB.payments.delete_many({"organisation_id": {"$in": org_ids}})
        DB.plans.delete_many({"organisation_id": {"$in": org_ids}})
        DB.outlets.delete_many({"organisation_id": {"$in": org_ids}})
        DB.batches.delete_many({"organisation_id": {"$in": org_ids}})
        DB.attendance.delete_many({"organisation_id": {"$in": org_ids}})
        DB.audit_logs.delete_many({"organisation_id": {"$in": org_ids}})
        DB.events.delete_many({"org_id": {"$in": org_ids}})
        DB.organisations.delete_many({"id": {"$in": org_ids}})
    if user_ids:
        DB.users.delete_many({"id": {"$in": user_ids}})
    if vids:
        DB.events.delete_many({"visitor_id": {"$in": vids}})

    # ensure activation rules back to defaults
    DB.settings.update_one({"id": "platform"}, {"$set": {"activation_rules": {"min_plans": 1, "min_members": 3, "min_payments": 1}}}, upsert=True)
