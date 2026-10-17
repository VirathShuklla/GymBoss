import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Logo } from "../components/Logo";
import { LEGAL, UPDATED, CONTACT_EMAIL } from "../constants/legal";

export default function Legal({ kind }) {
  const navigate = useNavigate();
  const doc = LEGAL[kind];
  const other = kind === "privacy" ? { to: "/terms", label: "Terms of Service" } : { to: "/privacy", label: "Privacy Policy" };
  useEffect(() => { document.title = `${doc.title} · GymBoss_VVO`; window.scrollTo(0, 0); }, [doc.title]);

  return (
    <div className="min-h-screen bg-background text-foreground" data-testid={`legal-${kind}-page`}>
      <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-4">
          <button onClick={() => (window.history.length > 1 ? navigate(-1) : navigate("/"))} data-testid="legal-back"
            className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <Link to="/"><Logo /></Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 pb-[calc(64px+env(safe-area-inset-bottom))] pt-10">
        <h1 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl" data-testid="legal-title">{doc.title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Last updated: {UPDATED}</p>
        <p className="mt-6 leading-relaxed text-muted-foreground">{doc.intro}</p>
        {doc.sections.map(([heading, items], i) => (
          <section key={heading} className="mt-9">
            <h2 className="font-display text-lg font-bold">{i + 1}. {heading}</h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-muted-foreground">
              {items.map((t) => <li key={t}>{t}</li>)}
            </ul>
          </section>
        ))}
        <div className="mt-12 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-border pt-6 text-sm">
          <Link to={other.to} className="font-semibold text-brand hover:underline" data-testid="legal-other-link">{other.label}</Link>
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-muted-foreground hover:text-foreground" data-testid="legal-contact-email">{CONTACT_EMAIL}</a>
        </div>
      </main>
    </div>
  );
}
