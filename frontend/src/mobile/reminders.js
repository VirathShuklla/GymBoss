import { Clock, IndianRupee, FileText } from "lucide-react";
import { inr } from "../lib/format";

const msgDate = (d) => {
  if (!d) return "—";
  const dt = new Date(`${String(d).slice(0, 10)}T00:00:00`);
  return dt.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" });
};

export function buildReminderOptions(member, gymName = "Your Gym", payments) {
  if (!member) return [];
  const firstName = (member.full_name || "").split(" ")[0];
  const expiry = msgDate(member.membership_expiry);
  const sorted = [...(payments || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  const latest = sorted[0];
  const expired = member.days_left != null && member.days_left < 0;
  const options = [];

  if (member.membership_expiry) {
    options.push({
      key: "expiry",
      icon: Clock,
      tile: "bg-warning/12 text-warning",
      title: "Send Expiry Reminder",
      desc: expired ? "Membership has expired — request renewal" : "Remind about upcoming expiry",
      message: expired
        ? `Dear ${firstName},\n\nOur records show that your ${member.plan_name} membership at ${gymName} expired on ${expiry}.\n\nWe would love to see you back — kindly renew your membership to resume your training without any further gap.\n\nWarm regards,\n${gymName}`
        : `Dear ${firstName},\n\nThis is a gentle reminder from ${gymName} that your ${member.plan_name} membership is due to expire on ${expiry}.\n\nTo continue enjoying uninterrupted access to the gym, kindly renew before the expiry date.\n\nWarm regards,\n${gymName}`,
    });
  }
  if (member.due_amount > 0) {
    options.push({
      key: "payment",
      icon: IndianRupee,
      tile: "bg-danger/12 text-danger",
      title: "Send Payment Reminder",
      desc: `Outstanding balance of ${inr(member.due_amount)}`,
      message: `Dear ${firstName},\n\nWe hope you are doing well. Our records show an outstanding balance of ${inr(member.due_amount)} against your ${member.plan_name} membership at ${gymName}, valid until ${expiry}.\n\nKindly clear the pending amount at your earliest convenience.\n\nIf you have already paid, please disregard this message.\n\nWarm regards,\n${gymName}`,
    });
  }
  if (latest) {
    options.push({
      key: "invoice",
      icon: FileText,
      tile: "bg-brand/12 text-brand",
      title: "Send Invoice",
      desc: "Send the latest invoice via WhatsApp",
      message: `Dear ${firstName},\n\nThank you for your payment towards your ${latest.plan_name || member.plan_name} membership at ${gymName}.\n\nInvoice Summary\n• Receipt No: ${latest.receipt_no}\n• Payment Date: ${msgDate(latest.payment_date || latest.created_at)}\n• Amount Paid: ${inr(latest.amount)}\n• Balance Due: ${member.due_amount > 0 ? inr(member.due_amount) : "Nil"}\n• Valid Until: ${expiry}\n\nPlease keep this message as confirmation of your payment.\n\nWarm regards,\n${gymName}`,
    });
  }
  return options;
}
