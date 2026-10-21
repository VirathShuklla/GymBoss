# GymBoss_VVO — Store Billing Compliance Assessment (June 2026)

Not legal advice. Policies were checked against official pages on the assessment date. Re-verify before each submission.

## Product facts
- B2B SaaS sold by BuildVVO Technologies Pvt Ltd (India) to gym businesses. One organisation account has an owner plus multiple staff logins.
- ₹999/month (plus quarterly/half-yearly/yearly) via Razorpay Subscriptions (auto-debit) or one-time Razorpay orders. 14-day free trial, then read-only.
- Store apps: Android = PWABuilder TWA wrapping `/m`. iOS = Capacitor wrapping `/m`. Single FastAPI + MongoDB backend and entitlement source (`organisations.subscription`).

## Android — Google Play
**Policy:** Google Play Payments policy: https://support.google.com/googleplay/android-developer/answer/9858738
- §2: in-app purchases of features/services must use Google Play Billing. The examples explicitly include "subscription services" and "cloud software and services (such as … business productivity software …)".
- §3: the exemption for "physical services (such as … gym memberships …)" covers a gym selling memberships to its own members. It does **not** cover GymBoss's SaaS fee. Neither section has a B2B/enterprise exemption.
- §4: apps may not lead users to other payment methods (buttons, links, webviews, sign-up flows) except under §8/§9 programs.
- §6: pricing and terms must be clear and accurate.

**Conclusion:** Showing the Razorpay subscription checkout (or a link to it) inside the Play app is **not compliant** today.

**Compliant options:**
1. **Consumption-only app (no purchase in app).** No prices, no buy buttons, no links or instructions to pay elsewhere. Existing subscribers sign in, and the entitlement comes from our backend. This is allowed because §2 applies only to apps that *require or accept* payment in the app.
2. **India user choice billing.** Program page: https://support.google.com/googleplay/android-developer/answer/13306652 and the programs overview: https://support.google.com/googleplay/android-developer/answer/13821247
   - Google Play Billing **must be offered alongside** Razorpay. There is no "alternative-only" program in India (that exists only in the EEA).
   - The service fee is reduced by 4% (≈11% instead of 15% on subscriptions) when the user picks Razorpay. Razorpay's ~2% fee comes on top.
   - Requirements:
     - Enrol in Play Console (Settings → Alternative billing) and accept the program terms.
     - Attest PCI DSS compliance and give users a way to report fraud.
     - Integrate the alternative billing APIs, which render the user-choice screen.
     - Report every transaction within 24 hours via the ExternalTransactions API.
     - Set a subscription management URL in Play Console.
     - Pay invoiced fees.
   - Technical: needs the native Play Billing Library (UserChoiceBilling). The current PWABuilder TWA only supports Play Billing through the Digital Goods API, and its support for the user-choice APIs is unverified. Realistically this means a native Android build (e.g. Capacitor Android plus a Play Billing plugin), a Google Play Developer API service account, Real-time Developer Notifications (Pub/Sub → our webhook), purchase verification and acknowledgement, and ExternalTransactions reporting.

## iOS — Apple App Store
**Policy:** App Review Guidelines: https://developer.apple.com/app-store/review/guidelines/ (Last Updated Oct 16, 2026)
- 3.1.1: digital features/subscriptions unlocked in-app must use In-App Purchase. Buttons, links or calls to action to other purchase methods are prohibited outside storefronts with an entitlement.
- **3.1.3(c) Enterprise Services:** "If your app is only sold by you directly to organizations or groups for their employees or students (for example professional databases and classroom management tools), you may allow enterprise users to access previously purchased content or subscriptions. Consumer, single user, or family sales must use in-app purchase." (Re-check the exact wording on the live page.)
- 3.1.3(b) Multiplatform Services: users may access subscriptions acquired on our website.
- External Purchase Link entitlement storefronts: EU, Japan, Brazil (with IAP alongside); the US allows links without an entitlement. **India is not eligible.** https://developer.apple.com/documentation/storekit/external-purchase

**3.1.3(c) eligibility for GymBoss:**
- *For:* sold to businesses (gyms), not consumers. Multi-seat organisation accounts (owner plus staff). The fitness-club members never pay us. This is business-management software.
- *Against / risk:*
  - Self-serve signup by any individual. Many customers are sole-proprietor gyms, which App Review may treat as "single user".
  - The pricing is public and consumer-style.
  - The wording "access previously purchased" implies the purchase happens **outside** the app. So 3.1.3(c) is a basis for *sign-in and access*, not clearly for an in-app Razorpay checkout.
- **Assessment:** GymBoss is **likely eligible to let organisation users sign in and use subscriptions bought on the website** (3.1.3(b)/(c)). It is **not safe** to show Razorpay checkout or a website-purchase link/CTA in the Indian App Store build. Do not add Apple IAP unless App Review rejects the 3.1.3(c) position. Explain the B2B model in the Review Notes and supply a demo org account.

## Current-state audit (gaps found in code)
| # | Gap | Risk |
|---|-----|------|
| 1 | In-app detection relies on `?app=1` / TWA referrer / `window.Capacitor`, with no explicit store-build flag and no platform reported to the backend | Wrapper may show Razorpay if detection fails |
| 2 | `ExpiredBanner` and `TrialBanner` in `/m` show "₹999/month" and a "Reactivate"/"Upgrade" CTA even in in-app mode | Google §4 and Apple 3.1.1 violation (price + CTA) |
| 3 | Mobile Profile shows the plan picker with prices in in-app mode, and the note says it is "managed … on our website" | Steering language (Apple 3.1.1) |
| 4 | The wrapper can navigate to `/`, `/pricing` and `/app/subscription` (web pages with Razorpay) | Purchase flow reachable inside the store app |
| 5 | Webhook handles activated/charged/halted/cancelled/completed and payment.captured/failed, but not `subscription.pending`, `subscription.paused`/`resumed` or `subscription.updated`. There is no reconciliation job | Renewal/failed-payment status can drift |
| 6 | The web checkout has no explicit auto-renew disclosure (renewal period, amount, auto-renews until cancelled, how to cancel) next to the pay button | Consumer-protection / RBI e-mandate transparency |

## Proposed changes (pending approval)
**Phase 1 — "Consumption-only" store builds (recommended now, no payment-architecture change)**
- A single platform resolver (`web` | `android_store` | `ios_store`), set reliably. Android TWA start_url `/m?src=play`, iOS Capacitor via `Capacitor.getPlatform()`. It persists and is sent as an `X-Client-Platform` header. The backend refuses to create Razorpay orders/subscriptions from store clients (defence in depth).
- In store builds:
  - No prices, plan picker, upgrade/reactivate CTAs, or "pay on website" wording anywhere.
  - Expired accounts see a neutral "Your organisation's subscription is not active" message.
  - Routes that sell are blocked (`/`, `/pricing`, `/app/subscription`) and redirect to `/m`.
- Web is unchanged: Razorpay stays exactly as is.
- Sync hardening:
  - Handle the `subscription.pending`, `paused`, `resumed` and `updated` webhooks, and record failed renewals.
  - Daily reconciliation cron that fetches Razorpay subscription status for active/pending orgs.
- Clear web pricing disclosure at checkout and in Terms: amount, period, auto-renews until cancelled, cancel anytime in Profile (access continues to the end of the period), and what happens on a failed payment.
- App Review notes text plus demo account, explaining the 3.1.3(b)/(c) B2B position.

**Phase 2 — Android India user choice billing (optional, needs approval and inputs)**
- Native Android build, Play Billing Library user-choice flow, Google Play Developer API service account, RTDN Pub/Sub, ExternalTransactions reporting.
- Google Play products mapped to the same `organisations.subscription` entitlement.
- Inputs required: Play Console enrolment, a service-account JSON, a PCI DSS attestation, and a fee decision (≈15% via Play / ≈11% + Razorpay via choice).

**Phase 3 — iOS IAP (only if Apple rejects 3.1.3(c))**
- StoreKit 2 auto-renewable subscription, App Store Server API plus Server Notifications v2, mapped to the same entitlement.
