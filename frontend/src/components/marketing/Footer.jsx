import { Link } from "react-router-dom";
import { Logo } from "../Logo";
import { usePublicConfig } from "../../hooks/usePublicConfig";

export function MarketingFooter() {
  const config = usePublicConfig();
  const year = new Date().getFullYear();
  return (
    <footer className="bg-[#0B1224] text-slate-400" data-testid="marketing-footer">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-4">
          <div>
            <Logo dark />
            <p className="mt-4 max-w-xs text-sm leading-relaxed">
              The modern gym operating system — members, payments, attendance, staff and communication in one place.
            </p>
          </div>
          <div>
            <h4 className="font-display text-sm font-bold uppercase tracking-wider text-white">Product</h4>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li><a href="/#features" className="transition-colors hover:text-white">Features</a></li>
              <li><a href="/#pricing" className="transition-colors hover:text-white">Pricing</a></li>
              <li><a href="/#how-it-works" className="transition-colors hover:text-white">How It Works</a></li>
              <li><a href="/#faq" className="transition-colors hover:text-white">FAQ</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-display text-sm font-bold uppercase tracking-wider text-white">Company</h4>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li><span className="cursor-default">About BuildVVO</span></li>
              <li><a href="/#faq" className="transition-colors hover:text-white">Contact</a></li>
              <li><span className="cursor-default">Privacy Policy</span></li>
              <li><span className="cursor-default">Terms of Service</span></li>
            </ul>
          </div>
          <div>
            <h4 className="font-display text-sm font-bold uppercase tracking-wider text-white">Support</h4>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li><Link to="/login" className="transition-colors hover:text-white">Help & Support</Link></li>
              {config?.support_email && <li><a href={`mailto:${config.support_email}`} className="transition-colors hover:text-white">{config.support_email}</a></li>}
              <li><span className="cursor-default text-slate-500">Android & iOS apps — coming soon</span></li>
            </ul>
          </div>
        </div>
        <div className="mt-14 border-t border-slate-800 pt-8 text-center text-sm">
          <p>© {year} BuildVVO Technologies Private Limited. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
