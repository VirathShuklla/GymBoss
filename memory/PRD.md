# GymBoss_VVO — Product Requirements & Progress Document

## Original Problem Statement
Build GYMBOSS_VVO, a commercial gym management SaaS by BuildVVO Technologies Private Limited (India-first): public marketing website + authenticated web application + future Android/iOS apps sharing one backend. Pricing: 10-day free trial (no credit card), then ₹999/month. Reference screenshots define the UI benchmark (structure only — original branding). Multi-tenant, role-based, WhatsApp communication, announcements, finance/reports, Razorpay SaaS billing, BuildVVO super admin. Build in milestones 0→5, stopping for review after each.

## User Decisions (confirmed)
- Pricing: **₹999/month** after 10-day free trial
- WhatsApp: click-to-WhatsApp (wa.me) for individuals; bulk announcements via official WhatsApp Business API only (honest "integration required" state until connected)
- Color scheme: premium **violet (#7C3AED)** + deep navy (user requested change from initial amber) — full light/dark/system theming
- Demo account with rich seeded Indian data: demo@gymbossvvo.in
- Super admin: GymBoss / GymBoss@2026
- Page title: GymBoss_VVO; "Made with Emergent" watermark removed

## Architecture
- **Stack**: React (CRA+craco, Tailwind, shadcn) + FastAPI + MongoDB (motor). Single backend API consumed by web now and mobile apps later (token auth supports both cookie and Bearer).
- **Design system**: Outfit (headings) / DM Sans (body) / JetBrains Mono (numbers); CSS-var tokens for light/dark/system themes; amber brand (#FF5A1F), navy dark surfaces (#080D1A/#0F172A).
- **Tenant isolation**: every business document carries organisation_id (+ outlet_id); all queries scoped server-side from the authenticated user's org — client-supplied org IDs are never trusted.
- **Auth**: JWT (30-min access + 7-day refresh) in httpOnly/Secure/SameSite=None cookies; bcrypt hashing; token_version invalidation on password reset; brute-force lockout (5/IP+identifier, 10/identifier per 15 min, X-Forwarded-For aware); forgot/reset password with sha256-hashed single-use tokens and generic responses (no enumeration).
- **Subscription**: org.subscription {status, trial_started_at, trial_ends_at}; trial countdown backend-derived; expired trials show paywall screen, data never deleted.
- **Time zone**: dashboard "today" metrics use IST day boundaries.
- **Demo data**: Iron Paradise Fitness (Bengaluru, 2 outlets, 26 members, 4 plans, payments incl. today, attendance, enquiries, expenses, staff) — isolated from real orgs.

## User Personas
- Gym Owner (full access), staff roles (Admin/Manager/Receptionist/Trainer/Sales — M3), BuildVVO Super Admin (platform owner, no tenant access in M1).

## Implemented — Milestone 0 + 1 (2026-09-03)
- Landing page: navbar (anchors), hero + dashboard mockup, 9 feature cards, 3-step how-it-works, pricing (FREE 10 days → ₹999/mo), FAQ accordion, final CTA, dark footer (dynamic year), floating WhatsApp button (configurable number via platform settings; falls back to #faq)
- Auth: login (email/mobile/username), 3-step registration → org+outlet+10-day trial, forgot/reset password, protected routes, refresh-token retry interceptor
- App shell: collapsible sidebar (scoped -desktop/-mobile testids), gym card, trial badge + Upgrade Now, outlet switcher, theme Light/Dark/System (persisted, system-aware), notifications popover, user dropdown, trial-expired paywall screen
- Dashboard: 8 primary KPI cards + 7 secondary metrics (all DB-computed), quick actions, recent transactions table, onboarding checklist (dismiss persists)
- Super admin login → /superadmin placeholder (console in M5)
- Testing: 33/33 backend pytest + full frontend regression pass (iterations 1–2, all defects fixed)

## Implemented — Milestones 0–5 (2026-09-03)
**M1 — Website + Auth**: Landing page (navbar, hero + dashboard mockup, 9 feature cards, how-it-works, pricing FREE 10d → ₹999/mo, FAQ, final CTA, dark BuildVVO footer, floating WhatsApp button with configurable number, apps "coming soon"); login (email/mobile/username), 3-step registration → org+outlet+10-day trial, forgot/reset password (secure single-use tokens, anti-enumeration), brute-force lockout (XFF-aware), protected routes, refresh-token interceptor; app shell (collapsible sidebar, trial badge + Upgrade Now, outlet switcher, Light/Dark/System persisted, trial-expired paywall that still allows Subscription/Support/Profile/Settings); dashboard with real IST-day KPIs + recent transactions + onboarding checklist.
**M2 — Core**: Plans & Catalogue (Membership/PT/Service/Product CRUD), Members CRUD + auto expiry calc + due calc + receipt on admission, member detail drawer + action sheet (Freeze with expiry extension / Unfreeze / More Info / Edit / Delete-with-confirm / Attendance History / Renew / Record Payment / Payment Reminder / Transaction History / Receipt print), WhatsApp template picker (wa.me).
**M3 — Operations**: Attendance (check-in/out, duplicate-guard, today list, monthly history), Enquiries CRM (follow-ups, convert→member prefill), Expenses (month/year/category/outlet filters), Outlets (multi-branch, primary protected, disable/enable), Staff (roles, optional login accounts, disable blocks login + session), role guard (owner/admin/manager) for sensitive mutations.
**M4 — Communications**: Announcements composer (template placeholders, 5 audience types, preview with exact recipient count, send now/schedule, cancel, history, per-recipient wa.me links, honest `integration_required` status until official WhatsApp API connected), individual WhatsApp templates (welcome/reminder/expiring/expired/birthday/follow-up/custom), receipts/invoices (view + print).
**M5 — Business + Billing**: Finance (range filters, revenue/expense/net/outstanding, by-method, by-category, transactions), Reports (revenue trend, member growth, outstanding dues, membership expiry, enquiry conversion), Export Center (7 datasets CSV), Subscription page + Razorpay order/verify/webhook flow (honest 503 until keys configured), BuildVVO Super Admin console (overview KPIs, gyms table, gym detail, disable/reactivate with audit, platform settings incl. support WhatsApp/email/store URLs, audit logs), support requests.
**Quality**: 114/114 pytest + full Playwright regression across iterations 1–5; startup migrations keep seeded data upgrade-safe (plan type backfill, staff role casing, member/receipt counter init + unique (org, member_code) index, demo catalogue backfill); DateField (dd MMM yyyy) pickers; filtered-vs-first-run empty states; tenant isolation verified both directions (404 cross-tenant); receipt parity across payment flows.

## Credentials (see /app/memory/test_credentials.md)
- Demo owner: demo@gymbossvvo.in / Demo@2026
- Super admin: GymBoss / GymBoss@2026

## Backlog
### P0 — External credentials (user action)
- Razorpay: add RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET (+ RAZORPAY_WEBHOOK_SECRET) to backend/.env to activate ₹999/mo online billing
- Official WhatsApp Business API credentials for bulk announcements (Settings → Integrations)
### P1 — Product polish
- CSV member import, QR check-in, SMS/Email channels, push notifications
- Mongo aggregation pipelines for dashboard/finance/reports (scale hardening)
- Granular per-role permission matrix UI (currently owner/admin/manager vs staff split)
### P2 — Future
- Android/iOS apps on the same backend, store badges when live, multi-language

## Known Limitations (M1, intentional)
- Sidebar modules other than Dashboard render milestone-gated placeholders
- Password-reset email: EMERGENT_EMAIL_KEY is a platform placeholder; flow returns generic 200 (safe); real sending works once key is provisioned
- Floating WhatsApp button has no number configured yet (super admin sets it in M5 settings)
