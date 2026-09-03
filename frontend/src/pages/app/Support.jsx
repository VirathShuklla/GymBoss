import { MessageCircle, Mail } from "lucide-react";
import { usePublicConfig, waLink } from "../../hooks/usePublicConfig";
import { PageHeader } from "../../components/app/ui";

export default function Support() {
  const config = usePublicConfig();

  return (
    <div data-testid="support-page">
      <PageHeader title="Help & Support" subtitle="We're here to help you run your gym." testid="support-header" />
      <div className="grid max-w-3xl gap-5 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="support-whatsapp-card">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#25D366]/12 text-[#25D366]"><MessageCircle className="h-5 w-5" /></div>
          <p className="mt-3 font-display text-base font-bold text-foreground">WhatsApp Support</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {config?.whatsapp_number ? "Chat directly with the BuildVVO team." : "The BuildVVO team is setting this up — check back shortly."}
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
    </div>
  );
}
