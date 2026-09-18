import { useState } from "react";
import { X, Printer, MessageCircle } from "lucide-react";
import { inr, formatDate, formatPhone } from "../../lib/format";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Logo } from "../Logo";
import { waMe, buildReceiptMessage } from "../../lib/whatsapp";

export function ReceiptModal({ receipt, onClose }) {
  if (!receipt) return null;
  const { payment, member, gym, outlet } = receipt;
  return (
    <Dialog open={Boolean(receipt)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="receipt-modal">
        <DialogTitle className="sr-only">Payment Receipt</DialogTitle>
        <div id="receipt-print" className="rounded-lg border border-border p-6">
          <div className="flex items-center justify-between">
            <Logo />
            <span className="font-num text-xs text-muted-foreground">{payment.receipt_no}</span>
          </div>
          <h3 className="mt-5 text-center font-display text-lg font-bold text-foreground">Payment Receipt</h3>
          <p className="text-center text-xs text-muted-foreground">{gym?.name}{outlet?.name ? ` — ${outlet.name}` : ""}{gym?.city ? `, ${gym.city}` : ""}</p>
          <div className="mt-5 space-y-2.5 border-t border-dashed border-border pt-4 text-sm">
            <Row label="Member" value={member?.full_name} />
            <Row label="Member ID" value={member?.member_code} />
            <Row label="Phone" value={formatPhone(member?.phone)} />
            <Row label="Payment Date" value={formatDate(payment.created_at)} />
            <Row label="Plan / Item" value={payment.plan_name} />
            <Row label="Payment Type" value={payment.type === "admission" ? "Admission" : payment.type === "renewal" ? "Renewal" : "Due Payment"} />
            <Row label="Payment Method" value={payment.method} />
            <Row label="Valid Until" value={formatDate(member?.membership_expiry)} />
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-dashed border-border pt-4">
            <span className="font-display text-sm font-bold text-foreground">Amount Paid</span>
            <span className="font-num text-xl font-extrabold text-success" data-testid="receipt-amount">{inr(payment.amount)}</span>
          </div>
          {member?.due_amount > 0 && (
            <div className="mt-1 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Outstanding</span>
              <span className="font-num font-bold text-danger">{inr(member.due_amount)}</span>
            </div>
          )}
          <p className="mt-5 text-center text-[11px] text-muted-foreground">Thank you for training with {gym?.name}. Powered by GymBoss_VVO.</p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="outline" onClick={onClose} data-testid="receipt-close"><X className="mr-1.5 h-4 w-4" />Close</Button>
          {member?.phone && (
            <Button className="bg-[#25D366] text-white hover:bg-[#1fb857]" onClick={() => window.open(waMe(member.phone, buildReceiptMessage(receipt)), "_blank")} data-testid="receipt-whatsapp-button">
              <MessageCircle className="mr-1.5 h-4 w-4" />Send on WhatsApp
            </Button>
          )}
          <Button className="bg-brand hover:bg-brand-hover" onClick={() => window.print()} data-testid="receipt-print-button">
            <Printer className="mr-1.5 h-4 w-4" />Print / Download
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value || "—"}</span>
    </div>
  );
}
