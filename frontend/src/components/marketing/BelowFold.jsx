import { Features } from "./Features";
import { ValueStack } from "./ValueStack";
import { HowItWorks } from "./HowItWorks";
import { RoiCalculator } from "./RoiCalculator";
import { Comparison } from "./Comparison";
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
      <ValueStack />
      <HowItWorks />
      <RoiCalculator />
      <Comparison />
      <Pricing />
      <Faq />
      <FinalCta />
      <MarketingFooter />
      <FloatingWhatsApp />
      <StickyMobileCta />
    </>
  );
}
