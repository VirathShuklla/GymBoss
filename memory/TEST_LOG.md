# GymBoss_VVO — Test Log (June 2026, Emergent preview, Razorpay TEST mode)

## Automated suites run (backend, against live preview API + MongoDB)
`pytest -n 0 tests/test_milestones.py tests/test_iter15_attendance_pricing.py tests/test_iter18_delete_account_staff_email.py tests/test_iter19_staff_priv_delete_lock.py tests/test_iter20_billing_sync.py` → **152 passed**.

The suites cover registration, login, lockout, forgot/reset/change password, staff roles and login-email changes, account deletion, plans, members (create/renew/freeze), payments and receipts, attendance check-in, trial read-only enforcement, and pricing. Billing sync coverage:
- signed webhooks, with 400 for bad or missing signatures
- event-id dedupe
- activated + charged for the same payment = one extension
- renewal extends access again
- pending/halted → billing issue, then charged clears it
- cancellation
- one-time order capture/failure
- checkout verify with a bad signature (400) or an unknown order (404)
- invoice PDF access control
- cron and super-admin reconcile auth
- store-platform 403 on purchase endpoints
- Bearer tokens and JSON refresh for store clients
- CORS for `capacitor://localhost`

Removed `test_iter9_subscription.py`: it created real Razorpay test subscriptions on the demo org and its assumptions are superseded by iteration 20.

## Browser tests (testing agent, Playwright) — iterations 17–20
- Billing portal: login redirect, plan picker, Pay → Razorpay test checkout opens, renewal disclosure, cancel auto-renewal, invoice download, staff without permission.
- Store mode (`?app=1`): no prices, Pay buttons or plan picker; neutral trial/expired banners; `/`, `/billing`, `/pricing`, `/app/subscription` redirect into `/m`. Web behaviour is restored when the flag is cleared.
- Web and mobile regression: login, members, attendance, payments, profile, change password, delete account, staff edit.

## Manual checks by the agent
- Razorpay test checkout opened for the monthly plan (iteration 19 fix: stale plan/subscription IDs after a key change; yearly `total_count`).
- `scripts/build-mobile.sh`: React store bundle built, and the Capacitor `android/` and `ios/` projects generated and synced.

## NOT verified (environment limits)
- **No APK/AAB/IPA built**: this environment has no JDK/Android SDK and no macOS/Xcode/CocoaPods. Build locally per DEPLOYMENT.md §5.
- No real Razorpay payment completed end-to-end. Renewals and failures were simulated with signed webhooks; live mode and UPI AutoPay mandates are untested.
- Not exercised in the preview: SMTP email, S3 storage backend, the `COOKIE_DOMAIN` cross-subdomain login, the `payments.gymboss.in` host redirect.
- Native-device camera (QR scanning) inside the Capacitor WebView, and biometric ADMS devices.
