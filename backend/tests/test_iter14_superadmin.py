"""Iteration 14 — Super-admin analytics console: /api/admin/analytics,
/api/admin/gyms filters and health, 403 for non-super-admin, and reconciliation of
numeric fields against the underlying collections."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://violet-gym-app.preview.emergentagent.com").rstrip("/")
SA = {"identifier": "GymBoss", "password": "GymBoss@2026"}
OWNER = {"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"}


def _session(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login {creds['identifier']} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def sa_headers():
    return _session(SA)


@pytest.fixture(scope="module")
def owner_headers():
    return _session(OWNER)


# --- AUTH / ACCESS ----------------------------------------------------------
class TestAccess:
    def test_owner_forbidden_analytics(self, owner_headers):
        r = owner_headers.get(f"{BASE}/api/admin/analytics", timeout=20)
        assert r.status_code == 403

    def test_owner_forbidden_gyms(self, owner_headers):
        r = owner_headers.get(f"{BASE}/api/admin/gyms", timeout=20)
        assert r.status_code == 403

    def test_unauth_analytics(self):
        r = requests.get(f"{BASE}/api/admin/analytics", timeout=20)
        assert r.status_code == 401


# --- ANALYTICS SHAPE + INTERNAL CONSISTENCY --------------------------------
class TestAnalytics:
    @pytest.fixture(scope="class")
    def payload(self, sa_headers):
        r = sa_headers.get(f"{BASE}/api/admin/analytics", timeout=30)
        assert r.status_code == 200, r.text
        return r.json()

    def test_top_level_keys(self, payload):
        for k in ("kpis", "revenue", "series", "funnel", "trials", "payments", "usage", "currency"):
            assert k in payload, f"missing {k}"

    def test_kpis_shape(self, payload):
        k = payload["kpis"]
        for key in ("mrr", "arr", "arpu", "total_customers", "paying", "trial", "expired",
                    "cancelled", "new_this_month", "signup_growth", "retention_rate",
                    "churn_rate", "trial_to_paid", "avg_lifetime_months"):
            assert key in k, f"kpi missing {key}"

    def test_mrr_equals_paying_times_price(self, payload, sa_headers):
        s = sa_headers.get(f"{BASE}/api/admin/settings", timeout=20).json()
        price = int(s.get("plan_price_inr") or 999)
        k = payload["kpis"]
        assert k["mrr"] == k["paying"] * price, f'mrr {k["mrr"]} != paying {k["paying"]} * price {price}'
        assert k["arr"] == k["mrr"] * 12

    def test_arpu(self, payload):
        k = payload["kpis"]
        expected = round(k["mrr"] / k["paying"]) if k["paying"] else 0
        assert k["arpu"] == expected

    def test_retention_vs_churn(self, payload):
        k = payload["kpis"]
        assert k["retention_rate"] == round(100 - k["churn_rate"], 1)

    def test_revenue_lifetime_matches_mrr_arr(self, payload):
        r = payload["revenue"]
        assert r["current_mrr"] == payload["kpis"]["mrr"]
        assert r["projected_arr"] == payload["kpis"]["arr"]
        assert isinstance(r["lifetime"], (int, float))
        assert r["lifetime"] >= 0

    def test_series_is_12_points(self, payload):
        s = payload["series"]
        assert len(s) == 12
        for pt in s:
            for key in ("month", "revenue", "new_customers", "total_customers"):
                assert key in pt
        # total_customers monotonically non-decreasing
        totals = [pt["total_customers"] for pt in s]
        assert totals == sorted(totals), "total_customers should be monotonically non-decreasing"

    def test_payments_success_rate(self, payload):
        p = payload["payments"]
        s, f = p["successful"], p["failed"]
        expected = round(100 * s / (s + f), 1) if (s + f) else 100.0
        assert p["success_rate"] == expected

    def test_usage_fields(self, payload):
        u = payload["usage"]
        for key in ("dau", "wau", "mau", "total_members", "members_this_month", "member_payments"):
            assert key in u
        assert u["dau"] <= u["wau"] <= u["mau"]

    def test_trials_fields(self, payload):
        t = payload["trials"]
        for key in ("ending_today", "ending_3d", "ending_7d", "active"):
            assert key in t
        assert t["ending_today"] <= t["ending_3d"] <= t["ending_7d"]


# --- GYMS LIST + FILTERS + HEALTH -------------------------------------------
class TestGyms:
    @pytest.fixture(scope="class")
    def gyms(self, sa_headers):
        r = sa_headers.get(f"{BASE}/api/admin/gyms", timeout=30)
        assert r.status_code == 200, r.text
        return r.json()

    def test_rows_shape(self, gyms):
        assert isinstance(gyms, list)
        assert len(gyms) >= 1
        g = gyms[0]
        for key in ("id", "name", "subscription", "health", "health_score",
                    "monthly_revenue", "member_count", "last_activity_days"):
            assert key in g, f"gym row missing {key}"
        assert g["subscription"]["status"] in ("trial", "active", "expired", "payment_due", "cancelled")
        assert g["health"] in ("healthy", "at_risk", "high_risk", "churned")
        assert 0 <= g["health_score"] <= 100

    def test_monthly_revenue_rule(self, gyms):
        for g in gyms:
            if g["subscription"]["status"] != "active":
                assert g["monthly_revenue"] == 0, f'{g["name"]} inactive but revenue {g["monthly_revenue"]}'

    def test_cancelled_is_churned(self, gyms):
        for g in gyms:
            if g["subscription"]["status"] == "cancelled":
                assert g["health"] == "churned"

    def test_status_filter(self, sa_headers, gyms):
        statuses = {g["subscription"]["status"] for g in gyms}
        for s in statuses:
            r = sa_headers.get(f"{BASE}/api/admin/gyms?status={s}", timeout=20)
            assert r.status_code == 200
            rows = r.json()
            assert all(x["subscription"]["status"] == s for x in rows), f"status={s} returned mismatched rows"

    def test_health_filter(self, sa_headers, gyms):
        healths = {g["health"] for g in gyms}
        for h in healths:
            r = sa_headers.get(f"{BASE}/api/admin/gyms?health={h}", timeout=20)
            assert r.status_code == 200
            rows = r.json()
            assert all(x["health"] == h for x in rows), f"health={h} returned mismatched rows"

    def test_analytics_paying_matches_gyms_active(self, sa_headers, gyms):
        r = sa_headers.get(f"{BASE}/api/admin/analytics", timeout=20).json()
        active = sum(1 for g in gyms if g["subscription"]["status"] == "active")
        assert r["kpis"]["paying"] == active, f'paying {r["kpis"]["paying"]} != active-gyms {active}'
        trial = sum(1 for g in gyms if g["subscription"]["status"] == "trial")
        assert r["kpis"]["trial"] == trial


# --- SETTINGS: plan price updates MRR --------------------------------------
class TestPriceAffectsMRR:
    def test_change_price_updates_mrr(self, sa_headers):
        orig = sa_headers.get(f"{BASE}/api/admin/settings", timeout=20).json()
        original_price = int(orig.get("plan_price_inr") or 999)
        try:
            new_price = original_price + 100
            r = sa_headers.put(f"{BASE}/api/admin/settings",
                             json={"plan_price_inr": new_price}, timeout=20)
            assert r.status_code == 200
            a = sa_headers.get(f"{BASE}/api/admin/analytics", timeout=20).json()
            assert a["kpis"]["mrr"] == a["kpis"]["paying"] * new_price
        finally:
            sa_headers.put(f"{BASE}/api/admin/settings",
                         json={"plan_price_inr": original_price}, timeout=20)


# --- AUDIT LOGS regression --------------------------------------------------
class TestAudit:
    def test_audit_logs(self, sa_headers):
        r = sa_headers.get(f"{BASE}/api/admin/audit-logs", timeout=20)
        assert r.status_code == 200
        logs = r.json()
        assert isinstance(logs, list)
