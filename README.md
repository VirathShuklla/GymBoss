# GymBoss_VVO

**The modern gym operating system.** A multi-tenant SaaS for gym owners, built by **BuildVVO Technologies Private Limited** (India).

One backend and one database power:
- the marketing website,
- the web dashboard,
- the mobile app (`/m`, also packaged as Android and iOS apps),
- the billing portal,
- the BuildVVO Super Admin console.

| | |
|---|---|
| Website | `/` (marketing landing page) |
| Web app | `/app/dashboard` (login required) |
| Mobile app | `/m` (PWA, and the Capacitor Android/iOS apps) |
| Billing portal | `/billing` (intended for `payments.gymboss.in`) |
| Super Admin | `/superadmin` (BuildVVO staff only) |
| Trial / price | 10-day free trial, no card · ₹999/month (Quarterly/Yearly set by Super Admin) |
| Public check-in | `/checkin/{token}` (QR attendance page, no login) |

### Login credentials (preview / demo data)
| Account | Login ID | Password | Where |
|---|---|---|---|
| **Super Admin** (BuildVVO) | `GymBoss` | `GymBoss@2026` | `/login` → `/superadmin` |
| **Demo gym owner** | `demo@gymbossvvo.in` | `Demo@2026` | `/login` → `/app/dashboard`, or `/m` |

> In production, set `SUPER_ADMIN_PASSWORD` to a strong password and `SEED_DEMO=false`.

---

## Table of Contents
1. [Project Status: Done vs. To Do](#project-status-done-vs-to-do)
2. [Feature Overview](#feature-overview)
3. [Tech Stack & Codebase](#tech-stack)
4. [API Reference](#api-reference-summary)
5. [Step-by-step: Host the Website, API & Billing Portal](#step-by-step-host-the-website-api--billing-portal)
6. [Step-by-step: Razorpay Setup](#step-by-step-razorpay-setup)
7. [Step-by-step: Build the Android APK / AAB](#step-by-step-build-the-android-apk--aab)
8. [Step-by-step: Publish on Google Play](#step-by-step-publish-on-google-play)
9. [Step-by-step: Build & Publish on the Apple App Store](#step-by-step-build--publish-on-the-apple-app-store)
10. [Store Payment Rules (why the apps don't sell)](#store-payment-rules-why-the-apps-dont-sell)
11. [Testing](#testing)
12. [Go-Live Checklist](#go-live-checklist)

---

## Project Status: Done vs. To Do

### ✅ Done (built and tested in the development preview)
- Website, web dashboard, mobile app `/m`, Super Admin, all sharing one FastAPI backend and MongoDB.
- Members, plans, payments, PDF receipts, attendance (QR + biometric ADMS + manual), enquiries, expenses, outlets, staff permissions, finance, reports and exports.
- Auth:
  - register, login and lockout;
  - forgot, reset and change password;
  - delete account;
  - owner can change a staff member's login email.
- 10-day trial, then read-only (data is never deleted).
- Razorpay subscriptions with HMAC verification, webhooks, renewals, failed payments, cancellation, duplicate protection and daily reconciliation.
- Billing portal with history and invoice PDFs.
- Store-compliant app mode (no purchase UI in store builds) plus server-side blocking.
- Privacy and Terms pages, in-app account deletion and an `assetlinks.json` placeholder.
- Capacitor 7 Android Studio project (`frontend/android`) and Xcode project (`frontend/ios`), camera permissions, and a build script.
- Self-hosting support:
  - all URLs, keys, origins and domains come from env variables;
  - S3-compatible storage and SMTP email;
  - backend `Dockerfile`, index migration script and `.env.example` files.

### ⏳ To do (by you; these can't be done inside the development environment)
| # | Task | Where |
|---|---|---|
| 1 | Buy hosting, point DNS, enable HTTPS | [Hosting guide](#step-by-step-host-the-website-api--billing-portal) |
| 2 | Create a production MongoDB (e.g. Atlas, Mumbai region) | Hosting guide, step 1 |
| 3 | Create an S3/R2 bucket and SMTP mailbox | Hosting guide, step 2 |
| 4 | Activate Razorpay **Live Mode** (KYC), add the webhook, enable UPI AutoPay | [Razorpay guide](#step-by-step-razorpay-setup) |
| 5 | Build the APK/AAB on a PC with Android Studio | [Android guide](#step-by-step-build-the-android-apk--aab) |
| 6 | Build the iOS app on a Mac with Xcode | [iOS guide](#step-by-step-build--publish-on-the-apple-app-store) |
| 7 | Google Play Console ($25 one-time) and Apple Developer Program ($99/year) accounts | Store guides |
| 8 | App icons, screenshots, store listing text, Data Safety / Privacy Nutrition forms | Store guides |
| 9 | Remove the Emergent preview analytics `<script>` (`ap.emergent.sh`) from `frontend/public/index.html` | Go-live checklist |
| 10 | Fill `frontend/public/.well-known/assetlinks.json` (only if you also ship a TWA/PWABuilder app) | Android guide |

### ⚠️ Not verified in the development environment
- APK/AAB/IPA compilation: there is no Android SDK, JDK or Xcode in the dev environment. The projects are generated and synced but have **not been compiled**.
- A real Razorpay payment end-to-end, Live Mode and UPI AutoPay mandates. Renewals and failures were simulated with signed webhooks.
- SMTP email, S3 storage, cross-subdomain login (`COOKIE_DOMAIN`), the `payments.gymboss.in` host redirect, and native-device camera scanning.
- Biometric devices (need real hardware).

### 🗺️ Roadmap (optional, later)
- **Phase 2:** Google Play Billing + India *user choice billing* (lets Android users subscribe inside the app, with Razorpay as an alternative).
- Apple In-App Purchase, only if Apple rejects the business-app exception.
- One-step signup, Revenue & Profit dashboard, renewal reminders.

---

## Feature Overview

### 1. Public Marketing Website
- Landing page: sticky navbar (Features / How It Works / Pricing / FAQ anchors), hero with live-style dashboard mockup, 9 feature cards, 3-step "How It Works", pricing card (10-day free trial → configurable ₹/month), FAQ accordion, final CTA band, dark footer with dynamic copyright year
- Floating WhatsApp contact button (number configurable by super admin; falls back to FAQ anchor when unset)
- Pricing section shows **Monthly / Quarterly / Yearly** cards with strike-through offer prices and offer labels. All pricing copy comes from the Super Admin plan settings: change it once and the landing page, web app, mobile app and Razorpay checkout all update
- No fake testimonials, no fake store badges (app-store URLs configurable; shows "coming soon" until set)

### 2. Authentication & Onboarding
- 3-step registration: Account Info → Contact & Security (+91 phone, password show/hide, validation) → Gym Setup (gym name + first outlet). Creates user + organisation + outlet + default batches + 10-day trial in one shot, logs the user in
- Login by **email, mobile number, or username** (super admin uses a username)
- Forgot/reset password with single-use, sha256-hashed, 1-hour-expiry tokens; anti-enumeration generic responses
- Brute-force lockout: 5 attempts per IP+identifier / 10 per identifier per 15 min (proxy-aware via `X-Forwarded-For`)
- JWT auth: 30-min access + 7-day refresh tokens in `HttpOnly; Secure; SameSite=None` cookies (shareable across subdomains via `COOKIE_DOMAIN`). Store apps get Bearer tokens instead. `token_version` invalidates all sessions on password reset/change
- **Change password** (web Profile + mobile Profile; other devices are signed out) and **Forgot password** links on web and mobile login
- **Delete my account** (web + mobile Profile, password + typing DELETE): an owner permanently erases the whole gym and cancels any Razorpay auto-renewal; a staff member removes only their own login (Play Store / App Store requirement)
- Trial-expired paywall: data is never deleted; the app locks to Subscription / Support / Profile / Settings until payment

### 3. Dashboard
- Real DB-computed KPIs (IST day boundaries): Today's Collection (with online/cash split), Admissions, Renewals, Due Paid, Enquiries, PT/Service/Product sales
- Secondary metrics: Active Members, Total Members, Due Members, Expiry Today, Expiry in 1–3 Days, Birthdays Today, Today's Attendance
- Quick actions (Add Member / Record Payment / Check In / Add Enquiry), recent transactions table, dismissible onboarding checklist
- Light / Dark / System theme (persisted), collapsible sidebar, outlet switcher, trial badge with days-left + Upgrade Now

### 4. Members
- Table with search (scoped by Name / Phone / Member ID), filters (outlet, status, plan, gender, batch), pagination, CSV export
- **3-step Add Member modal**:
  - *Step 1 — Basic Details*: profile photo upload (object storage), read-only auto-generated Member ID, name, +91 phone, gender, batch dropdown (existing batches + "New batch")
  - *Step 2 — Optional*: email, height, weight, address, notes, DOB (calendar picker), attachment upload (image/PDF)
  - *Step 3 — Membership*: joining/payment dates, plan select, admission amount, discount, payment mode, amount collected + **live payment summary** (`Payable = Plan + Admission − Discount`, `Due = Payable − Collected`) with automatic **Paid / Partially Paid / Due** status and auto start/expiry from plan duration
- Member detail drawer with action sheet: Freeze (auto-extends expiry) / Unfreeze, Show More Info, Edit, Delete (confirmed, soft-delete + audit), Attendance History, Renew Membership, Record Payment, Send Payment Reminder (WhatsApp templates), Transaction History, printable Receipt
- WhatsApp templates: welcome, payment reminder, expiring, expired, birthday, follow-up, custom — opened via click-to-WhatsApp (`wa.me`)

### 5. Plans & Catalogue
- Tabs: Membership / PT / Service / Product
- Single category-driven form — the **Category dropdown decides the tab**; conditional fields (duration for Membership/PT, sessions+trainer for PT, inventory for Product)
- Edit / archive with confirmation

### 6. Mobile App (installable PWA, `/m`)
- A separate, native-style mobile experience sharing the same backend and accounts (violet branding, light/dark)
- Onboarding carousel → welcome → login/register → Home (today's collection, KPIs, getting-started checklist, recent transactions), Manage (Members, Plans, Enquiries, Expenses, Outlets, Staff — plus **Finance + Reports** for finance-enabled users), Profile (subscription + Razorpay pay button, theme, logout)
- Members: debounced search + **Active / Expiring / Due** filter chips + member actions (renew, record payment, WhatsApp reminder, and WhatsApp receipt after a payment)
- Bottom navigation: **Home · Attendance · Manage · Profile**. Home has 4 quick actions (Add Member, Payment, Check-in, Renewals) and tappable KPI tiles, including today's check-ins
- **Attendance tab**: "Inside the gym now" counter, QR Check-in sheet (show / share / download QR), Biometric sheet (setup guide, supported devices, contact, connected devices, auto-delete on expiry, connect a device, test punch), manual check-in, and today's member and staff lists
- Profile: plan picker (Monthly / Quarterly / Yearly) before paying with Razorpay
- After recording a payment: WhatsApp receipt text **and** share/download the **PDF receipt** (uses the phone's share sheet, so it can go straight to WhatsApp)
- Installable via `manifest.json` + service worker; `start_url` is `/m`

### 7. Payments & Receipts
- Record payments against dues (Cash / UPI / Card / Bank Transfer / Other), filters, pagination
- Professional receipt modal (gym, member, plan, method, receipt no., outstanding) with Print, **Download PDF** and Send on WhatsApp
- **PDF receipts** generated on the server (`GET /api/payments/{id}/receipt.pdf`, reportlab, A5, gym-branded)
- Receipt opens automatically after recording a payment
- Edit or reverse a wrongly recorded payment (web and mobile); dues recalculate automatically

### 7b. Attendance (`/app/attendance` and `/m/attendance`)
Three ways to mark attendance. All of them use the same rule: **the first scan of the day is Punch In, the next is Punch Out** (scans less than 1 minute apart are ignored).

**QR check-in (no hardware)**
1. Open Attendance → *QR Check-in*. Each outlet has its own QR code.
2. Print it or share it, and put it at the entrance.
3. Members scan it with their phone camera, which opens `/checkin/{token}`. They enter their member ID (e.g. `IPF-1001`, or just `1001`) or their phone number.
4. Staff choose the **Staff** tab and enter their phone or email. Staff attendance is stored separately.
5. Expired or frozen members are refused with a clear "please renew at the front desk" message.
6. *Generate a new QR* invalidates the old printed code.

**Biometric (eSSL / ZKTeco over the ADMS push protocol)**
1. Attendance → *Biometric* → *Connect a Device*: pick the model (eSSL X990, K30, K40, MB20, MB160, MB460, or another eSSL/ZKTeco ADMS model) and enter the serial number and a name.
2. On the device: Menu → COMM → Cloud Server Setting (ADMS). Turn on Enable Domain Name, set the server address to your app domain and port 443 (or 80), and save.
3. Enrol each member on the device with **User ID = the number in their member code** (`IPF-1001` → `1001`). The Setup Guide lists every member's device ID.
4. The device polls `GET /iclock/getrequest` and pushes punches to `POST /iclock/cdata?table=ATTLOG`. These are served at both `/iclock/*` and `/api/iclock/*`. The device shows **Online** when it has polled in the last 5 minutes.
5. **Auto delete access on expiry** (per-device toggle): the server sends `DATA DELETE USERINFO PIN=…` for expired members. They stay in the app; re-enrol them after renewal.
6. **Test punch** simulates a fingerprint scan through the same code path, so you can check everything without a machine.

**Manual**: search a member and check them in or out.

The dashboard shows today's attendance count, and Super Admin shows platform-wide check-ins and device counts.

### 8. Enquiries (CRM)
- Lead capture with source (Walk-In/Instagram/Facebook/Google/Website/Referral/WhatsApp), statuses (New → Converted/Lost), follow-up scheduling with history
- One-click **Convert to Member** (pre-fills the member form), per-lead WhatsApp action

### 9. Expenses
- Month/year/category/outlet filters, running total, CRUD with confirmations

### 10. Outlets
- Multi-branch management: simplified add form (name + address), disable/enable (primary outlet protected), outlet switcher scopes the whole app

### 11. Staff & Permissions
- Staff form: Type (Staff/Trainer/Manager/Admin/Sales), outlet, **Permission (View / View & Edit / Full Access)**, **Enable Finance Page** toggle, +91 phone, email, optional login password
- Permission enforced **backend-side**: `View` = read-only (403 on writes, write buttons hidden); finance pages (Finance/Reports/Export) hidden + 403 unless owner or finance-enabled
- Disable/enable staff (blocks login + existing sessions), delete staff (removes login too)
- The **owner** can change a staff member's **login email** and set a new password (web Staff page + mobile Manage → Staff). Only the owner can change roles, login emails or passwords

### 12. Finance, Reports & Exports
- Finance: date ranges (today/week/month/year/custom), Revenue / Expenses / Net / Outstanding dues, collections-by-method, expenses-by-category, transaction table
- Reports: revenue trend (6-month chart), member growth, outstanding dues, membership expiry (30 days), enquiry conversion (status + source)
- Export Center: CSV download for members, payments, attendance, expenses, enquiries, staff, plans — outlet-scoped

### 13. SaaS Subscription (Gym → BuildVVO)
- Trial (10 days) → active → payment_due/expired states, all backend-derived (never client-side)
- Plans: **Monthly (1 month), Quarterly (3 months), Yearly (12 months)**. The gym owner picks one on the web Subscription page or in mobile Profile, and access is extended by 30 × months days
- Razorpay auto-debit subscription (one Razorpay plan per app plan, recreated automatically when the price changes) → checkout → HMAC signature verification; webhook endpoint for charged/halted/cancelled/captured/failed
- Payment history; honest "being configured" state until keys exist
- Separate from member payments — never mixed

### 14. BuildVVO Super Admin (`/superadmin`)
- **Light / Dark / System theme** toggle in the header
- Overview: MRR (multi-month plans spread per month), ARR, ARPU, paying customers, retention, churn, trial → paid, revenue and customer-growth charts, trial funnel, payment analytics, product usage (including check-ins and biometric devices), Action Required
- Customers table: owner, status, health (Healthy / At Risk / High Risk / Churned), MRR, members, last activity; detail dialog
- **Churn watchlist export**: "Export churn watchlist" (high risk) and "Incl. at-risk" download a CSV (`GET /api/admin/churn-export?health=high_risk|all_risk`) with gym, owner contact, status, health score, members and last activity, ready for a win-back campaign. Demo gyms are excluded
- Disable / reactivate gym accounts (data preserved, access blocked, audit-logged)
- **Platform Settings**: support WhatsApp number, support email, app-store URLs, **Subscription Plans & Offers** (price, offer price, offer label, and show/hide for Quarterly and Yearly; changes go live on the landing page, web app, mobile app and Razorpay checkout), **Razorpay Key ID / Secret / Webhook Secret** (DB settings override env)
- Audit log viewer (registrations, deletions, freezes, payments, admin actions)

### 15. File Storage
- Profile photos + attachments uploaded via `POST /api/uploads` and served back via authenticated, tenant-checked `GET /api/files/{id}`
- Storage backend set by `STORAGE_BACKEND`: `s3` (AWS S3 / Cloudflare R2 / DigitalOcean Spaces / MinIO) for self-hosting, `emergent` in the preview

---

### 16. Billing Portal (`/billing`, intended for `payments.gymboss.in`)
- A standalone page for gym owners and admins: subscription status, plan picker (Monthly ₹999 / Quarterly / Yearly), Razorpay auto-debit checkout, a clear renewal and cancellation notice, **Cancel auto-renewal**, payment history and **invoice PDF download**
- Uses the same backend, login and entitlement as the app. When hosted on `REACT_APP_PORTAL_HOST`, the root opens straight into billing, and login redirects back (`/login?next=/billing`)
- Staff without the owner or admin role see a "no permission" notice. The server enforces this too

### 17. Store-App Mode (Google Play / App Store compliance)
- Store builds (`REACT_APP_STORE_BUILD=true`, Capacitor, or a TWA opened with `?app=1` / `?src=play`) contain **no purchase UI**: no prices, Pay buttons, plan picker, upgrade CTAs, pricing pages or "pay on the website" wording
- `/`, `/pricing`, `/billing` and `/app/subscription` redirect into `/m`. Trial and expired banners become neutral messages
- Every request sends `X-Client-Platform: android_store|ios_store`, and the backend refuses to create Razorpay orders or subscriptions from store clients (403)
- Existing subscribers just sign in; their entitlement comes from the shared database. Policy assessment: `memory/STORE_BILLING_COMPLIANCE.md`

### 18. Razorpay Payment Synchronisation (`backend/billing_sync.py`)
- Checkout responses and webhooks are HMAC-verified. Webhooks are **rejected unless `RAZORPAY_WEBHOOK_SECRET` is set**
- **Duplicate protection**: each webhook event id is processed once, and each Razorpay payment id extends access **exactly once** (a ledger with a unique index). Checkout verify, `subscription.activated`, `subscription.charged` and reconciliation can all report the same payment safely
- Renewals (`subscription.charged`) add a paid row with an invoice and extend access by the plan period
- Failed payments (`subscription.pending`/`halted`, `payment.failed`) flag a billing issue, record a failed row and show a retry prompt. When the paid period ends unpaid, the gym becomes read-only and data is never deleted
- Cancellation (portal, app or Razorpay): access continues to the end of the paid period. Paused, resumed and updated events are handled too
- **Daily reconciliation** pulls subscription and order status from Razorpay and applies anything missed (`python -m scripts.reconcile`, or `POST /api/internal/billing/reconcile` with `X-Cron-Secret`)

### 19. Legal & Compliance Pages
- `/privacy` and `/terms` (BuildVVO Technologies Private Limited, India; account deletion section), linked from the footer, signup and mobile Profile
- `public/.well-known/assetlinks.json` placeholder for Android app links (fill in your package name + SHA-256)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 (CRA + craco), Tailwind CSS, shadcn/ui, lucide-react, recharts, sonner |
| Mobile | Installable PWA at `/m` (manifest + service worker), same React codebase & API |
| Backend | FastAPI (Python 3.11), Motor (async MongoDB), PyJWT, bcrypt, httpx |
| Database | MongoDB |
| Storage | Emergent object storage (`/objstore` proxy) |
| Billing | Razorpay (orders + HMAC verification + webhooks) |
| Fonts | Outfit (display), DM Sans (body), JetBrains Mono (numbers) |
| Theme | Violet `#7C3AED` + deep navy, full light/dark/system support |

---

## Codebase Structure

```
/app
├── backend/
│   ├── server.py          # App entry: auth (register/login/logout/refresh/me/forgot/reset),
│   │                      # public config, dashboard summary, onboarding, outlets list,
│   │                      # startup (indexes, seed migrations, super admin, demo data)
│   ├── deps.py            # Shared: db client, JWT, password hashing, auth dependencies
│   │                      # (get_current_user, get_org_user, require_write, require_manager,
│   │                      # require_finance_access, require_super_admin), subscription
│   │                      # derivation, member status helpers, counters, object storage,
│   │                      # plan price + Razorpay key resolution (settings → env)
│   ├── members.py         # Plans & catalogue, members (CRUD, freeze, renew), payments,
│   │                      # receipts, attendance, batches, next-code, file uploads
│   ├── ops.py             # Enquiries (+follow-ups), expenses, outlets, staff, gym profile,
│   │                      # user profile, support requests
│   ├── comms.py           # Announcements engine (kept server-side; UI module currently
│   │                      # removed per product decision)
│   ├── finance.py         # Finance summary/transactions, reports, CSV export center
│   ├── billing.py         # Subscription status, Razorpay order/verify, webhook
│   ├── admin.py           # Super admin: overview, gyms, disable/reactivate, platform
│   │                      # settings, audit logs
│   ├── requirements.txt
│   ├── .env               # Secrets & config (see below)
│   └── tests/             # 163 pytest tests (auth, milestones, iterations), cleanup helpers
│
├── frontend/
│   ├── public/index.html  # Title, fonts, favicon (no watermark)
│   ├── src/
│   │   ├── App.js         # Routes: landing, auth, /app/* (guarded), /superadmin
│   │   ├── index.css      # Design tokens (light/dark CSS vars), status badges
│   │   ├── lib/           # api.js (axios + refresh interceptor + apiError),
│   │   │                  # format.js (₹ INR, dd MMM yyyy), whatsapp.js (templates),
│   │   │                  # upload.js (file uploads)
│   │   ├── contexts/      # AuthContext (me/login/register/logout), ThemeContext
│   │   ├── components/
│   │   │   ├── marketing/ # Navbar, Hero, DashboardMockup, Features, HowItWorks,
│   │   │   │              # Pricing, Faq, FinalCta, Footer, FloatingWhatsApp
│   │   │   ├── app/       # ui.jsx (PageHeader, DataTable, StatusBadge, EmptyState,
│   │   │   │              # ConfirmDialog, DateField, MemberPicker, Pagination),
│   │   │   │              # MemberForm (3-step), MemberDrawer (action sheet),
│   │   │   │              # ReceiptModal
│   │   │   └── ui/        # shadcn components
│   │   ├── layouts/AppLayout.jsx   # Sidebar (trial badge, scoped nav), topbar, paywall
│   │   └── pages/
│   │       ├── Landing.jsx
│   │       ├── auth/      # Login, Register (3-step), ForgotPassword, ResetPassword
│   │       ├── app/       # Dashboard, Members, Plans, Attendance, Payments, Enquiries,
│   │       │              # Expenses, Outlets, Staff, Finance, Reports, ExportCenter,
│   │       │              # Settings, Subscription, Support, Profile, ComingSoon
│   │       └── SuperAdmin.jsx
│   └── package.json
│
├── memory/
│   ├── PRD.md             # Product requirements + milestone history + backlog
│   └── test_credentials.md
└── design_guidelines.json
```

---

## Data Model

All collections are tenant-scoped (`organisation_id`, often `outlet_id`); string UUIDs as `id` (no raw ObjectId leakage).

| Collection | Purpose |
|---|---|
| `users` | Owners, staff logins, super admin (username). Roles: `owner`, `admin`, `manager`, `receptionist`, `trainer`, `sales`, `staff`, `super_admin`. Fields: `permission` (view/manage/full), `finance_enabled`, `token_version`, `status` |
| `organisations` | Gyms. Holds `subscription` (status, trial/period dates, plan, amount), `onboarding`, `disabled` flag |
| `outlets` | Branches (`is_primary`, `status`) |
| `members` | Member profile + `member_code` (unique per org via counters), plan snapshot, `membership_start/expiry`, `due_amount`, `payable`, `payment_status`, `frozen_until`, `freeze_history[]`, photo/attachment URLs, soft-delete `deleted_at` |
| `plans` | Catalogue: `type` = membership/pt/service/product, duration, price, sessions, inventory |
| `payments` | Immutable member payment records (receipt_no, type, method, amount, payment_date) |
| `attendance` | Check-in/out records |
| `enquiries` | Leads with status, source, follow_ups[] |
| `expenses` | Expense records |
| `staff` | Staff profiles (linked `user_id` when login exists) |
| `batches` | Batch names per gym (auto-created on member save) |
| `announcements` | Bulk messaging engine records (module hidden from gyms for now) |
| `subscription_payments` | Gym → BuildVVO Razorpay orders/payments |
| `settings` | `platform` doc: support contact, store URLs, `plan_price_inr`, Razorpay keys |
| `files` | Object-storage metadata (tenant-scoped) |
| `counters` | Per-org sequences (member codes, receipts) |
| `audit_logs` | Actor, action, target, metadata, timestamp |
| `login_attempts`, `password_reset_tokens`, `password_reset_requests` | Auth security (TTL indexes) |

Key indexes: `users.email` (unique), `users.username` (unique), `(organisation_id, member_code)` **unique**, org-scoped indexes on members/payments/attendance, TTL on reset tokens & rate-limit records.

---

## Architecture: Tenancy, Auth, Permissions

- **Tenant isolation is server-side only.** Every query is scoped from the authenticated user's `organisation_id` claim — client-supplied org IDs are never trusted. Cross-tenant access returns 404/403 (verified by tests in both directions).
- **Permission model** (backend-enforced in `deps.py`):
  - `get_org_user` — any authenticated gym user (blocks disabled gyms/accounts)
  - `require_write` — blocks `permission: view` staff from mutations (only owner bypasses)
  - `require_manager` — owner/admin/manager (staff & outlet management)
  - `require_finance_access` — owner or staff with finance flag (Finance/Reports/Export)
  - `require_super_admin` — BuildVVO console only
- **Derived state, never stored manually**: membership status (Active/Expiring Soon/Expired/Frozen), days left, trial countdown, subscription status — all computed from authoritative records at read time.
- **Startup migrations** keep the seeded demo org upgrade-safe (plan-type backfill, staff-role casing, counter initialisation, batch/catalogue backfill).
- **Mobile-ready**: the same API supports cookie auth (web) and `Authorization: Bearer` (future Android/iOS apps share the same backend, database and business rules).

---

## Billing & Subscription

1. Registration starts a **10-day trial** (`trial_ends_at` on the org) — no card required.
2. Trial end → status `expired` → paywall screen (price shown from platform settings). Data is never deleted.
3. **Subscribe Now** → `POST /api/subscription/create-order` (Razorpay order, amount = platform price) → checkout.js → `POST /api/subscription/verify` (HMAC-SHA256 signature check) → subscription active for +30 days (stacks if paid early).
4. Webhook `POST /api/webhooks/razorpay` handles `payment.captured` / `payment.failed` idempotently.
5. Razorpay keys and price are managed in **Super Admin → Platform Settings** (DB), with env vars as fallback.
6. `payment_due` (active period lapsed) behaves like expired until the next payment.

---

---

## API Reference (summary)

All under `/api`. Auth via httpOnly cookies or `Authorization: Bearer`.

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register` · `POST /auth/login` · `POST /auth/logout` · `POST /auth/refresh` · `GET /auth/me` · `POST /auth/forgot-password` · `POST /auth/reset-password` · `POST /auth/change-password` · `POST /auth/delete-account` |
| Public | `GET /public/config` |
| Dashboard | `GET /dashboard/summary` · `GET /dashboard/recent-transactions` · `GET|PUT /onboarding` |
| Members | `GET|POST /members` · `GET /members/next-code` · `GET|PUT|DELETE /members/{id}` · `POST /members/{id}/freeze|unfreeze|renew` |
| Plans | `GET|POST /plans` · `PUT|DELETE /plans/{id}` |
| Payments | `GET|POST /payments` · `PUT|DELETE /payments/{id}` · `GET /payments/{id}/receipt` · `GET /payments/{id}/receipt.pdf` |
| Attendance | `POST /attendance/check-in` · `POST /attendance/{id}/check-out` · `GET /attendance` · `GET /attendance/history` · `GET /attendance/summary` · `GET /attendance/staff` · `GET /attendance/qr` · `POST /attendance/qr/{outlet_id}/rotate` · `GET|POST /attendance/devices` · `PUT|DELETE /attendance/devices/{id}` · `POST /attendance/devices/{id}/test-punch` · `GET /attendance/device-ids` |
| Public check-in | `GET|POST /public/checkin/{token}` |
| ADMS (devices) | `GET|POST /iclock/cdata` · `GET /iclock/getrequest` · `POST /iclock/devicecmd` (also under `/api`) |
| Misc | `GET /batches` · `POST /uploads` · `GET /files/{id}` |
| Operations | `GET|POST|PUT /enquiries(/{id})` · `POST /enquiries/{id}/follow-ups` · `GET|POST|PUT|DELETE /expenses(/{id})` · `GET|POST|PUT /outlets(/{id})` · `POST /outlets/{id}/toggle` · `GET|POST|PUT|DELETE /staff(/{id})` · `POST /staff/{id}/toggle` · `PUT /gym/profile` · `PUT /profile` |
| Finance | `GET /finance/summary` · `GET /finance/transactions` · `GET /reports/*` (revenue-trend, member-growth, outstanding-dues, membership-expiry, enquiry-conversion) · `GET /export/{dataset}` |
| Billing | `GET /subscription` (includes `plans`) · `POST /subscription/create-order {plan_id}` · `POST /subscription/verify` · `POST /subscription/autodebit/start {plan_id}` · `POST /subscription/autodebit/verify|cancel` · `GET /subscription/payments/{id}/invoice.pdf` · `POST /webhooks/razorpay` · `POST /internal/billing/reconcile` (X-Cron-Secret) · `POST /admin/billing/reconcile` |
| Super Admin | `GET /admin/overview` · `GET /admin/analytics` · `GET /admin/gyms(/{id})` · `POST /admin/gyms/{id}/toggle` · `GET|PUT /admin/settings` · `GET /admin/churn-export` · `GET /admin/audit-logs` |

Interactive docs: `http://localhost:8001/docs` (FastAPI Swagger UI).

---
---

## Step-by-step: Host the Website, API & Billing Portal

**Recommended setup for India** (~₹1,500–3,000/month to start):
- one VPS (DigitalOcean/Hetzner/AWS Lightsail, 2 vCPU / 4 GB, Bangalore or Mumbai region) running the API with Nginx;
- MongoDB Atlas (M10 in Mumbai, or M0 free to start);
- Cloudflare R2 or AWS S3 for uploads;
- Zoho Mail or Amazon SES for email.

### Step 1 — Database
1. Create a MongoDB Atlas cluster. Create a database user and allow your server's IP.
2. Copy the connection string (`mongodb+srv://...`). This is your `MONGO_URL`. Choose `DB_NAME=gymboss_prod`.
3. *(Optional)* move the preview data: `mongodump` the preview DB, then `mongorestore` into production (see `DEPLOYMENT.md` §6).

### Step 2 — File storage & email
1. Create a bucket (e.g. Cloudflare R2 `gymboss-uploads`) and an access key. Set `STORAGE_BACKEND=s3`, plus `S3_BUCKET`, `S3_ENDPOINT_URL` (R2/Spaces only), `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY`.
2. Create a mailbox such as `no-reply@gymboss.in`. Set `EMAIL_PROVIDER=smtp`, plus `SMTP_HOST`, `SMTP_PORT=587`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM`.

### Step 3 — Server & backend
```bash
# on the VPS (Ubuntu 22.04+)
sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx git certbot python3-certbot-nginx
git clone <your-repo> /srv/gymboss && cd /srv/gymboss/backend
python3.11 -m venv .venv && source .venv/bin/activate
grep -v '^emergentintegrations' requirements.txt > req.txt && pip install -r req.txt
cp .env.example .env && nano .env          # fill in every value
python -m scripts.migrate                  # creates MongoDB indexes
```
Run the API as a service. Create `/etc/systemd/system/gymboss.service`:
```ini
[Unit]
Description=GymBoss API
After=network.target
[Service]
WorkingDirectory=/srv/gymboss/backend
ExecStart=/srv/gymboss/backend/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001 --workers 2 --proxy-headers
Restart=always
[Install]
WantedBy=multi-user.target
```
Then run `sudo systemctl enable --now gymboss`. *(Alternative: `docker build -t gymboss-api backend/ && docker run -d --env-file backend/.env -p 8001:8001 gymboss-api`.)*

### Step 4 — Frontend (website + web app + `/m`) and billing portal
Build on your laptop or on the server (Node 20 + Yarn):
```bash
cd frontend && yarn install
# Main site
REACT_APP_BACKEND_URL=https://gymboss.in yarn build && cp -r build /var/www/gymboss
# Billing portal (same code, opens straight into /billing)
REACT_APP_BACKEND_URL=https://gymboss.in REACT_APP_PORTAL_HOST=payments.gymboss.in \
REACT_APP_APP_URL=https://gymboss.in/app yarn build && cp -r build /var/www/gymboss-portal
```

### Step 5 — Nginx, DNS & HTTPS
1. **DNS** (at your domain registrar or Cloudflare): add `A` records for `gymboss.in`, `www` and `payments`, all pointing to the VPS IP.
2. **Nginx** `/etc/nginx/sites-available/gymboss`:
```nginx
server {
  server_name gymboss.in www.gymboss.in;
  root /var/www/gymboss;
  client_max_body_size 12m;
  location /api/    { proxy_pass http://127.0.0.1:8001; proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme; }
  location /iclock/ { proxy_pass http://127.0.0.1:8001; }   # biometric devices
  location /        { try_files $uri /index.html; }
}
server {
  server_name payments.gymboss.in;
  root /var/www/gymboss-portal;
  location /api/ { proxy_pass http://127.0.0.1:8001; proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; }
  location /     { try_files $uri /index.html; }
}
```
3. Enable the site, then add HTTPS: `sudo ln -s /etc/nginx/sites-available/gymboss /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx && sudo certbot --nginx -d gymboss.in -d www.gymboss.in -d payments.gymboss.in`.
4. In `backend/.env` set:
   - `FRONTEND_URL=https://gymboss.in`
   - `PORTAL_URL=https://payments.gymboss.in`
   - `COOKIE_DOMAIN=.gymboss.in` (one login across both)
   - `CORS_ORIGINS=https://www.gymboss.in,capacitor://localhost,https://localhost` (the last two are for the store apps)

   Then restart: `sudo systemctl restart gymboss`.
5. Check: `https://gymboss.in` loads, `https://gymboss.in/api/public/config` returns JSON, and you can log in at `https://payments.gymboss.in`.

### Step 6 — Daily reconciliation cron
```bash
crontab -e
15 3 * * * cd /srv/gymboss/backend && .venv/bin/python -m scripts.reconcile >> /var/log/gymboss-reconcile.log 2>&1
```
Backups: enable Atlas daily backups (or run `mongodump` nightly).

---

## Step-by-step: Razorpay Setup
1. **Activate your account:** dashboard.razorpay.com → complete KYC (PAN, GST optional, bank account) to unlock **Live Mode**.
2. **Enable Subscriptions** (Products → Subscriptions). Ask Razorpay support to enable **UPI AutoPay / recurring payments** on your account.
3. **API keys:** Settings → API Keys → generate Live keys. Put them in `backend/.env` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`), or in Super Admin → Platform Settings (saving new keys automatically clears old cached plans).
4. **Webhook:** Settings → Webhooks → *Add New*:
   - URL: `https://gymboss.in/api/webhooks/razorpay`
   - Secret: a long random string. Set the same value as `RAZORPAY_WEBHOOK_SECRET`. Without it, webhooks are rejected.
   - Events: `subscription.authenticated`, `subscription.activated`, `subscription.charged`, `subscription.pending`, `subscription.halted`, `subscription.paused`, `subscription.resumed`, `subscription.cancelled`, `subscription.completed`, `subscription.updated`, `payment.captured`, `payment.failed`
5. **Prices:** Super Admin → Platform Settings → Subscription Plans (Monthly ₹999 by default). The matching Razorpay plans are created automatically.
6. **Test:** in Test Mode, pay with card `4111 1111 1111 1111` (any future expiry, any CVV), then check Super Admin and the billing portal history. Switch to Live keys only after this works.

---

## Step-by-step: Build the Android APK / AAB
You need a Windows, macOS or Linux PC with **Android Studio** (it includes the Android SDK and JDK 17), **Node 20** and **Yarn**.

1. **Get the code** onto your PC (GitHub "Save to GitHub", or download the code).
2. **Set the app identity** (once, before the first upload; it can't change later). Edit `frontend/capacitor.config.json`:
   - `appId` (e.g. `in.gymboss.app`)
   - `appName` (e.g. `GymBoss`)
3. **Build the store bundle and sync the Android project:**
   ```bash
   cd frontend
   yarn install
   REACT_APP_BACKEND_URL=https://gymboss.in ./scripts/build-mobile.sh
   ```
   This builds the React app in store mode (no purchase UI), bundles it, and runs `npx cap sync`. On Windows, run the commands from the script manually:
   ```powershell
   $env:REACT_APP_STORE_BUILD="true"; $env:REACT_APP_BACKEND_URL="https://gymboss.in"; yarn build; npx cap sync
   ```
4. **App icon and splash:** put a 1024×1024 `icon.png` (and optionally `splash.png`) in `frontend/resources/`, then run `npx @capacitor/assets generate --android --ios`.
5. **Open in Android Studio:** `npx cap open android` (or File → Open → `frontend/android`). Wait for Gradle sync to finish.
6. **Test APK (install on your phone):** Build → Build Bundle(s)/APK(s) → **Build APK(s)**. Or from a terminal: `cd frontend/android && ./gradlew assembleDebug`. The file is at `android/app/build/outputs/apk/debug/app-debug.apk`. Send it to your phone and install it (allow "install unknown apps").
7. **Release AAB (for Play Store):**
   1. Build → **Generate Signed Bundle / APK** → Android App Bundle.
   2. Create a new keystore (`gymboss-release.jks`). **Back it up and remember the passwords**: losing it means you can't update the app (unless you use Play App Signing, which is recommended).
   3. Choose *release*. The output is `android/app/release/app-release.aab`.
8. **Versioning:** before each new upload, increase `versionCode` (1, 2, 3…) and `versionName` (`1.0.1`…) in `android/app/build.gradle`.
9. Every time you change the web code, run step 3 again, then rebuild.

> **Alternative (quick test APK without Android Studio):** host the site, then use **PWABuilder.com** → enter `https://gymboss.in/m?src=play` → Package for Android. It produces a signed APK/AAB (TWA). If you go this way, fill `frontend/public/.well-known/assetlinks.json` with the package name and SHA-256 fingerprint that PWABuilder shows. The Capacitor build above is the recommended route.

---

## Step-by-step: Publish on Google Play
1. **Account:** play.google.com/console → pay the one-time **$25** fee. Choose an *Organisation* account for BuildVVO Technologies Pvt Ltd (needs a D-U-N-S number) or a personal account. New personal accounts must run a **closed test with at least 12 testers for 14 days** before production.
2. **Create the app:** name *GymBoss*, default language English (India), App, Free.
3. **Store listing:**
   - short description (80 characters) and full description;
   - app icon 512×512, feature graphic 1024×500;
   - at least 2 phone screenshots.
4. **App content** (left menu → Policy → App content):
   - Privacy policy URL: `https://gymboss.in/privacy`
   - App access: *All or some functionality is restricted*. Give reviewers the demo login (`demo@gymbossvvo.in` / `Demo@2026`), or a dedicated reviewer account.
   - Ads: No ads.
   - Data safety:
     - Collected: name, email, phone (account), photos (member photos), app activity.
     - Encrypted in transit: Yes. Users can request deletion: Yes (in-app *Delete my account*).
     - Not shared with third parties for advertising.
   - Account deletion URL: `https://gymboss.in/privacy` (it explains in-app deletion and email requests).
   - Target audience: 18+. Content rating questionnaire: Business/productivity.
   - Financial features: none (the app doesn't sell anything).
5. **Payments:** the store build has **no in-app purchase UI** (consumption-only), so you don't set up Play Billing products. Don't mention prices or "subscribe on our website" in the app or its listing.
6. **Release:**
   1. Testing → Internal testing → create a release.
   2. Upload `app-release.aab` and accept **Play App Signing**.
   3. Add testers' emails and roll out.
   4. Install from the opt-in link and check login, members, attendance (camera) and profile.
7. **Production:** Production → Create release → reuse the AAB → submit for review (usually 1–7 days).
8. **Updates:** bump `versionCode`, rebuild the AAB, upload a new release.

---

## Step-by-step: Build & Publish on the Apple App Store
You need a **Mac** (macOS 14+) with **Xcode 16+**, **CocoaPods** (`sudo gem install cocoapods`), Node 20 and Yarn, plus an **Apple Developer Program** membership ($99/year; enrol as an Organisation with a D-U-N-S number for BuildVVO).

1. **Build and sync:**
   ```bash
   cd frontend && yarn install
   REACT_APP_BACKEND_URL=https://gymboss.in ./scripts/build-mobile.sh
   cd ios/App && pod install && open App.xcworkspace
   ```
2. **In Xcode** (App target → *Signing & Capabilities*):
   - select your Team;
   - set the Bundle Identifier (same as `appId`, e.g. `in.gymboss.app`);
   - set Version (`1.0.0`) and Build (`1`).
3. **Icons:** use `npx @capacitor/assets generate --ios` (see the Android step 4), or drag a 1024×1024 icon into *Assets → AppIcon*.
4. **Test on an iPhone:** connect it, select it as the run target and press ▶. Check that login, the camera (QR attendance) and file uploads work.
5. **App Store Connect** (appstoreconnect.apple.com) → My Apps → **+ New App**:
   - name *GymBoss*, primary language English (India);
   - the bundle ID from step 2;
   - SKU `gymboss-ios`.
6. **Archive and upload:** in Xcode select *Any iOS Device (arm64)* → Product → **Archive** → Distribute App → App Store Connect → Upload.
7. **TestFlight:** once processed (~15 min), add internal testers and install via the TestFlight app.
8. **App information:**
   - Category: Business.
   - Privacy Policy URL: `https://gymboss.in/privacy`.
   - App Privacy questionnaire: same data types as Google's Data Safety, not used for tracking.
   - Age rating: 4+.
   - Screenshots: 6.7" and 6.5" iPhone, and iPad if you support it.
9. **App Review notes** (paste this):
   > GymBoss_VVO is business-management software that BuildVVO Technologies sells to gym businesses for use by their owners and staff (multi-user organisation accounts with owner + staff logins). There is no purchase UI, pricing or external payment link in the app. Organisations that already have a subscription simply sign in (Guidelines 3.1.3(c) Enterprise Services / 3.1.3(b) Multiplatform Services). Accounts can be deleted in-app under Profile → Delete my account (5.1.1(v)). Demo login: demo@gymbossvvo.in / Demo@2026.
10. **Submit for Review** (usually 1–3 days). If Apple asks for In-App Purchase, reply explaining the B2B model above. Only if they still refuse, plan StoreKit IAP (Roadmap Phase 3).

---

## Store Payment Rules (why the apps don't sell)
| | Google Play (India) | Apple App Store (India) |
|---|---|---|
| Rule | Digital subscriptions bought in the app must use Play Billing ("business productivity software" is named). The "gym memberships" exemption covers a gym's own members, not our SaaS fee | Digital subscriptions bought in the app must use IAP. No external purchase links in India |
| What we do | **Consumption-only app**: no prices, buy buttons or steering. Users subscribe on the website/portal and sign in on the app | Same. Relies on 3.1.3(c)/(b): business users access subscriptions bought outside the app |
| Enforced by | `REACT_APP_STORE_BUILD`, `PlatformGate`, neutral banners, backend 403 on purchase endpoints from `X-Client-Platform: android_store/ios_store` | same |
| Optional later | India *user choice billing* (Play Billing + Razorpay side by side, ~11% fee) | IAP via StoreKit 2 (only if required) |

Full assessment with official policy links: `memory/STORE_BILLING_COMPLIANCE.md`.

---

## Testing
```bash
cd backend
python -m pytest tests/ -q -n 0      # run against a running API (reads REACT_APP_BACKEND_URL from frontend/.env)
```
- **Backend:** 152 automated tests pass. They cover auth, tenant isolation, members, plans, payments, attendance, staff permissions, account deletion, trial read-only, billing sync and store-client blocking.
- **Frontend:** Playwright end-to-end runs pass for the web app, mobile app, billing portal and store mode.

What was actually run, and what couldn't be verified: `memory/TEST_LOG.md`.

---

## Go-Live Checklist
- [ ] `backend/.env` is filled in from `.env.example`: strong `JWT_SECRET`, `SEED_DEMO=false` and a strong `SUPER_ADMIN_PASSWORD`.
- [ ] `python -m scripts.migrate` has been run against the production DB.
- [ ] HTTPS works on `gymboss.in`, `www` and `payments`, and `COOKIE_DOMAIN=.gymboss.in` is set.
- [ ] The `ap.emergent.sh` analytics `<script>` is removed from `frontend/public/index.html`.
- [ ] Razorpay Live keys are set, the webhook (with secret) is added, a test payment shows in history, and the reconcile cron is installed.
- [ ] S3 bucket and SMTP are configured. Test a member photo upload and a forgot-password email.
- [ ] Mobile apps are rebuilt with `REACT_APP_BACKEND_URL=https://gymboss.in` and `CORS_ORIGINS` includes `capacitor://localhost,https://localhost`.
- [ ] Database backups are enabled.

---

© BuildVVO Technologies Private Limited. All rights reserved.
