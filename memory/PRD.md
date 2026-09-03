# GymBoss_VVO — Product Requirements & Progress Document

## Original Problem Statement
Build GYMBOSS_VVO, a commercial gym management SaaS by BuildVVO Technologies Private Limited (India-first): public marketing website + authenticated web application + future Android/iOS apps sharing one backend. Pricing: 10-day free trial (no credit card), then ₹999/month. Reference screenshots define the UI benchmark (structure only — original branding). Multi-tenant, role-based, WhatsApp communication, announcements, finance/reports, Razorpay SaaS billing, BuildVVO super admin. Build in milestones 0→5, stopping for review after each.

## User Decisions (confirmed)
- Pricing: **₹999/month** after 10-day free trial
- Milestone 1: click-to-WhatsApp (wa.me) only; Razorpay/official WhatsApp API deferred
- Color scheme: original amber/orange (#FF5A1F) + deep navy — NOT the reference purple
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

## Credentials (see /app/memory/test_credentials.md)
- Demo owner: demo@gymbossvvo.in / Demo@2026
- Super admin: GymBoss / GymBoss@2026

## Backlog (by priority)
### P0 — Milestone 2 (Core Application)
Members CRUD, add/edit member modal with plan+expiry auto-calc, member detail drawer, member action sheet (Freeze / More Info / Edit / Delete with confirm / Attendance History), member payments + transaction history, Plans & Catalogue tabs (Membership/PT/Service/Product)
### P1 — Milestone 3 (Operations)
Attendance (check-in/out, history), Enquiries CRM (+ convert to member), Expenses, Outlets management, Staff + role permissions
### P1 — Milestone 4 (Communications)
Individual WhatsApp actions + templates, payment reminder, invoice/receipt, announcements composer with audience selection + preview + scheduling, official WhatsApp Business API architecture, delivery tracking, message queue
### P2 — Milestone 5 (Business + Billing)
Finance reports, export center (CSV), reports, Razorpay ₹999/month billing + webhooks, BuildVVO super admin console (gyms, MRR, conversion, disable/reactivate), audit log UI, support request system, platform settings editing (WhatsApp number, store URLs)
### P2 — Tech debt
- Dashboard summary: replace in-memory member scan with Mongo aggregation pipeline (flagged in testing)
- /app/profile dedicated page
- Member CSV import

## Known Limitations (M1, intentional)
- Sidebar modules other than Dashboard render milestone-gated placeholders
- Password-reset email: EMERGENT_EMAIL_KEY is a platform placeholder; flow returns generic 200 (safe); real sending works once key is provisioned
- Floating WhatsApp button has no number configured yet (super admin sets it in M5 settings)
