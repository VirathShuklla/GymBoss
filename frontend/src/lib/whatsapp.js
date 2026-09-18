export const waMe = (phone, message) =>
  `https://wa.me/${String(phone || "").replace(/\D/g, "")}${message ? `?text=${encodeURIComponent(message)}` : ""}`;

export const fillTemplate = (tpl, vars) =>
  tpl.replace(/{(\w+)}/g, (_, k) => (vars[k] != null && vars[k] !== "" ? String(vars[k]) : `{${k}}`));

export const WA_TEMPLATES = [
  { key: "welcome", label: "Welcome", body: "Hi {member_name}, welcome to {gym_name}! We're excited to have you train with us. Reach out anytime you need help." },
  { key: "payment_reminder", label: "Payment Reminder", body: "Hi {member_name}, this is a friendly reminder from {gym_name} that a payment of {due_amount} is pending on your membership. Please clear it at your earliest convenience. Thank you!" },
  { key: "expiring", label: "Membership Expiring", body: "Hi {member_name}, your {plan_name} membership at {gym_name} expires on {expiry_date}. Renew soon to keep your training uninterrupted!" },
  { key: "expired", label: "Membership Expired", body: "Hi {member_name}, your {gym_name} membership expired on {expiry_date}. Visit us or reply here to renew and resume your workouts." },
  { key: "birthday", label: "Birthday Wish", body: "Happy Birthday, {member_name}! Wishing you a year of strength and great health — from all of us at {gym_name}." },
  { key: "follow_up", label: "Enquiry Follow-Up", body: "Hi {member_name}, thanks for your interest in {gym_name}! We'd love to help you get started. When would be a good time to talk?" },
  { key: "custom", label: "Custom Message", body: "" },
];

const _rdate = (v) =>
  v ? new Date(`${String(v).slice(0, 10)}T00:00:00`).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
const _rupee = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

export const buildReceiptMessage = ({ payment, member, gym } = {}) => {
  const first = (member?.full_name || "").split(" ")[0] || "Member";
  const gymName = gym?.name || "our gym";
  const lines = [
    `Dear ${first},`,
    "",
    `Thank you for your payment at ${gymName}. Here is your receipt:`,
    "",
    `Receipt No: ${payment?.receipt_no || "—"}`,
    `Date: ${_rdate(payment?.created_at)}`,
    `Plan / Item: ${payment?.plan_name || member?.plan_name || "Membership"}`,
    `Amount Paid: ${_rupee(payment?.amount)}`,
    `Payment Mode: ${payment?.method || "—"}`,
  ];
  if ((member?.due_amount || 0) > 0) lines.push(`Balance Due: ${_rupee(member.due_amount)}`);
  lines.push(
    `Valid Until: ${_rdate(member?.membership_expiry)}`,
    "",
    "Please keep this message as your payment confirmation.",
    "",
    "Warm regards,",
    gymName,
  );
  return lines.join("\n");
};
