import { useMemo, useState } from "react";
import { Clock, FileText, IndianRupee, ChevronRight, ChevronLeft, MessageCircle } from "lucide-react";
import { inr } from "../../lib/format";
import { waMe } from "../../lib/whatsapp";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";

const msgDate = (d) => {
  if (!d) return "—";
  const dt = new Date(`${String(d).slice(0, 10)}T00:00:00`);
  return dt.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" });
};

function buildOptions(member, gymName, payments) {
  const firstName = member.full_name.split(" ")[0];
  const expiry = msgDate(member.membership_expiry);
  const sorted = [...(payments || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  const latest = sorted[0];
  const daysLeft = member.days_left;
  const expired = daysLeft != null && daysLeft < 0;
  const options = [];

  if (member.membership_expiry) {
    options.push({
      key: "expiry",
      icon: Clock,
      tile: "bg-warning/12 text-warning",
      title: "Send Expiry Reminder",
      desc: expired ? "Membership has expired — request renewal" : "Remind about upcoming membership expiry",
      message: expired
        ? `Dear ${firstName},

Our records show that your ${member.plan_name} membership at ${gymName} expired on ${expiry}.

We would love to see you back — kindly renew your membership to resume your training without any further gap.

We would be happy to assist you at the front desk.

Warm regards,
${gymName}`
        : `Dear ${firstName},

This is a gentle reminder from ${gymName} that your ${member.plan_name} membership is due to expire on ${expiry}.

To continue enjoying uninterrupted access to the gym, we kindly request you to renew your membership before the expiry date.

We would be happy to assist you at the front desk.

Warm regards,
${gymName}`,
    });
  }
  if (member.due_amount > 0) {
    options.push({
      key: "payment",
      icon: IndianRupee,
      tile: "bg-danger/12 text-danger",
      title: "Send Payment Reminder",
      desc: `Outstanding balance of ${inr(member.due_amount)}`,
      message: `Dear ${firstName},

We hope you are doing well. Our records show an outstanding balance of ${inr(member.due_amount)} against your ${member.plan_name} membership at ${gymName}, valid until ${expiry}.

Kindly clear the pending amount at your earliest convenience to keep your membership in good standing.

If you have already made the payment, please disregard this message.

Warm regards,
${gymName}`,
    });
  }
  if (latest) {
    options.push({
      key: "invoice",
      icon: FileText,
      tile: "bg-brand/12 text-brand",
      title: "Send Invoice",
      desc: "Send the latest invoice via WhatsApp",
      message: `Dear ${firstName},

Thank you for your payment towards your ${latest.plan_name || member.plan_name} membership at ${gymName}.

Invoice Summary
• Receipt No: ${latest.receipt_no}
• Payment Date: ${msgDate(latest.payment_date || latest.created_at)}
• Amount Paid: ${inr(latest.amount)}
• Balance Due: ${member.due_amount > 0 ? inr(member.due_amount) : "Nil"}
• Membership Valid Until: ${expiry}

Please keep this message as confirmation of your payment.

Warm regards,
${gymName}`,
    });
  }
  return options;
}

export function ReminderModal({ member, gymName, payments, open, onClose }) {
  const [selected, setSelected] = useState(null);
  const options = useMemo(
    () => (member ? buildOptions(member, gymName || "Your Gym", payments) : []),
    [member, gymName, payments]
  );

  const close = () => {
    setSelected(null);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && close()}>
      <DialogContent className="max-w-sm p-0" data-testid="reminder-modal">
        <DialogTitle className="sr-only">WhatsApp Reminder</DialogTitle>
        <div className="flex items-center justify-between border-b border-border px-5 py-4 pr-12">
          <h3 className="font-display text-base font-bold text-foreground">WhatsApp Reminder</h3>
        </div>
        {!selected ? (
          <div className="p-4">
            <p className="mb-3 text-sm text-muted-foreground">Select the type of reminder to send{member ? ` to ${member.full_name}` : ""}:</p>
            <div className="space-y-2.5">
              {options.map((opt) => (
                <button key={opt.key} onClick={() => setSelected(opt)} data-testid={`reminder-option-${opt.key}`}
                        className="flex w-full items-center gap-3.5 rounded-xl border border-border px-4 py-3.5 text-left transition-all hover:border-brand/50 hover:bg-brand/5">
                  <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${opt.tile}`}>
                    <opt.icon className="h-5 w-5" />
                  </span>
                  <span className="flex-1">
                    <span className="block text-sm font-bold text-foreground">{opt.title}</span>
                    <span className="block text-xs text-muted-foreground">{opt.desc}</span>
                  </span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </button>
              ))}
              {options.length === 0 && (
                <p className="py-6 text-center text-sm text-muted-foreground">No reminders available for this member.</p>
              )}
            </div>
          </div>
        ) : (
          <div className="p-4">
            <button onClick={() => setSelected(null)} className="mb-3 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground" data-testid="reminder-back">
              <ChevronLeft className="h-3.5 w-3.5" />Back
            </button>
            <p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">{selected.title} — preview</p>
            <div className="whitespace-pre-line rounded-xl rounded-tl-sm border border-border bg-secondary/50 p-4 text-sm leading-relaxed text-foreground" data-testid="reminder-preview">
              {selected.message}
            </div>
            <a href={waMe(member.phone, selected.message)} target="_blank" rel="noopener noreferrer" onClick={close}
               className="mt-4 flex w-full items-center justify-center rounded-lg bg-[#25D366] py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#1fb857]"
               data-testid="reminder-send">
              <MessageCircle className="mr-2 h-4 w-4" />Send via WhatsApp
            </a>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
