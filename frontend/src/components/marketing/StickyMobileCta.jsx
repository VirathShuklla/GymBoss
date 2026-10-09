import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { track } from "../../lib/track";

// Mobile-only bottom CTA that appears once the visitor scrolls past the hero.
export function StickyMobileCta() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 600);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <div className={`fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 px-4 pb-[calc(12px+env(safe-area-inset-bottom))] pt-3 backdrop-blur transition-transform duration-300 md:hidden ${show ? "translate-y-0" : "translate-y-full"}`}
      data-testid="sticky-mobile-cta">
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-slate-900">10 days free</p>
          <p className="text-xs text-slate-500">No credit card needed</p>
        </div>
        <Link to="/register" onClick={() => track("hero_cta_click", { location: "sticky_mobile" })} data-testid="sticky-mobile-cta-button"
          className="rounded-xl bg-brand px-5 py-3 text-sm font-semibold text-white">Start Free Trial</Link>
      </div>
    </div>
  );
}
