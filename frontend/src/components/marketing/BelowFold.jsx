import { Features } from "./Features";
import { HowItWorks } from "./HowItWorks";
import { Pricing } from "./Pricing";
import { Faq } from "./Faq";
import { FinalCta } from "./FinalCta";
import { MarketingFooter } from "./Footer";
import { FloatingWhatsApp } from "./FloatingWhatsApp";
import { StickyMobileCta } from "./StickyMobileCta";

// Everything below the hero, loaded as a separate chunk so the hero paints first.
export default function BelowFold() {
  return (
    <>
      <Features />
      <HowItWorks />
      <Pricing />
      <Faq />
      <FinalCta />
      <MarketingFooter />
      <FloatingWhatsApp />
      <StickyMobileCta />
    </>
  );
}
