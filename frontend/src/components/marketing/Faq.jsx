import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "../ui/accordion";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";

export function Faq() {
  const config = usePublicConfig();
  const price = inr(config?.plan_price_inr || 999);
  const FAQS = [
    { q: "How much does it cost after the trial?", a: `Plans start at ${price}/month, with lower monthly prices on quarterly and yearly plans. Every plan includes every feature, with no per-member fees.` },
    { q: "Is a credit card required for the trial?", a: "No. You can start your 10-day free trial without sharing any payment details." },
    { q: "What happens to my data if I stop paying?", a: "Nothing is deleted. You can still log in and view all your members, payments and attendance. Adding or editing is paused until you reactivate." },
    { q: "I'm not good with technology. Will I manage?", a: "Yes. If you can use WhatsApp, you can use GymBoss. Our team can also help you set up over WhatsApp." },
    { q: "Can I manage more than one branch?", a: "Yes. Add all your branches to one account and switch between them, or see everything together." },
    { q: "Can my staff use it without seeing my earnings?", a: "Yes. Give each staff member their own login, and choose whether they can see finance or only view records." },
    { q: "Can I take my data out?", a: "Yes. Export members, payments and reports to Excel from the Export Center whenever you want." },
    { q: "Is there support?", a: "Yes. The BuildVVO team is available on WhatsApp and email, and you can raise requests from inside the app." },
  ];
  return (
    <section id="faq" className="bg-slate-50 py-20 sm:py-28" data-testid="faq-section">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Frequently Asked <span className="text-brand">Questions</span>
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">Straight answers before you start.</p>
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
