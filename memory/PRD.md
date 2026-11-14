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
- Known/pending (P2): mobile Enquiry/Expense use native date inputs; Register maps city = outlet_name.

## Mobile app updates (2026-06)
- Removed the mobile "Templates" Manage tab (kept simple, matching the web app; Templates.jsx deleted).
- Member Actions: tapping a member row on mobile opens an actions sheet (`m-member-actions`) with member summary + Renew Membership (POST /members/{id}/renew), Record Payment (POST /payments), and Send WhatsApp Reminder (expiry/payment/invoice messages via `buildReminderOptions` → wa.me). Test-ids: m-action-renew/payment/reminder, m-renew-save, m-payment-save, m-reminder-send. Verified: payment + renew toasts fire and list refreshes.
- Light/Dark/System theming in the mobile app: quick sun/moon toggle in the Home header (`m-theme-toggle`) + Light/Dark/System selector in Profile (`m-appearance`, m-theme-light/dark/system), reusing the shared ThemeContext. Verified dark mode renders correctly.
- Pills options now carry `data-testid={m-pill-<value>}` for reliable automation.
- Mobile Members search: debounced search bar (`m-members-search`, clear `m-members-search-clear`) hitting `GET /members?search=` (name/phone/member code). Verified: 52 → 1 result for "Aarav".

## Landing page — mascot branding + classy refresh (2026-06)
- Hero uses a classy circular avatar (panda bust `hero_bust.jpg` on a violet disc with subtle ring + glow), replacing the full-body sticker look per user feedback.
- Pricing: a peeking panda head (`peek.png`, background-removed) leans over the top of the offer card ("looking over the offer"), shown on all sizes, small + tasteful.
- Removed floating chips / Final CTA + How It Works mascots to keep it ad-conversion clean.
- Mascot assets in `/app/frontend/public/mascots/`. Verified desktop (1920) + mobile (390): no horizontal overflow.

## Razorpay activated + mobile pay flow (2026-06)
- Saved live TEST keys in Platform Settings (`razorpay_key_id=rzp_test_TXqmoAJOCNDkiy`, secret set) — verified real Razorpay subscription/plan creation succeeds; `razorpay_configured=true`.
- Added the missing Razorpay pay flow to the MOBILE app (`/m` → Profile): "Pay ₹999/month" button (`m-pay-button`) loads checkout.js → `/subscription/autodebit/start` → checkout → `/subscription/autodebit/verify`; halted-retry card, cancel auto-renewal (`m-cancel-autodebit`), and "payments being enabled" fallback all mirror the web app. Verified button renders for the expired demo tenant.
- Still needed from user for PRODUCTION: (1) switch to `rzp_live_` keys after Razorpay KYC, (2) set Webhook Secret in Platform Settings + point Razorpay webhook to `/api/webhooks/razorpay` (events: payment.captured/failed, subscription.activated/charged/halted/cancelled) so auto-renewals reflect automatically.

## Landing revamp + Attendance removal + Receipts + Panda logo (2026-06)
- **Landing redesign (Cream + Navy + Soft Purple)**: hero now on cream (#FBF6EC) with navy headline, violet accents, and handwritten (Caveat) annotations + hand-drawn arrows on desktop only ("Stronger Gyms, Brighter People", "All Your Gym Operations In One Place", "Members/Payments/Growth ✓"). `hero-annotations` hidden < lg; no horizontal overflow at 1920 or 390. Matches user's reference mockup.
- **Panda logo everywhere**: replaced the dumbbell mark with the user's panda image at `/frontend/public/logo.png`; regenerated PWA icons (icon-192/512/maskable-512, apple-touch-icon) + favicon from it. Used in web `Logo.jsx`, dashboard mockup, mobile `Welcome.jsx`.
- **Attendance module REMOVED** (web + mobile + marketing): route + sidebar nav + mobile tab + MemberDrawer "Attendance History" + Dashboard metric/quick-action + landing feature card + mockup sidebar + copy. (Backend attendance endpoints untouched/harmless.)
- **Members filter chips (All / Active / Expiring / Due)**: web `Members.jsx` (`members-chip-*`, wired to status + new backend `due` bool param on GET /members) and mobile `manage/Members.jsx` (`m-chip-*`, client-side filter on loaded list).
- **WhatsApp payment receipt to the customer**: after a gym owner records a member payment (or renews with amount paid), they can send a formatted receipt to that member on WhatsApp. Web: `ReceiptModal` "Send on WhatsApp" (`receipt-whatsapp-button`). Mobile: post-payment "Payment Receipt" sheet with `m-receipt-whatsapp` + `m-receipt-done`. Shared `buildReceiptMessage()` in `lib/whatsapp.js`.
- **Mobile Razorpay pay flow** added to `/m` Profile (`m-pay-button`) — see previous entry; both web & mobile now accept subscription payments with the saved rzp_test_ keys.
- **Demo trial auto-refresh**: startup now resets the demo tenant's lapsed 10-day trial so the web app is never stuck behind the paywall in preview.
- Verified: iteration_11 → backend 5/5 pytest, frontend 100% of flows (web + mobile), zero bugs. Razorpay hosted checkout not auto-completed (needs real card — user does final tap).

## Landing polish + Mobile Finance/Reports/Onboarding + Docs (2026-06)
- **Landing**: left annotation changed to "From Chaos to Control"; removed the play icon on "See How It Works"; panda logo image now has rounded (transparent) corners — regenerated `/frontend/public/logo.png` + all PWA icons (192/512/maskable/apple-touch) from a rounded, white-trimmed master so no white edges.
- **Mobile app** (`/m`): added **Finance** and **Reports** tabs to Manage (finance-access gated: owner/admin/manager or finance_enabled) — new `mobile/manage/Finance.jsx` (range summary + collections-by-method + transactions) and `Reports.jsx` (revenue trend, outstanding dues, upcoming expiries, enquiry conversion), reusing /finance/* and /reports/* endpoints. Added the getting-started **onboarding checklist** ("Get your gym ready") to mobile Home (`m-onboarding`, deep-links into Manage, dismiss persists via PUT /onboarding).
- **README** updated: mobile PWA section (replaces Attendance), mobile row in tech stack, intro reflects web+mobile.
- **Code comments**: added module docstrings to backend server/deps/members/ops/comms/finance/billing/admin and header comments to the new/changed mobile screens.
- Verified via screenshots (landing desktop, mobile Home checklist, mobile Finance) + backend health; frontend compiles clean.

## Financial-logic audit + fix (2026-06)
- **Bug**: demo/members could show a due unrelated to price (e.g. ₹6000 plan → random ₹7000/₹7911 due).
- **Root cause**: the demo SEED fabricated `due_amount` via `rng.choice([...,plan_price])` and wrote payment rows with random amounts, with NO `payable`/`discount`/`admission` stored — so due ≠ payable − paid. The real backend math (create_membership/renew/record_payment in members.py) was already correct: payable = price − discount + admission; due = payable − paid; payments decrement due.
- **Fix** (backend, source-of-truth only): (1) rewrote demo seed so each member has payable = price − discount + admission and a matching payment row so due = payable − Σ(payments); a few "today" payments each reduce their member's due. (2) Added a demo-only startup migration recomputing payable/due from plan price + discount + admission and actual payments. (3) One-time wiped & re-seeded the demo tenant to remove drift + leftover QA `TEST_` members.
- **Existing records**: real tenants need NO recalculation (their data already obeys the invariant via correct write logic); only the demo tenant was corrected. record_payment intentionally decrements per-cycle (NOT Σ-all-payments) because renewals reset payable each cycle.
- **Verified**: testing_agent iteration_12 → backend 9/9 (all 5 example cases, partial→full, validation 422/404, renewal, due filter, persistence), frontend 100% screens. Post-reseed direct check: 26 members, 0 inconsistent, Σdues == finance.outstanding (32,625), Σpayments == revenue (113,875), status mix 17 Paid/6 Partial/3 Due.
- **Not a bug**: DELETE /members works (soft-delete + list filters deleted_at); the "leftover members" were un-cleaned QA test rows, now purged.

## Payment reversal/edit + onboarding fix (2026-06)
- **Payment reverse & edit** (web + mobile): new backend `PUT /payments/{id}` (edit amount/method/notes) and `DELETE /payments/{id}` (reverse). Both call `_apply_payment_delta` → due = clamp(due + (old−new), 0, payable) + payment_status. UI: web Payments page rows (Edit/Reverse modals), web MemberDrawer transaction history (Edit/Reverse), mobile member sheet → new **Payment History** view (`m-action-history`) with inline edit + reverse.
- **Onboarding "tutorial" not updating — fixed**: root cause was AuthContext loading `organisation.onboarding` once at login (stale). Web Dashboard + mobile Home now fetch `GET /onboarding` fresh on mount. Also added **self-heal** in `GET /onboarding`: if plans/members/payments/staff already exist but a flag was never set, it backfills the flag.
- **Verified**: testing_agent iteration_13 → backend 6/6 (6000 plan: pay 2000→due 4000, edit→5000→due 1000, reverse→due 6000/Due; clamp when amount>payable→0/Paid; 422/404 validation; sum(dues)==finance.outstanding), frontend 100% web + mobile selectors; onboarding auto-progresses on a fresh gym and dismiss persists. Direct curl confirmed edit/reverse math.
- Known minor (not blocking): edit does not cap amount at payable (server clamps due, keeps finances consistent — treats excess as overpayment); reverse hard-deletes the payment (audit logs the amount).

## Super Admin SaaS analytics console (2026-06)
- Rebuilt `/superadmin` into a professional analytics dashboard (SuperAdmin.jsx) with controlled Tabs: Overview / Customers / Settings / Audit.
- **Backend** `/api/admin/analytics` (admin.py): real-data KPIs — MRR (=paying×price), ARR, ARPU, total/paying/trial/expired/cancelled, new-this-month + MoM signup growth, retention, churn, trial→paid, avg lifetime; 12-month revenue+growth series (from paid `subscription_payments`); trial funnel; payments (successful/failed/pending/success-rate/renewals/expired); product usage (DAU/WAU/MAU via member-payment recency proxy, members managed, members this month, payments logged). `/api/admin/gyms` enhanced with per-gym health (healthy/at_risk/high_risk/churned) + score, monthly_revenue (price only if active), last_activity, and `status`/`health` filters (no N+1 — aggregations).
- **Frontend**: priority KPI row, revenue chart with metric (Revenue/New/Total) + range (3M/6M/1Y/All) toggles, customer-growth chart, trial funnel w/ conversion %, payments & usage cards, clickable Action Required → filtered Customers tab, customers table w/ status+health chips, gym detail dialog, enable/disable.
- **Data integrity**: all values from DB; trial≠paying, cancelled/expired≠paying, only paid subscription_payments count as revenue. Honest "Not tracked yet" note for marketing/CAC, website visitors, per-user logins, WhatsApp-sent, retention cohorts (no event data) — omitted rather than faked.
- **Verified**: testing_agent iteration_14 → backend 21/21 (auth 403/401, metric reconciliation, filters, price→MRR propagation), frontend all testids + filter/settings/audit; fixed Action Required tab navigation (controlled Radix Tabs) and verified high-risk drill-down. Purged leftover QA test gyms.

## Attendance (QR + Biometric), Plans & Offers, PDF receipts, Churn export, Admin dark mode (2026-10-07)
- User asked: churn watchlist CSV export; light/dark for Super Admin + owner dashboard; PDF invoices (chose member payment receipts only); admin-editable prices everywhere (chose Monthly/Quarterly/Yearly with offers); attendance module with biometric (chose real eSSL/ZKTeco ADMS + test punch) and QR (no location check); better mobile UI with attendance; full testing; README with admin + demo passwords.
- Backend: `attendance.py` (summary, staff list, per-outlet QR tokens + rotate, public `/public/checkin/{token}`, devices CRUD, auto-delete-on-expiry, test punch, device-ids, ADMS `/iclock/cdata|getrequest|devicecmd` at `/iclock` and `/api/iclock`); `deps._price_plans/get_pricing_plans/org_mrr`; billing takes `plan_id` (30×months days, per-plan Razorpay plan cache); admin `pricing_plans` settings + `/admin/churn-export`; `receipt_pdf.py` + `/payments/{id}/receipt.pdf`.
- Frontend: shared `components/attendance/*` (web dialogs + mobile bottom sheets), web `/app/attendance` + sidebar nav, public `/checkin/:token`, mobile Attendance tab (4-tab nav), Home quick actions; `PlanPicker` on web Subscription + mobile Profile; landing 3-plan pricing; Super Admin theme toggle, churn CSV buttons, plans & offers editor; PDF download (web) / share (mobile).
- Verified: testing_agent iteration_15 → backend 24/24, frontend 100%. Test data cleaned, pricing restored to defaults.
- Caveat: real eSSL devices call `/iclock/*` at the domain root; preview ingress only routes `/api/*` to backend, so production routing of `/iclock` must be confirmed (or device path set to /api/iclock if model supports it).

## Landing pricing redesign (2026-10-07)
- Pricing section only (user choice): Yearly highlighted as "Best Value" (dark card, first on mobile), automatic savings vs monthly price (strike-through + "You save ₹X", "Save N%"), per-month equivalent, fixed price-digit spacing (display font instead of monospace), trust row (no card, cancel anytime, data never deleted, UPI/card/netbanking). Self-verified by screenshot (desktop + 390px).

## Conversion tracking, Activated Trial, trial UX, landing value sections (2026-10-09)
- User asked: landing page as a conversion machine with very high perceived value (chose: keep look, add sections + speed work); simpler Super Admin; track 20 conversion events (chose first-party only); Activated Trial (1 plan, 3 members, 1 payment; editable now); funnel Visitors→Signup Started→Registered→Gym Created→Activated→Paying→Retained with %; non-aggressive trial countdown showing value created; trial expiry never deletes data (chose read-only mode); performance.
- Backend: `analytics.py` (events collection, POST /api/events whitelist, milestones via after_change, link_visitor on register, GET /trial/status, GET /admin/funnel); write block (402) for expired trials in deps.get_org_user (subscription/auth/support/events/onboarding allowed); billing tracks payment_initiated/successful/failed + subscription_started; admin activation_rules setting.
- Frontend: lib/track.js (visitor id, UTM first-touch, WhatsApp tracking via window.open/link capture), TrialBanner + ExpiredBanner (web + mobile), Super Admin Funnel tab (FunnelTab.jsx) with plain-language descriptions, landing ValueStack / RoiCalculator / Comparison / StickyMobileCta, per-day pricing, React.lazy code-splitting of all non-landing routes + below-fold, trimmed Google Fonts, blur effects hidden on mobile.
- Verified: testing_agent iteration_16 → backend 12/12, frontend 100%. Test events/orgs cleaned.
- Note: excel_import_used is defined but the app has no Excel import feature yet, so it will stay 0.

## Landing simplified (2026-10-09)
- Removed "Do the maths" ROI calculator, "8 tools" value stack and Register-vs-Excel comparison (files deleted). Features are now mentioned once: 8 outcome-led cards (with "Replaces:" line) in Features; How It Works = 3 setup steps; Pricing keeps plan cards + per-day + trust row + one "every plan includes every feature" line; FAQ rewritten as objection-handling and removed two inaccurate claims (CSV import, WhatsApp Business API bulk). Page order: Hero → Features → How It Works → Pricing → FAQ → Final CTA (+ sticky mobile CTA). Self-verified by screenshots desktop + 390px (no overflow).

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
- Confirm `/iclock/*` root routing in production for physical biometric devices
- CSV member import, SMS/Email channels, push notifications
- Mongo aggregation pipelines for dashboard/finance/reports (scale hardening)
- Granular per-role permission matrix UI (currently owner/admin/manager vs staff split)
### P2 — Future
- Android/iOS apps on the same backend, store badges when live, multi-language

## Known Limitations (M1, intentional)
- Sidebar modules other than Dashboard render milestone-gated placeholders
- Password-reset email: EMERGENT_EMAIL_KEY is a platform placeholder; flow returns generic 200 (safe); real sending works once key is provisioned
- Floating WhatsApp button has no number configured yet (super admin sets it in M5 settings)

## Store-readiness pack + Password management (2026-06)
- `/privacy` and `/terms` pages (BuildVVO Technologies Private Limited, buildvvotechnologies@gmail.com, India; DPDP Act, account-deletion-by-email section). Linked from footer, web/mobile register consent, mobile Profile.
- In-app (store wrapper) mode: `lib/inApp.js` detects Capacitor, TWA referrer `android-app://`, or `?app=1` (persisted `gb-in-app`, run at boot in index.js). Razorpay pay buttons hidden on /m/profile and /app/subscription; `StoreBillingNote` shown instead. **Set the PWABuilder/TWA start URL to `/m?app=1`.**
- `public/.well-known/assetlinks.json` placeholder (fill package_name + SHA-256 when Play Console app is created).
- `POST /api/auth/change-password` (current pw check, 5 fails/15min → 429, token_version bump, current session re-issued, other devices signed out). UI: web Profile ChangePasswordCard, mobile Profile bottom sheet. Mobile login has "Forgot password?" (→ /forgot-password?from=m, back returns to /m/login).
- WhatsApp float no longer overlaps sticky mobile CTA.
- Tested: iteration_17 (backend 10/10, frontend flows pass; in-app boot flag bug fixed after).

## Backlog
- P1: shorter one-step signup; "Free WhatsApp demo" hero button; hide "Upgrade Now" CTAs in in-app mode
- P2: Revenue & Profit view in Super Admin; Testimonials manager; in-app account deletion button

## Account deletion + Staff login editing + Mobile polish (2026-06)
- `POST /api/auth/delete-account` {password, confirm:"DELETE"}: the true owner (role owner, no staff_id, org.owner_id matches) permanently wipes the org and every org-scoped collection, and Razorpay subscriptions are cancelled. Staff delete only their own login. Demo and super admin are blocked (403). 5 wrong passwords in 15 min → 429. UI: web Profile DeleteAccountCard (dialog) and mobile Profile DeleteAccountSheet.
- Staff edit (web + mobile): the owner can change a staff member's login email (uniqueness check, signs them out) and set a new password, or create a login for a staff member who has none. Only the owner can change roles, emails or passwords, and roles are validated (role elevation is blocked).
- Mobile polish: refined primitives (buttons, sheets, inputs with focus rings, tabs/pills with 40px+ targets, skeleton rows, empty states), sticky Manage tabs that auto-scroll to the active tab, row press states, emoji removed, checklist hidden once complete, trial badge kept on one line, reduced-motion support. Tailwind opacity 8/12 added (fixes invisible avatar/tint backgrounds).
- Demo trial auto-refreshes when ≤3 days left.
- Tested: iteration_18/19 → backend 33/33, frontend 100%.

## Bug fix: Razorpay checkout "Something went wrong / Payment Failed" (2026-06)
- Root cause: Razorpay keys were switched to a new account, but the cached Razorpay plan ID (settings.razorpay_plan_cache*) and the pending "created" subscriptions belonged to the old account → checkout got a non-existent subscription_id.
- Fix: the plan cache is now tied to key_id; reused pending subscriptions are re-validated with Razorpay (and abandoned if invalid or from another key); saving new keys in Super Admin clears the plan cache and abandons pending subs. Yearly plan also failed (total_count 120 > Razorpay max) → total_count = 120 // months.
- Verified: monthly/quarterly/half-yearly/yearly autodebit start OK; checkout opens with payment options in test mode.

## Self-hosting + Store compliance Phase 1 + Billing sync + Billing portal (2026-06)
- Compliance assessment: memory/STORE_BILLING_COMPLIANCE.md. Decision: consumption-only store apps (no purchase UI); website/portal keep Razorpay.
- Store builds: REACT_APP_STORE_BUILD / Capacitor / ?app=1 → X-Client-Platform header, Bearer tokens, PlatformGate redirects selling routes to /m, neutral banners, backend 403 on purchase endpoints from store clients.
- Billing portal /billing (payments.gymboss.in via REACT_APP_PORTAL_HOST): plans, Razorpay pay, renewal disclosure, cancel auto-renew, history, invoice PDF. Owner/admin only (server-enforced).
- billing_sync.py: payment ledger (exactly-once extension), webhook event dedupe (failure-safe), pending/halted/paused/resumed/cancelled/completed/updated handling, failed-renewal rows (24h dedupe), reconcile (cron endpoint + scripts/reconcile.py). Webhooks now require a secret.
- Env-driven: CORS_ORIGINS/PORTAL_URL/COOKIE_DOMAIN, STORAGE_BACKEND (emergent|s3|local), EMAIL_PROVIDER smtp, SEED_DEMO, CRON_SECRET. .env.example files, scripts/migrate.py, backend Dockerfile, DEPLOYMENT.md, memory/TEST_LOG.md.
- Capacitor 7: frontend/android + frontend/ios generated, camera permissions, scripts/build-mobile.sh. Native binaries NOT built (no SDK/Xcode in env).

## Backlog
- P1: Phase 2 Android Play Billing + India user choice billing (needs native billing plugin, Play service account)
- P1: one-step signup; WhatsApp demo hero button
- P2: Revenue & Profit view in Super Admin; testimonials manager; iOS IAP only if Apple rejects 3.1.3(c)

## Mobile UI minimal refinement + README guide (2026-06)
- /m refined to a calm, minimal look:
  - Home: date + greeting; an ink "Today's collection" hero; borderless quick actions; "Needs attention" and "At a glance" grouped lists; max 5 recent payments; a compact onboarding progress card.
  - Navigation and lists: frosted full-width bottom nav with an indicator; grouped iOS-style lists in Profile, Members, Staff and Attendance; quiet segmented tabs.
  - Behaviour: scroll-to-top on navigation; Home shortcuts deep-link to member filter chips (?chip=due|expiring|active).
- README.md rewritten as a full step-by-step guide: Done/To-do status, features (incl. billing portal, store mode, billing sync), hosting (VPS + Nginx + DNS + HTTPS + cron), Razorpay setup, Android APK/AAB build, Google Play publishing, iOS build and App Store publishing, store payment rules, go-live checklist.
- Tested: iteration_21 (frontend 95%; the scroll-position bug and consistency nits fixed afterwards).

## Security & accounting hardening — Round 1 (2026-06)
- Billing: /subscription/verify fetches the Razorpay payment and requires matching order, amount, currency and a captured/authorized status (payment_matches); webhook payment.captured is checked the same way. Webhook secret is mandatory, and the ledger keeps access extension exactly-once.
- Mongo client is tz_aware (UTC) → fixes naive/aware comparisons.
- Super admin seed: explicit env credentials only (no defaults, min 10 chars), never resets an existing password. Demo seed needs DEMO_OWNER_EMAIL/PASSWORD + SEED_DEMO=true.
- Permission matrix (deps.perm_level):
  - owner/admin = full; "full" = create/edit + delete/reverse + staff/outlets/settings; "manage" = create/edit; "view" = read.
  - require_manager needs full; require_full guards member delete and payment reversal.
  - Only owner/admin change permission/finance; only the owner changes role/login email/password.
  - Finance = owner/admin/finance_enabled, with the frontend aligned.
  - Salary is hidden from users without finance access.
- Write restriction covers expired, payment_due, cancelled and none.
- Auth:
  - api.js refreshes on /auth/me 401;
  - refresh rejects disabled users;
  - login input lengths bounded;
  - phone login with a duplicated number returns 409 (use email);
  - X-Forwarded-For only trusted via TRUSTED_PROXIES;
  - CSRF Origin/Referer guard for cookie-authenticated writes.
- Member accounting (member_ledger.py):
  - invoice per membership cycle (member_invoices); payments allocated FIFO; overpayment kept as credit_balance; dues carry over across renewals;
  - balances recomputed from invoices+payments with optimistic concurrency (ledger_rev + touch);
  - reversals never delete (status reversed + negative compensating entry, reason/actor/time); edit history kept;
  - money fields validated (≥0, finite, discount ≤ gross), plans must be active membership plans, methods validated, outlet ownership checked, payment_date honoured;
  - one-time versioned migration (db.migrations) creates opening invoices for existing members.
- Dates & freezes: month/year math clamps to the real month end; freezes store frozen_from (future freezes don't apply early), overlaps rejected, and unfreeze gives back unused extension days.
- Attendance:
  - one eligibility rule (assert_member_eligible) for manual, QR and biometric;
  - the punch engine uses the event's own IST day and exact-timestamp dedupe;
  - QR staff check-in uses the staff record + status (owner fallback);
  - biometric devices take an optional allowed_ips allowlist; deletion commands are queued in device_commands until the device acknowledges them via /iclock/devicecmd (re-sent after 5 min).
- Round 2 (pending): reports via aggregation + accounting-date policy, typed report params, upload content sniffing + streaming limits, lockfile/pins/health checks, portable isolated tests.
- Round-1 follow-ups (iteration_22/23 findings, fixed):
  - salary isn't overwritten by non-finance editors;
  - staff toggle/delete hierarchy guard (no self, admins only by owner/admin);
  - deletes of expenses, plans and devices need full access;
  - freeze status is read from freeze_history;
  - verify returns 400 for an unknown payment;
  - reconcile expires stale orders;
  - ADMS failed commands are retried 3×;
  - credit balance is shown in the web drawer and mobile member list/actions;
  - the mobile renew sheet preselects the current plan;
  - client IP is taken from the right-most trusted X-Forwarded-For hop, or REAL_IP_HEADER, so spoofing is blocked.


## Round 1 completion — transactional money writes (2026-10-21)
- User choices: MongoDB transactions (not step records); block account deletion until Razorpay confirms cancellation; idempotency keys for payments/renewals/reversals/migration; tests for crashes, retries, races, concurrent migrations.
- Preview MongoDB switched to single-member replica set rs0 (supervisord `--replSet rs0`, rs.initiate). Backup taken first: /root/mongo_backup_2026-10-21. MONGO_URL unchanged. API refuses to start on standalone Mongo (require_transactions); DEPLOYMENT.md documents this.
- deps.run_txn (snapshot/majority, auto-retry on conflicts), best_effort (audit/analytics after commit), checkpoint/FAULTS (test-only fault injection), Idempotency-Key helpers with body fingerprint (same key + different body → 422; TTL 7 days).
- Atomic: member create, renew (expiry CAS), record payment, edit payment, reversal (negative entry + mark original + recompute), subscription grant (ledger + access + payment row; ledger never deleted), opening-balance migration.
- Unique indexes: uniq_opening_invoice, uniq_member_cycle (member_id+cycle_key), uniq_reversal (reversal_of), idempotency_keys(org,key), migrations.id.
- Webhooks: claim lease (processing/done/failed, 5-min stale reclaim, 409 while busy) — crashed events are re-processed, never skipped.
- Razorpay cancellations: durable razorpay_ops records; confirmed only when Razorpay reports cancelled/completed/expired; failures (incl. network) block delete-account (409) / autodebit cancel (503); reconcile retries failed ops and resumes interrupted purges.
- Account purge: org marked deleting_at+disabled first, purge idempotent, resumed at startup/reconcile; disabled/deleting orgs can't log in or refresh.
- Frontend: api.js auto-adds Idempotency-Key to money writes (reused on retry, cleared on success); reversed/reversal rows show badges, red -₹ amounts, no Edit/Reverse (web drawer, Payments table, mobile).
- Tests: iteration_25 + iteration_26 — in-process suites tests/test_iter25_txn_recovery.py (20/20) and test_iter26_idem_fp_purge.py (6/6) on isolated DB gymboss_txn_tests; HTTP regression 48/48. Razorpay MOCKED in those tests only.
- Next: Round 2 (reports aggregation + IST accounting dates, typed params, upload sniffing/limits, lockfile/pins/health checks, portable isolated tests, ADMS device auth review).


## Round 2 — reports, uploads, native app, portability (2026-10-21)
- User choices: reports use the transaction date entered (IST), legacy rows derive it from created_at in IST; uploads = JPG/PNG/WebP/PDF up to 5 MB; reversals dated on their own day, originals kept.
- Reports/finance (finance.py): all totals via MongoDB aggregation (no 5,000/2,000 caps) on payments.payment_date / expenses.date; paginated transactions, dues, expiry, expenses (stable sort with id tiebreaker); streamed CSV exports with date_from/date_to, formula-injection escaping; strict 422 param validation (parse_day, page_params, ranges/months/days).
- Dashboard today's collection uses payment_date == today IST. Payments list filters on payment_date. Migration 2026_10_txn_dates_v1 (server.backfill_txn_dates) backfilled payment_date, expense dates and member joining_date.
- Uploads: body streamed with a 5 MB limit (413 early), real type sniffed from bytes, safe filenames; files served with sniffed type + nosniff; unsafe legacy files served as attachment with CSP sandbox (existing attachments kept).
- Billing: immutable purchase snapshot (plan_id, plan_name, months, amount) stored on orders and autodebit subscriptions; access grants, subscription amount and invoices use the snapshot.
- Auth: change-password returns replacement native tokens for app clients; disabled/deleting orgs rejected at login/refresh.
- Frontend: persistent Idempotency-Keys in localStorage 'gb-idem' (24h, removed on success); native tokens in OS secure storage (@aparajita/capacitor-secure-storage, migrated from localStorage); native PDF/CSV via @capacitor/filesystem + @capacitor/share; exports via authenticated API (no window.open); Finance "Load more"; Export Center date range.
- Ops: GET /api/health (DB + transactions), Dockerfile HEALTHCHECK, frontend/yarn.lock staged for commit, tests use tests/paths.py (old one-off suites moved to tests/archive, excluded).
- Tests: iteration_27 (in-process tests/test_iter27_round2.py 12/12 on isolated DB with 6,200 payments / 2,600 expenses, IST boundaries) + iteration_28 retest 100%.
- Known limits: native secure storage/share only verifiable on a device build (needs `npx cap sync`); members list endpoint still loads up to 10,000 members per request; ADMS device-auth review still pending.

## Round 3 — 2026-10-21
- Monthly Finance PDF (`GET /api/reports/monthly.pdf?month=YYYY-MM&outlet_id=`): collections by type and method, expenses by category, net, and outstanding dues, by IST transaction date. Available from web Reports and mobile Reports.
- Outlet filter on revenue-trend, member-growth, enquiry-conversion, outstanding-dues, membership-expiry and the PDF. Web uses the header outlet; mobile has its own selector (stored in gb-outlet).
- Load more for dues and expiry on web and mobile; mobile's 15-row cap removed.
- Dashboard active count uses deps.member_status, so a future freeze still counts as active.
- Uploads: 5 MB limit. Images may be at most 6000 px per side and 36 MP; dimensions are checked before decoding, and corrupt images and decompression bombs are rejected. Profile photos are resized to a 1024 px longest edge (never upscaled), EXIF-rotated and stripped of metadata. Attachments are stored byte-identical. PDFs are checked with pypdf (no encrypted or 0-page files). Legacy files are still served.
- Protected photos and attachments: `ProtectedImg` and `openProtectedFile` load them through the authenticated API client, so native Bearer sessions work.
- Idempotency: stored retry scopes are hashed, with no member data kept. `GET /api/idempotency/{key}` lets the client reconcile keys after login: completed keys are dropped, and unknown keys only after 10 minutes. Keys no longer expire on a timer without a server check.
- Tests: backend/tests/test_iter29_round3.py (5/5), iteration_29.json. Native Android/iOS devices were not tested.

## Backlog
- P1: device-test native photo/attachment loading and PDF sharing after `npx cap sync`.
- P2: show the member photo in the drawer header; make DateField clearable in Export Center.



## Marketing ad videos — 2026-11-02
- User request: "make a video for gym boss that looks like a good ad with the attached avatar as the gym boss". Choices: motion-graphics ad that explains all features; both Wide 16:9 ~30s and Vertical 9:16 ~20s; AI voiceover plus music; brand fun plus a gym-owner feature message; default end card ("Start your free trial", no website).
- Outputs: /app/frontend/public/ad/GymBoss_Ad_16x9_30s.mp4 (1920x1080, 30s) and GymBoss_Ad_9x16_20s.mp4 (1080x1920, 20s), H.264 yuv420p + AAC.
- Pipeline in /app/ad: AI-generated panda poses based on the user's character sheet, backgrounds removed with rembg (isnet-anime); real app screenshots from the demo account (capture.py); HTML/JS motion composition (ad.html, ad.js, ?fmt=wide|vertical) rendered frame by frame with Playwright, then ffmpeg (render.py); OpenAI TTS tts-1-hd "ash" voice (tts.py, fix_vo.py); original synthesized music (music.py); audio remix with ducking (remix.py).
- Verified: Whisper transcripts of both final tracks match the scripts; key frames were reviewed visually.
- Backlog: add a website URL or offer to the end card; Hindi voiceover version; square 1:1 feed cut.


## Google Play listing assets — 2026-11-02
- User request: "create a proper assets for me to have in the google playstore before they download the app". Screenshot priorities: Dashboard and collections, Member management, Attendance and QR check-in, Plans and renewals, Payment recording and dues, Reports, Staff access, Subscription plans. Choices: framed screenshots with headline and panda; Subscription plans left out; feature graphic 1024x500; captions combine a clear benefit with a panda catchphrase.
- Outputs in /app/frontend/public/playstore/: 7 phone screenshots (1080x1920, 24-bit PNG), feature_graphic_1024x500.png, and GymBoss_PlayStore_Assets.zip.
- Method: a temporary backend on port 8002 used an isolated DB (gymboss_store_demo) seeded with a sample gym, "Peak Fitness Studio" (owner "Rohan Mehta", 32 sample members). The real mobile app was screenshotted through Playwright API routing, then framed in /app/ad/store/store.html (render_store.py). The temporary DB and server were removed afterwards; the customer's DB was not touched.

## Marketing Reels (Nov 2026)
- 3 vertical 9:16 reels (~20s each), every one opening with a 4-second hook, English AI voiceover, music + sound effects, ending on "Start your free trial".
  - Reel 1 Fee Chase (funny: angry panda + flood of excuse chats)
  - Reel 2 Money Leak (money stat: ₹40,000 stuck/month from 20 late payers × ₹2,000)
  - Reel 3 Midnight Register (funny: tired panda doing accounts at 11:47 PM)
- Output: /app/ad/reels/ (+ GymBoss_Reels.zip). Code: /app/ad/reels.js (scenes), reels_tts.py, sfx.py, render.py `vertical - <reel#>`.
- New panda poses: angry, tired, shocked, confused, cash (assets/cut/).

## Panda Comedy Series (Nov 2026) – mascot-led, Duolingo-style
- 3 AI-animated reels (Kling v3 image-to-video via the Universal Key; start frames made with Gemini image generation), each ~18s at 9:16 and 24fps, each in a different visual world:
  - Ep1 "Six Tomorrows" – 80s retro pastel/neon, sarcastic panda voice (onyx), app punchline + free trial CTA
  - Ep2 "Missing Cash" – film noir teal, meme captions + noir jazz, no voice, logo-only ending
  - Ep3 "Planet Gym" – pastel savanna nature-doc parody, British narrator (fable), app punchline + free trial CTA
- Output: /app/ad/series/final/ (+ GymBoss_Panda_Series.zip). Pipeline: series/kling.py (clips), voices.py, music.py (synth music + sfx), render_series.py (captions, end cards, grade, mix).

## Planet Gym Season 1 (Nov 2026)
- 4 nature-doc parody episodes (~23s, 9:16, 24fps), each with a 4-shot story (Kling v2.6 Pro, picked after an A/B test against v3 Pro: same 1176x1756 output, half the price), British narrator, music + ambience made for each world, a hook caption in the first 4s, species lower-thirds, and branded end cards.
  - Ep1 The Wild Gym Owner (savanna, app CTA) – remake of the earlier episode with a new "collapse" shot
  - Ep2 The January Migration (arctic aurora, logo only)
  - Ep3 The Ghost Member (moonlit forest, app CTA)
  - Ep4 The Protein Shake Addict (neon rainforest + chocolate shake falls, logo only)
- Output: /app/ad/series/planet_gym/ (+ PlanetGym_Season1.zip). Pipeline: pg_kling.py, pg_voices.py, pg_music.py, pg_render.py.
- Audio pass: narrator switched to deep calm "onyx" (speed 0.92), cleaned up like broadcast audio (EQ, de-ess, compression, limiter, light room); music cut to about a third, ambience low, ducking under the voice; mixed to -14 LUFS with a fixed gain. Speech sits about 17 dB above the bed. Script: series/pg_remix.py (audio only, video copied). Old fable voice lines are in audio/fable_backup/.

## Screen-Recorded Tutorial (Nov 2026)
- Full 16:9 walkthrough (9:19, 1920x1080, 25fps) on the real web app with the demo account, plus 16 chapter clips, an .srt subtitle file and YouTube chapter timestamps. Friendly "nova" voice, captions, chapter cards, smooth zoom on taps, a visible cursor with click ripples.
- Covers: sign in, dashboard, plans, add member (plan + payment), record payment + receipt, attendance (manual/QR/staff/history), outstanding dues, renewal, WhatsApp reminders + custom holiday message (shown honestly as one-by-one via the owner's WhatsApp), freeze, enquiries, expenses, staff, outlets, finance, reports + monthly PDF, export center, settings/theme/integrations, subscription, help, profile, then the dashboard at end of day.
- Announcements left hidden at the user's request (the page exists in code but isn't routed). Demo data restored after recording (tutorial/snapshot.py).
- Output: /app/ad/tutorial/final/ (GymBoss_Tutorial.zip). Pipeline: tutorial/steps.py (script), vo.py, rec.py (Playwright + CDP capture), compose.py.
