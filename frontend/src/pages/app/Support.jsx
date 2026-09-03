import { useState } from "react";
import { MessageCircle, Mail, Loader2, LifeBuoy } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { usePublicConfig, waLink } from "../../hooks/usePublicConfig";
import { PageHeader } from "../../components/app/ui";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";

export default function Support() {
  const config = usePublicConfig();
  const [form, setForm] = useState({ subject: "", message: "" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/support/requests", form);
      toast.success("Support request submitted. The BuildVVO team will reach out.");
      setForm({ subject: "", message: "" });
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="support-page">
      <PageHeader title="Help & Support" subtitle="We're here to help you run your gym." testid="support-header" />
      <div className="grid max-w-4xl gap-5 lg:grid-cols-2">
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="support-whatsapp-card">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#25D366]/12 text-[#25D366]"><MessageCircle className="h-5 w-5" /></div>
            <p className="mt-3 font-display text-base font-bold text-foreground">WhatsApp Support</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {config?.whatsapp_number ? "Chat directly with the BuildVVO team." : "The BuildVVO team is setting this up — raise a request and we'll reach out."}
            </p>
            {config?.whatsapp_number && (
              <a href={waLink(config.whatsapp_number, "Hi, I need help with GymBoss_VVO.")} target="_blank" rel="noopener noreferrer" data-testid="support-whatsapp-link"
                 className="mt-4 inline-block rounded-lg bg-[#25D366] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#1fb857]">
                Chat on WhatsApp
              </a>
            )}
          </div>
          <div className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="support-email-card">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand/12 text-brand"><Mail className="h-5 w-5" /></div>
            <p className="mt-3 font-display text-base font-bold text-foreground">Email Support</p>
            {config?.support_email ? (
              <a href={`mailto:${config.support_email}`} className="mt-1 block text-sm font-semibold text-brand hover:underline" data-testid="support-email-link">{config.support_email}</a>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">Support email will be published by BuildVVO shortly.</p>
            )}
          </div>
        </div>
        <form onSubmit={submit} className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="support-request-form">
          <div className="flex items-center gap-2.5">
            <LifeBuoy className="h-5 w-5 text-brand" />
            <p className="font-display text-base font-bold text-foreground">Raise a Support Request</p>
          </div>
          <div className="mt-4 space-y-4">
            <div className="space-y-1.5"><Label>Subject</Label><Input required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="What do you need help with?" data-testid="support-subject" /></div>
            <div className="space-y-1.5"><Label>Message</Label><Textarea required rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Describe your issue or question" data-testid="support-message" /></div>
            <Button className="w-full bg-brand hover:bg-brand-hover" disabled={busy} data-testid="support-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Submit Request
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
