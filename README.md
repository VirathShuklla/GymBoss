# GymBoss_VVO

**The modern gym operating system** — a production-oriented, multi-tenant SaaS platform for gym owners, built by **BuildVVO Technologies Private Limited** (India-first).

GymBoss_VVO lets a gym owner run day-to-day operations from one app: members, memberships, attendance, payments, enquiries, staff, outlets, expenses, finance, reports, exports — plus the SaaS billing that powers the product itself.

| | |
|---|---|
| Public website | `/` — marketing landing page |
| App | `/app/dashboard` (login required) |
| Super Admin | `/superadmin` (BuildVVO staff only) |
| Trial | 10-day free trial, no credit card |
| Price | ₹999/month (configurable by super admin) |

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Tech Stack](#tech-stack)
3. [Codebase Structure](#codebase-structure)
4. [Data Model](#data-model)
5. [Architecture: Tenancy, Auth, Permissions](#architecture-tenancy-auth-permissions)
6. [Billing & Subscription](#billing--subscription)
7. [Environment Variables](#environment-variables)
8. [Running Locally](#running-locally)
9. [Deployment](#deployment)
10. [API Reference (summary)](#api-reference-summary)
11. [Testing](#testing)
12. [Seeded Accounts](#seeded-accounts)
13. [Roadmap / Backlog](#roadmap--backlog)

---

## Feature Overview

### 1. Public Marketing Website
- Landing page: sticky navbar (Features / How It Works / Pricing / FAQ anchors), hero with live-style dashboard mockup, 9 feature cards, 3-step "How It Works", pricing card (10-day free trial → configurable ₹/month), FAQ accordion, final CTA band, dark footer with dynamic copyright year
- Floating WhatsApp contact button (number configurable by super admin; falls back to FAQ anchor when unset)
- All pricing copy is **driven by the platform price setting** — change it once in Super Admin and the whole site updates
- No fake testimonials, no fake store badges (app-store URLs configurable; shows "coming soon" until set)

### 2. Authentication & Onboarding
- 3-step registration: Account Info → Contact & Security (+91 phone, password show/hide, validation) → Gym Setup (gym name + first outlet). Creates user + organisation + outlet + default batches + 10-day trial in one shot, logs the user in
- Login by **email, mobile number, or username** (super admin uses a username)
- Forgot/reset password with single-use, sha256-hashed, 1-hour-expiry tokens; anti-enumeration generic responses
- Brute-force lockout: 5 attempts per IP+identifier / 10 per identifier per 15 min (proxy-aware via `X-Forwarded-For`)
- JWT auth: 30-min access + 7-day refresh tokens in `HttpOnly; Secure; SameSite=None` cookies, Bearer token supported for future mobile apps; `token_version` invalidates all sessions on password reset
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

### 6. Attendance
- Check-in by member search (name/phone/ID), same-day duplicate guard, check-out
- Today's list per outlet, monthly history with daily counts

### 7. Payments & Receipts
- Record payments against dues (Cash / UPI / Card / Bank Transfer / Other), filters, pagination
- Professional receipt modal (gym, member, plan, method, receipt no., outstanding) with Print/Download
- Receipt opens automatically after recording a payment

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

### 12. Finance, Reports & Exports
- Finance: date ranges (today/week/month/year/custom), Revenue / Expenses / Net / Outstanding dues, collections-by-method, expenses-by-category, transaction table
- Reports: revenue trend (6-month chart), member growth, outstanding dues, membership expiry (30 days), enquiry conversion (status + source)
- Export Center: CSV download for members, payments, attendance, expenses, enquiries, staff, plans — outlet-scoped

### 13. SaaS Subscription (Gym → BuildVVO)
- Trial (10 days) → active → payment_due/expired states, all backend-derived (never client-side)
- Razorpay order → checkout → HMAC signature verification → +30 days access; webhook endpoint for captured/failed
- Payment history; honest "being configured" state until keys exist
- Separate from member payments — never mixed

### 14. BuildVVO Super Admin (`/superadmin`)
- Overview: total gyms, trial/paying/expired/cancelled, new signups (30d), MRR, subscription revenue, trial→paid conversion
- Gyms table: owner, city, members, subscription status, last payment; detail drawer
- Disable / reactivate gym accounts (data preserved, access blocked, audit-logged)
- **Platform Settings**: support WhatsApp number, support email, app-store URLs, **monthly subscription price** (propagates site-wide + billing + MRR), **Razorpay Key ID / Secret / Webhook Secret** (DB settings override env)
- Audit log viewer (registrations, deletions, freezes, payments, admin actions)

### 15. File Storage
- Profile photos + attachments uploaded to Emergent object storage (`POST /api/uploads`), served back via authenticated, tenant-checked `GET /api/files/{id}`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 (CRA + craco), Tailwind CSS, shadcn/ui, lucide-react, recharts, sonner |
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

## Environment Variables

### `backend/.env`
```bash
MONGO_URL="mongodb://localhost:27017"     # required
DB_NAME="test_database"                   # required
FRONTEND_URL="https://<your-domain>"      # CORS origin + reset links
JWT_SECRET="<64-hex>"                     # required
EMERGENT_LLM_KEY="sk-emergent-..."        # object storage + email proxy auth
EMAIL_FROM_NAME="GymBoss_VVO"
SUPER_ADMIN_USERNAME="GymBoss"            # seeded on startup
SUPER_ADMIN_PASSWORD="GymBoss@2026"       # seeded on startup — CHANGE IN PRODUCTION
SUPER_ADMIN_EMAIL="you@company.com"
DEMO_OWNER_EMAIL="demo@gymbossvvo.in"     # demo tenant (optional)
DEMO_OWNER_PASSWORD="Demo@2026"
RAZORPAY_KEY_ID=""                        # optional fallback (DB settings preferred)
RAZORPAY_KEY_SECRET=""
RAZORPAY_WEBHOOK_SECRET=""
```

### `frontend/.env`
```bash
REACT_APP_BACKEND_URL="https://<your-domain>"   # frontend calls `${REACT_APP_BACKEND_URL}/api`
```

> Never commit `.env`. Platform settings (price, Razorpay keys, support contact) can be changed at runtime via the Super Admin console without redeploying.

---

## Running Locally

Prerequisites: Python 3.11+, Node 18+, MongoDB, yarn.

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend
yarn install
yarn start          # http://localhost:3000
```

On first startup the backend automatically:
- creates all indexes (including the unique member-code index)
- seeds the platform settings doc
- seeds the super admin (from `SUPER_ADMIN_*` env)
- seeds the demo gym *Iron Paradise Fitness* (26 members, 2 outlets, plans, payments, attendance, enquiries, expenses, staff, batches)

All backend routes are prefixed with `/api`. If you run behind a proxy, forward `/api/*` to port 8001 and everything else to the frontend.

---

## Deployment

### Emergent (recommended — this repo is ready)
1. Push/keep the repo in the Emergent workspace; supervisor already manages `backend` (port 8001) and `frontend` (port 3000) with hot reload.
2. Set production values in `backend/.env` (`FRONTEND_URL`, strong `JWT_SECRET`, change `SUPER_ADMIN_PASSWORD`).
3. Ingress routes `/api/*` → backend, everything else → frontend automatically.
4. Click **Deploy** in Emergent.

### Manual (any Docker/VM host)
```bash
# Backend (example)
cd backend && pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend (static build behind nginx/caddy)
cd frontend && yarn build
# serve frontend/build, and reverse-proxy /api/* → http://127.0.0.1:8001
```

Production checklist:
- [ ] Strong `JWT_SECRET`; rotated `SUPER_ADMIN_PASSWORD`
- [ ] `FRONTEND_URL` = exact public origin (cookies + CORS depend on it; must be HTTPS)
- [ ] Super Admin → Platform Settings: support WhatsApp/email, price, Razorpay keys
- [ ] Razorpay dashboard webhook → `https://<domain>/api/webhooks/razorpay` (secret = webhook secret)
- [ ] MongoDB with authentication + backups
- [ ] (Optional) WhatsApp Business API credentials if bulk announcements are re-enabled

---

## API Reference (summary)

All under `/api`. Auth via httpOnly cookies or `Authorization: Bearer`.

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register` · `POST /auth/login` · `POST /auth/logout` · `POST /auth/refresh` · `GET /auth/me` · `POST /auth/forgot-password` · `POST /auth/reset-password` |
| Public | `GET /public/config` |
| Dashboard | `GET /dashboard/summary` · `GET /dashboard/recent-transactions` · `GET|PUT /onboarding` |
| Members | `GET|POST /members` · `GET /members/next-code` · `GET|PUT|DELETE /members/{id}` · `POST /members/{id}/freeze|unfreeze|renew` |
| Plans | `GET|POST /plans` · `PUT|DELETE /plans/{id}` |
| Payments | `GET|POST /payments` · `GET /payments/{id}/receipt` |
| Attendance | `POST /attendance/check-in` · `POST /attendance/{id}/check-out` · `GET /attendance` · `GET /attendance/history` |
| Misc | `GET /batches` · `POST /uploads` · `GET /files/{id}` |
| Operations | `GET|POST|PUT /enquiries(/{id})` · `POST /enquiries/{id}/follow-ups` · `GET|POST|PUT|DELETE /expenses(/{id})` · `GET|POST|PUT /outlets(/{id})` · `POST /outlets/{id}/toggle` · `GET|POST|PUT|DELETE /staff(/{id})` · `POST /staff/{id}/toggle` · `PUT /gym/profile` · `PUT /profile` |
| Finance | `GET /finance/summary` · `GET /finance/transactions` · `GET /reports/*` (revenue-trend, member-growth, outstanding-dues, membership-expiry, enquiry-conversion) · `GET /export/{dataset}` |
| Billing | `GET /subscription` · `POST /subscription/create-order` · `POST /subscription/verify` · `POST /webhooks/razorpay` |
| Super Admin | `GET /admin/overview` · `GET /admin/gyms(/{id})` · `POST /admin/gyms/{id}/toggle` · `GET|PUT /admin/settings` · `GET /admin/audit-logs` |

Interactive docs: `http://localhost:8001/docs` (FastAPI Swagger UI).

---

## Testing

```bash
cd backend
python tests/cleanup_test_data.py
python -m pytest tests/ -q -p no:randomly -n 0   # 163 tests
python tests/cleanup_test_data.py
```

Covers: auth (register/login/lockout/reset/refresh), tenant isolation (cross-org 404s), member math (payable/due/status), batches, next-code, plans, payments, attendance, enquiries, expenses, outlets, staff permissions (view-only 403, finance guard), admin settings (partial saves, price validation), subscription states, exports.

Frontend flows are verified with Playwright end-to-end suites (landing, 3-step registration, 3-step member modal, drawer actions, permission-restricted staff UX, super admin console).

---

## Seeded Accounts

| Account | Identifier | Password | Purpose |
|---|---|---|---|
| Demo gym owner | `demo@gymbossvvo.in` | `Demo@2026` | Iron Paradise Fitness — rich demo data |
| BuildVVO super admin | `GymBoss` | `GymBoss@2026` | `/superadmin` console |

> Demo data is isolated to the demo tenant — never mixed into newly registered gyms.

---

## Roadmap / Backlog

- **P0 (needs credentials)**: live Razorpay keys (Super Admin → Platform Settings)
- **P1**: CSV member import, QR check-in, official WhatsApp Business API (if bulk announcements return), granular per-module permission matrix
- **P2**: Android/iOS apps on this same backend, Mongo aggregation pipelines for dashboard/finance at scale, app-store badges when live

---

© BuildVVO Technologies Private Limited. All rights reserved.
