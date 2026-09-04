"""Iteration 9 focused tests: subscription payload hardening + admin settings razorpay key validation."""
import pytest
import requests

from conftest import API


# ---------------- GET /api/subscription (demo owner) ----------------
class TestSubscriptionPayload:
    def test_subscription_payload(self, demo_client):
        r = demo_client.get(f"{API}/subscription")
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert set(["subscription", "payments", "razorpay_configured", "autodebit"]).issubset(data.keys())
        assert data["razorpay_configured"] is False, "expected false because stored key_id is invalid"
        sub = data["subscription"]
        assert sub["plan_price_inr"] == 999, sub
        assert sub["status"] in ("trial", "active", "expired", "payment_due", "cancelled")
        assert isinstance(data["payments"], list)
        for p in data["payments"]:
            assert "_id" not in p
        assert data["autodebit"] is None or isinstance(data["autodebit"], dict)

    def test_autodebit_start_fails_gracefully(self, demo_client):
        """Razorpay keys are invalid -> must not 500; expect 502/503 with a clear message."""
        r = demo_client.post(f"{API}/subscription/autodebit/start")
        assert r.status_code in (502, 503), f"got {r.status_code}: {r.text[:300]}"
        # NOTE: 502 responses are replaced by the edge proxy with an HTML error page,
        # so the JSON detail message never reaches the browser (reported as a minor issue).
        if "application/json" in r.headers.get("content-type", ""):
            assert "detail" in r.json()

    def test_autodebit_cancel_no_subscription(self, demo_client):
        r = demo_client.post(f"{API}/subscription/autodebit/cancel")
        assert r.status_code == 404, r.text[:300]
        assert "No active auto-debit" in r.json().get("detail", "")

    def test_subscription_requires_auth(self, client):
        r = client.get(f"{API}/subscription")
        assert r.status_code in (401, 403)


# ---------------- PUT /api/admin/settings razorpay_key_id validation ----------------
@pytest.fixture(scope="function")
def admin_client(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=creds["super_admin"])
    if r.status_code != 200:
        pytest.fail(f"Super admin login failed {r.status_code}: {r.text[:300]}")
    yield s
    s.close()


class TestAdminSettingsRazorpayValidation:
    @pytest.mark.parametrize("bad", ["https://example.com/link", "abc123", "rzp_FAKE", " key_id "])
    def test_invalid_key_rejected(self, admin_client, bad):
        before = admin_client.get(f"{API}/admin/settings").json()
        r = admin_client.put(f"{API}/admin/settings", json={"razorpay_key_id": bad})
        assert r.status_code == 422, f"{bad!r} -> {r.status_code}: {r.text[:200]}"
        detail = r.json().get("detail", "")
        assert "rzp_test_" in str(detail), detail
        after = admin_client.get(f"{API}/admin/settings").json()
        assert after.get("razorpay_key_id") == before.get("razorpay_key_id"), "settings must not change on rejection"

    def test_plan_price_validation(self, admin_client):
        r = admin_client.put(f"{API}/admin/settings", json={"plan_price_inr": 0})
        assert r.status_code == 422, r.text[:200]

    def test_settings_get_no_mongo_id(self, admin_client):
        r = admin_client.get(f"{API}/admin/settings")
        assert r.status_code == 200
        assert "_id" not in r.json()

    def test_settings_requires_super_admin(self, demo_client):
        r = demo_client.put(f"{API}/admin/settings", json={"razorpay_key_id": "abc"})
        assert r.status_code in (401, 403), r.text[:200]


# ---------------- Regression smoke on core org endpoints ----------------
class TestRegressionSmoke:
    @pytest.mark.parametrize("path", [
        "/auth/me", "/dashboard/summary", "/members?limit=5", "/payments?limit=5",
        "/outlets", "/plans", "/public/config",
    ])
    def test_core_endpoints_ok(self, demo_client, path):
        r = demo_client.get(f"{API}{path}")
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"
