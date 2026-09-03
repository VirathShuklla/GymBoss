import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "../ui/accordion";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";

export function Faq() {
  const config = usePublicConfig();
  const price = inr(config?.plan_price_inr || 999);
  const FAQS = [
    { q: "Is GymBoss_VVO free?", a: `GymBoss_VVO includes a full-feature 10-day free trial. After the trial, the plan costs ${price}/month per gym.` },
    { q: "Is a credit card required for the trial?", a: "No. You can start your 10-day free trial without sharing any payment details." },
    { q: "Can I manage multiple gym locations?", a: "Yes. GymBoss_VVO is built multi-outlet from day one — add branches, switch between them, and view outlet-wise data from a single account." },
    { q: "Can my staff use GymBoss_VVO?", a: "Yes. Owners can create staff accounts for managers, receptionists, trainers and sales teams with role-based permissions." },
    { q: "Can I import my existing member data?", a: "Yes. CSV import support is built into the platform so you can bring your existing member records with validation before import." },
    { q: "Can I send WhatsApp reminders?", a: "Yes. You can message individual members instantly via click-to-WhatsApp. Bulk and automated messaging works through the official WhatsApp Business API once configured in Settings → Integrations." },
    { q: "Will my data be lost if my trial ends?", a: "No. Your data is never deleted when a trial expires. Access is paused until you subscribe, and everything is exactly where you left it." },
    { q: "Is there technical support?", a: "Yes. The BuildVVO team is available over WhatsApp and email. You can also raise support requests from inside the app." },
  ];
  return (
    <section id="faq" className="bg-slate-50 py-20 sm:py-28" data-testid="faq-section">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Frequently Asked <span className="text-brand">Questions</span>
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">Everything you need to know about GymBoss_VVO.</p>
        </div>
        <Accordion type="single" collapsible className="mt-12">
          {FAQS.map((f, i) => (
            <AccordionItem key={f.q} value={`faq-${i}`} className="border-slate-200" data-testid={`faq-item-${i}`}>
              <AccordionTrigger className="text-left font-display text-base font-bold text-slate-900 hover:no-underline">
                {f.q}
              </AccordionTrigger>
              <AccordionContent className="text-sm leading-relaxed text-slate-600">{f.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
