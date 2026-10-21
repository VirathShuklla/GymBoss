# GymBoss_VVO — Self-Hosting, Payments & Store Build Guide

This guide covers running GymBoss_VVO on **your own infrastructure**. Nothing here needs Emergent.
Components (one backend, one database, one login system, one entitlement record per gym):

| Component | Source | Suggested host |
|---|---|---|
| Website + web app + `/m` mobile web | `frontend/` (React, CRA + craco) | `https://gymboss.in` |
| Billing portal | same `frontend/` build, route `/billing` | `https://payments.gymboss.in` (same build, `REACT_APP_PORTAL_HOST`) |
| API | `backend/` (FastAPI, Python 3.11) | `https://gymboss.in/api` (reverse proxy) or `https://api.gymboss.in` |
| Database | MongoDB 6+/7 (Atlas or self-managed) | private network |
| Android app | `frontend/android/` (Capacitor 7, Android Studio) | Google Play |
| iOS app | `frontend/ios/` (Capacitor 7, Xcode) | Apple App Store |

---

## 1. Backend

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in every value (see table below)
python -m scripts.migrate   # creates all MongoDB indexes (idempotent)
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 2
```
Run it under systemd, supervisor or Docker. Put Nginx/Caddy in front for HTTPS.

**Important:** `pip install -r requirements.txt` includes `emergentintegrations`, served from Emergent's private index. The self-hosted code doesn't use it. Remove that line, or install with `--extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/`.

### Environment variables (`backend/.env`)
| Key | Purpose |
|---|---|
| `MONGO_URL`, `DB_NAME` | MongoDB connection |
| `JWT_SECRET` | 64-char random secret. Changing it logs everyone out |
| `FRONTEND_URL` | Public site origin. Used for CORS and password-reset links (must be `https://`) |
| `PORTAL_URL` | Billing portal origin (added to CORS) |
| `CORS_ORIGINS` | Extra comma-separated origins. Include `capacitor://localhost,https://localhost` for the store apps. `*` is ignored |
| `COOKIE_DOMAIN` | `.gymboss.in`, so one login works on `gymboss.in` **and** `payments.gymboss.in` |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay API keys. Super Admin → Settings can override them at runtime (stored in DB) |
| `RAZORPAY_WEBHOOK_SECRET` | **Required.** Webhooks are rejected (503) without it |
| `CRON_SECRET` | Protects `POST /api/internal/billing/reconcile` |
| `STORAGE_BACKEND` | `s3` (any S3-compatible store: AWS S3, Cloudflare R2, DigitalOcean Spaces, self-hosted MinIO) or `emergent` (preview only) |
| `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | AWS S3 / Cloudflare R2 / DigitalOcean Spaces (set `S3_ENDPOINT_URL` for non-AWS) |
| `EMAIL_PROVIDER` + `SMTP_HOST/PORT/USER/PASSWORD/FROM`, `EMAIL_FROM_NAME` | Password-reset email via any SMTP (Zoho, SES, Gmail Workspace) |
| `SUPER_ADMIN_USERNAME/PASSWORD/EMAIL` | Creates the BuildVVO super admin once (required, no defaults, password ≥10 chars; never reset on restart) |
| `TRUSTED_PROXIES` | Comma-separated IPs of your reverse proxies (e.g. `127.0.0.1`), so client IPs from X-Forwarded-For are trusted only from them |
| `SEED_DEMO` | `false` in production, so the demo gym isn't created |

## 2. Frontend (website, web app, `/m`, billing portal)

```bash
cd frontend
cp .env.example .env   # REACT_APP_BACKEND_URL=https://gymboss.in (origin that serves /api)
yarn install
yarn build             # static files in frontend/build
```
Serve `build/` from any static host (Nginx, Cloudflare Pages, Netlify, S3+CloudFront) with SPA fallback (every unknown path → `index.html`).

**Billing portal:** deploy the **same** `build/` to `payments.gymboss.in`, built with `REACT_APP_PORTAL_HOST=payments.gymboss.in` and `REACT_APP_APP_URL=https://gymboss.in/app`. Visiting the portal root opens `/billing`, and login redirects back to it.

**Remove Emergent preview scripts:** `frontend/public/index.html` contains an Emergent preview analytics snippet (`ap.emergent.sh`). Delete that `<script>` block before production.

### Example Nginx (single domain, API behind `/api`)
```nginx
server {
  server_name gymboss.in www.gymboss.in;
  root /var/www/gymboss/build;
  location /api/ { proxy_pass http://127.0.0.1:8001; proxy_set_header Host $host; proxy_set_header X-Forwarded-Proto $scheme; }
  location /iclock/ { proxy_pass http://127.0.0.1:8001; }   # biometric ADMS devices
  location / { try_files $uri /index.html; }
}
server {
  server_name payments.gymboss.in;
  root /var/www/gymboss/build-portal;
  location /api/ { proxy_pass http://127.0.0.1:8001; }
  location / { try_files $uri /index.html; }
}
```
## 3. DNS & HTTPS
- `A`/`AAAA` records for `gymboss.in`, `www`, and `payments` point to your server (or a CNAME to your static host).
- HTTPS: `certbot --nginx -d gymboss.in -d www.gymboss.in -d payments.gymboss.in`, or use your host's managed TLS. Cookies are `Secure; SameSite=None`, so **HTTPS is mandatory**.

## 4. Razorpay (subscriptions, ₹999/month, 10-day free trial)
1. Razorpay Dashboard → Settings → API Keys: put the keys in `.env` (or Super Admin → Settings).
2. Enable **Subscriptions**. For UPI AutoPay, ask Razorpay to enable recurring UPI on your account.
3. **Webhooks** → Add `https://gymboss.in/api/webhooks/razorpay`. Set a secret (same as `RAZORPAY_WEBHOOK_SECRET`) and enable these events: `subscription.authenticated, subscription.activated, subscription.charged, subscription.pending, subscription.halted, subscription.paused, subscription.resumed, subscription.cancelled, subscription.completed, subscription.updated, payment.captured, payment.failed`.
4. **Daily reconciliation** (catches missed webhooks): add one cron entry:
   ```cron
   15 3 * * * cd /srv/gymboss/backend && .venv/bin/python -m scripts.reconcile >> /var/log/gymboss-reconcile.log 2>&1
   ```
   or call `curl -X POST https://gymboss.in/api/internal/billing/reconcile -H "X-Cron-Secret: $CRON_SECRET"`. Super Admins can also trigger `POST /api/admin/billing/reconcile`.
5. Plans and prices are managed in Super Admin → Pricing (default Monthly ₹999). The Razorpay plan objects are created and cached automatically per key.

### How payment sync works (`backend/billing_sync.py`)
- **Verification:**
  - Checkout responses are HMAC-verified (`/subscription/verify`, `/subscription/autodebit/verify`).
  - Webhooks are HMAC-verified against `RAZORPAY_WEBHOOK_SECRET`.
- **Duplicate protection:**
  - Each webhook `X-Razorpay-Event-Id` is stored once (`webhook_events`, unique, 45-day TTL).
  - Each Razorpay `payment_id` extends access **exactly once** (`subscription_ledger`, unique). Checkout verify, `subscription.activated`, `subscription.charged` and reconciliation can all report the same payment safely.
- **Renewals:** `subscription.charged` → a paid row in `subscription_payments` (invoice downloadable) and access extended by the plan period.
- **Failed payments:** `subscription.pending`/`halted` → `billing_issue` flag, a failed row and a retry prompt in the UI. One-time order `payment.failed` → the row is marked failed. When the paid period ends without payment, the gym becomes read-only (`payment_due`); data is never deleted.
- **Cancellation:** from the portal/app (`/subscription/autodebit/cancel`) or Razorpay (`subscription.cancelled`). Access continues to the end of the paid period.

## 5. Store apps (Capacitor)
The store apps bundle the `/m` app. Built with `REACT_APP_STORE_BUILD=true`, they:
- send `X-Client-Platform: android_store|ios_store`;
- use Bearer tokens (stored on the device) instead of cookies;
- **contain no purchase UI**: no prices, Pay buttons, pricing pages or links to pay elsewhere;
- are blocked server-side (403) from creating Razorpay orders or subscriptions.

Existing subscribers just sign in, and their entitlement comes from the shared backend. See `memory/STORE_BILLING_COMPLIANCE.md` for the policy assessment.

```bash
cd frontend
REACT_APP_BACKEND_URL=https://gymboss.in ./scripts/build-mobile.sh   # build + cap sync (android/ & ios/)
```
### Android (Windows/macOS/Linux with Android Studio + JDK 17)
```bash
cd frontend/android
./gradlew assembleDebug      # test APK → app/build/outputs/apk/debug/app-debug.apk
./gradlew bundleRelease      # Play Store AAB (configure signing in Android Studio → Generate Signed Bundle)
```
- App id: `in.gymboss.app` (change in `capacitor.config.json` **before** the first upload).
- Camera permission is declared (QR attendance, member photos).
- Play Console: Data safety form, privacy policy URL `https://gymboss.in/privacy`, and in-app account deletion (Profile → Delete my account).
- If you also publish the PWABuilder/TWA build, fill `public/.well-known/assetlinks.json` with your package name and SHA-256 signing fingerprint.

### iOS (macOS + Xcode 16 + CocoaPods)
```bash
cd frontend && npx cap sync ios && cd ios/App && pod install && open App.xcworkspace
```
Set the Team and Bundle ID, then Product → Archive → Distribute. Camera and photo usage descriptions are already in `Info.plist`.

**App Review notes (suggested):**
> "GymBoss_VVO is business management software sold by BuildVVO Technologies to gym businesses for use by their owners and staff (multi-user organisation accounts). Subscriptions are purchased outside the app; the app contains no purchase UI or links. Guideline 3.1.3(c)/(b). Demo account: …"

## 6. Database migration from the preview
```bash
mongodump --uri "$PREVIEW_MONGO_URL" --db "$PREVIEW_DB" --out dump/
mongorestore --uri "$PROD_MONGO_URL" --nsFrom "$PREVIEW_DB.*" --nsTo "gymboss_prod.*" dump/
cd backend && python -m scripts.migrate
```
Uploaded files in Emergent object storage aren't included in the dump. Re-upload them, or start fresh with `STORAGE_BACKEND=s3`.

## 7. What is verified vs. unverified (preview environment)
See `memory/TEST_LOG.md` for the actual tests run. Not verifiable here:
- Android/iOS **native compilation**: no JDK/Android SDK, macOS or Xcode in this environment. The projects are generated and synced, but APK/AAB/IPA were **not built**.
- Real Razorpay renewals over time, live-mode payments and UPI AutoPay mandates (only test mode is available, and recurring charges can't be time-travelled).
- SMTP, S3 and local storage backends (code paths are present; the preview uses Emergent storage and email).
- Biometric devices (need real hardware).
