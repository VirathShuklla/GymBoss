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
**M2 — Core**: Plans & Catalogue (Membership/PT/Service/Product via category dropdown), Members CRUD via 3-step Add Member modal (photo + attachment upload to object storage, auto member-ID preview, batch dropdown, live payment summary: Payable = Plan + Admission − Discount, Due = Payable − Collected, Paid/Partially Paid/Due derivation, auto start/expiry), member detail drawer + action sheet (Freeze with expiry extension / Unfreeze / More Info / Edit / Delete-with-confirm / Attendance History / Renew / Record Payment / Payment Reminder / Transaction History / Receipt print), WhatsApp template picker (wa.me).
**M3 — Operations**: Attendance (check-in/out, duplicate-guard, today list, monthly history), Enquiries CRM (follow-ups, convert→member prefill), Expenses (month/year/category/outlet filters), Outlets (multi-branch, simplified name+address form, primary protected, disable/enable), Staff (type/outlet/permission View / View & Edit / Full Access + Enable Finance toggle, optional login accounts, disable blocks login, DELETE removes staff+login); permission enforcement: view-only staff get 403 on writes (owner-only bypass), finance pages hidden + 403 unless owner or finance-enabled.
**M4 — Communications**: Reference-style WhatsApp Reminder modal (Send Expiry Reminder / Send Payment Reminder / Send Invoice with professional templated messages incl. receipt no., amount paid, balance due, validity), row-level reminder bell on members with dues or expiry ≤7 days, individual WhatsApp templates (welcome/reminder/expiring/expired/birthday/follow-up/custom), receipts/invoices (view + print). Bulk Announcements module REMOVED per user decision; raise-support-request form removed (support = WhatsApp/Email cards only).
**M5 — Business + Billing**: Finance (range filters, revenue/expense/net/outstanding, by-method, by-category, transactions), Reports (revenue trend, member growth, outstanding dues, membership expiry, enquiry conversion), Export Center (7 CSV datasets), Subscription page with **Razorpay auto-debit subscriptions** (Plan entity cached per price, UPI Autopay/card recurring, subscription create → checkout authorization → HMAC verify → +30 days, monthly `subscription.charged` webhooks auto-extend access, `subscription.halted` shows paused state, `cancelled/completed` honored, Cancel Auto-Renew keeps access until paid-through date) plus manual one-month payment fallback, super-admin-managed keys (settings override env), dynamic plan price (plan_price_inr in platform settings propagates to landing hero/pricing/FAQ/CTA, paywall, subscription page, billing amount, MRR), BuildVVO Super Admin console (overview KPIs, gyms table, gym detail, disable/reactivate with audit, platform settings, audit logs).
**Quality**: 163/163 pytest + Playwright regression through iteration 7 (100%); startup migrations (plan type backfill, staff role casing, counter init + unique member_code index, demo batches/catalogue); 3-step member modal with live payment summary; DateField pickers (dd MMM yyyy, "Sep" normalized); filtered-vs-first-run empty states; tenant isolation verified both directions; receipt parity across payment flows; trial expiry auto-blocks app (paywall), subscription payments extend access continuously.

## Implemented — Subscription UX + Billing Hardening (2026-09-04)
- Subscription page redesign verified: single "Pay ₹{price}/month" CTA (auto-debit internally, never labeled as such), no cancel UI on the page, violet plan card, trial progress bar, payment history; cancellation lives only in My Profile as a small button (visible only when an auto-debit subscription exists, behind ConfirmDialog)
- razorpay_configured now requires a valid-format key (rzp_test_/rzp_live_); invalid/absent keys render a graceful "payments being enabled" card with WhatsApp link + support-email fallback
- PUT /api/admin/settings rejects invalid Razorpay Key IDs with 422 (a URL had been pasted into the Key ID field, causing Razorpay 401s); Razorpay upstream failures now return 503 instead of 502 (edge proxy was swallowing 502 JSON bodies)
- Verification: iteration 9 → 181/181 pytest + 100% frontend flows; card-height whitespace fixed (items-start)

## Implemented — Dashboard Billing Alert (2026-06)
- Dashboard now shows a prominent red "Your monthly payment didn't go through" alert (data-testid `billing-halted-alert`) with a "Retry Payment" CTA linking to /app/subscription, shown to owners only when the latest auto-debit subscription is `halted`
- Non-halted / non-owner states hide the banner (verified via temporary DB record + screenshot)

## Implemented — Installable PWA / Mobile App (2026-06)
- Turned the web app into an installable Progressive Web App (add-to-home-screen, standalone fullscreen, same FastAPI backend & login accounts — full owner/staff parity):
  - `public/manifest.json` (name, standalone, portrait, theme #7C3AED, icons any + maskable), PWA icons (icon-192/512/maskable-512.png generated from violet dumbbell art), apple-touch-icon + iOS web-app meta tags, `viewport-fit=cover`
  - `public/service-worker.js` — network-first for same-origin GETs with offline cache fallback; never caches `/api`; registered in `src/index.js`
  - Premium mobile bottom tab bar (`src/components/MobileTabBar.jsx`): Home / Members / Check-in / Payments + "More" (opens full nav drawer). Glass blur, safe-area padding, active-tab indicator + glow. Shown only <lg (`data-testid="mobile-tabbar"`, tabs `tab-*`). Main content given bottom padding so nothing sits behind the bar
- Verified on 390px viewport: tab bar renders, active indicator works, "More" opens the full module drawer; manifest/SW/icons all serve 200

## Implemented — Separate Mobile App (PWA) at /m (2026-06)
- Built a COMPLETELY SEPARATE mobile app experience at the `/m` route, sharing the same FastAPI backend & accounts (same users can log in AND register). Web app at `/` and `/app` untouched. Violet brand (#7C3AED) with a clean native-style layout modeled on the user's reference screens.
- PWA `manifest.json` `start_url` now points to `/m` so the installed home-screen app opens straight into the mobile app (installable now; can be wrapped for Play Store/App Store later).
- Structure (`/app/frontend/src/mobile/`): `MobileApp.jsx` (nested routes + Entry/Protected guards), `MobileLayout.jsx` (floating dark bottom nav: Home/Manage/Profile), `mobile.css`, `ui.jsx` (MButton, BottomSheet=vaul Drawer, Seg, Pills, TextInput/PhoneInput, StatusChip, skeleton/empty).
- Screens: Onboarding (4-slide carousel, Skip/Next, gb-m-onboarded flag) → Welcome (gym-photo hero, Login / Register) → Login (identifier+password) → Register (3 steps: Gym Info → owner name/email → phone/password → POST /auth/register, starts 10-day trial) → Home (Today's Collection gradient card, quick actions, 6 metric tiles, recent transactions) → Manage (7 segmented modules) → Profile (subscription card + logout).
- Manage modules (`/app/frontend/src/mobile/manage/`): Members, Plans, Enquiries, Expenses, Outlets, Staff — each a list + bottom-sheet create form wired to real APIs; Templates editor (Plan Expiring/Expired/Pending Due/Birthday Wish) with token insertion + live preview, persisted in localStorage (gb-m-templates-<orgId>) — NOT backend-synced yet.
- Verified: iteration_10 → 100% (16/16 mobile flows incl. brand-new tenant registration through /m/register) on 390x844; desktop web app regression OK. All create flows return success toasts and rows appear.
- Known/pending (P2): Templates are localStorage-only (no cross-device sync); mobile Enquiry/Expense use native date inputs; Register maps city = outlet_name.

## Credentials (see /app/memory/test_credentials.md)
- Demo owner: demo@gymbossvvo.in / Demo@2026
- Super admin: GymBoss / GymBoss@2026

## Backlog
### P0 — External credentials (user action)
- Razorpay keys are currently EMPTY in Platform Settings — save a valid Key ID (rzp_test_…/rzp_live_…; invalid formats like URLs are rejected with 422), Key Secret, and Webhook Secret in /superadmin → Platform Settings. Once saved, the Pay ₹999/month button appears and auto-debit works immediately (switch to rzp_live_ keys for production)
- DONE: In-app dashboard alert on `subscription.halted` (2026-06). Remaining P1: finalize live Razorpay webhook config (`/api/webhooks/razorpay`) in the Razorpay dashboard when going to production
- Razorpay webhook (optional, recommended): point to `https://<domain>/api/webhooks/razorpay` with the webhook secret, subscribe to `payment.captured`, `payment.failed`, `subscription.activated`, `subscription.charged`, `subscription.halted`, `subscription.cancelled`
- Official WhatsApp Business API credentials for bulk announcements (if the module is re-enabled later)
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
