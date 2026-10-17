export const COMPANY = "BuildVVO Technologies Private Limited";
export const CONTACT_EMAIL = "buildvvotechnologies@gmail.com";
export const UPDATED = "June 2026";

export const LEGAL = {
  privacy: {
    title: "Privacy Policy",
    intro: `This Privacy Policy explains how ${COMPANY} ("BuildVVO", "we", "us") collects, uses and protects information when you use GymBoss_VVO on the web, as an installed app, or through our Android and iOS apps. We process personal data in line with India's Digital Personal Data Protection Act, 2023 and the Information Technology Act, 2000.`,
    sections: [
      ["Information we collect", [
        "Account data: your name, email address, mobile number, gym name, outlet and city, and a securely hashed password (we never store your password in readable form).",
        "Gym data you enter: member profiles, photos and documents you upload, plans, payments, attendance, enquiries, expenses and staff records.",
        "Billing data: subscription status and transaction references from our payment partner Razorpay. Card, UPI and bank details are handled by Razorpay and are never stored on our servers.",
        "Usage data: basic, first-party product analytics (for example pages visited and features used) collected only by us to improve GymBoss_VVO. We do not use third-party advertising trackers.",
        "Device data: browser or device type and IP address, used for security, fraud prevention and login protection.",
      ]],
      ["How we use information", [
        "To provide, operate and secure the service, including login, password reset and account recovery.",
        "To process subscription payments and send service communications such as password reset emails.",
        "To provide customer support and respond to your requests.",
        "To improve product features and reliability using aggregated usage data.",
        "To comply with legal obligations.",
      ]],
      ["Your gym's member data", [
        "Gym owners are the data fiduciary for the member data they enter. BuildVVO processes it only on your behalf to run the service.",
        "We never sell member data or use it for advertising. WhatsApp messages are sent from your own device using click-to-chat links.",
      ]],
      ["Sharing", [
        "We share data only with service providers who help us run GymBoss_VVO (cloud hosting, file storage, email delivery and Razorpay for payments), under confidentiality obligations.",
        "We may disclose information if required by law or to protect the rights and safety of our users.",
      ]],
      ["Security & storage", [
        "Data is encrypted in transit (HTTPS). Passwords are hashed with bcrypt. Each gym's data is isolated from every other gym.",
        "We retain your data while your account is active. If your trial or subscription ends, your data is kept safely in read-only mode so you can reactivate at any time.",
      ]],
      ["Your rights & account deletion", [
        "You can access and correct your account details from My Profile, and export your gym data from the Export Center.",
        `To delete your account and all associated data, email ${CONTACT_EMAIL} from your registered email address with the subject "Delete my account". We will complete deletion within 30 days, except where retention is required by law.`,
        "You may withdraw consent or raise a grievance at any time by contacting us.",
      ]],
      ["Children", [
        "GymBoss_VVO is a business tool for gym owners and staff and is not directed at children under 18.",
      ]],
      ["Changes & contact", [
        "We may update this policy from time to time. Significant changes will be notified in the app or by email.",
        `Grievance Officer / Contact: ${COMPANY}, India — ${CONTACT_EMAIL}.`,
      ]],
    ],
  },
  terms: {
    title: "Terms of Service",
    intro: `These Terms of Service ("Terms") govern your use of GymBoss_VVO, provided by ${COMPANY}, India. By creating an account or using the service you agree to these Terms.`,
    sections: [
      ["Your account", [
        "You must provide accurate information and be at least 18 years old to create an account.",
        "You are responsible for keeping your password confidential and for all activity under your account and your staff logins. Tell us immediately if you suspect unauthorised access.",
      ]],
      ["Free trial & subscription", [
        "New gyms get a free trial for the period shown at signup, with no card required.",
        "After the trial, continued write access requires a paid subscription at the price shown in the app. Subscriptions may renew automatically via Razorpay until cancelled.",
        "If you do not subscribe, your account becomes read-only. Your data is not deleted.",
        "You can cancel auto-renewal at any time from My Profile. Access continues until the end of the paid period. Fees already paid are non-refundable except where required by law.",
      ]],
      ["Acceptable use", [
        "Use GymBoss_VVO only for lawful gym management. Do not misuse the service, attempt to access other gyms' data, interfere with security, or send spam through WhatsApp links.",
        "You must have the right to upload and process the member data and photos you add, including any consent required from your members.",
      ]],
      ["Your data", [
        "You own your gym's data. You grant us a limited licence to host and process it solely to provide the service.",
        "You can export your data at any time from the Export Center.",
      ]],
      ["Service availability", [
        "We work hard to keep GymBoss_VVO fast and available, but the service is provided \"as is\" without warranties of uninterrupted operation.",
        "We may update features over time. We will give reasonable notice of material changes.",
      ]],
      ["Liability", [
        `To the maximum extent permitted by law, ${COMPANY} is not liable for indirect or consequential losses. Our total liability is limited to the fees you paid in the 3 months before the claim.`,
      ]],
      ["Termination", [
        "You may stop using the service at any time and request account deletion. We may suspend accounts that violate these Terms.",
      ]],
      ["Governing law & contact", [
        "These Terms are governed by the laws of India, and courts in India have exclusive jurisdiction.",
        `Questions? Contact ${COMPANY} at ${CONTACT_EMAIL}.`,
      ]],
    ],
  },
};
