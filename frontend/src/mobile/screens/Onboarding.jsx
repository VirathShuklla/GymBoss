import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Dumbbell, BellRing, Building2, BarChart3 } from "lucide-react";
import { MButton } from "../ui";

const SLIDES = [
  { icon: Dumbbell, title: "Seamlessly Manage Memberships", text: "Handle admissions, renewals, dues and expenses — all from your pocket." },
  { icon: BellRing, title: "Expiry & Due Reminders", text: "Keep members engaged with timely WhatsApp reminders and wishes." },
  { icon: Building2, title: "Multi-Outlet Support", text: "Run all your gym branches from a single, unified dashboard." },
  { icon: BarChart3, title: "Reporting & Analytics", text: "See collections, growth and outstanding dues at a glance." },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [i, setI] = useState(0);
  const S = SLIDES[i];
  const finish = () => {
    localStorage.setItem("gb-m-onboarded", "1");
    navigate("/m/welcome", { replace: true });
  };
  const next = () => (i < SLIDES.length - 1 ? setI(i + 1) : finish());

  return (
    <div className="flex min-h-screen flex-col bg-background px-6 pb-[calc(28px+env(safe-area-inset-bottom))] pt-[calc(28px+env(safe-area-inset-top))]" data-testid="m-onboarding">
      <div className="flex justify-end">
        <button onClick={finish} className="text-sm font-semibold text-muted-foreground" data-testid="m-onboarding-skip">Skip</button>
      </div>
      <div key={i} className="m-anim flex flex-1 flex-col items-center justify-center text-center">
        <div className="relative mb-10 flex h-52 w-52 items-center justify-center rounded-full bg-brand/10">
          <div className="flex h-32 w-32 items-center justify-center rounded-3xl bg-gradient-to-br from-brand to-[#5B21B6] shadow-2xl shadow-brand/40">
            <S.icon className="h-14 w-14 text-white" strokeWidth={2} />
          </div>
        </div>
        <h1 className="font-display text-3xl font-extrabold leading-tight tracking-tight text-foreground">{S.title}</h1>
        <p className="mt-4 max-w-xs text-[15px] leading-relaxed text-muted-foreground">{S.text}</p>
      </div>
      <div className="mb-7 flex justify-center gap-2">
        {SLIDES.map((_, idx) => (
          <span key={idx} className={`h-2 rounded-full transition-all ${idx === i ? "w-6 bg-brand" : "w-2 bg-border"}`} />
        ))}
      </div>
      <MButton onClick={next} data-testid="m-onboarding-next">{i < SLIDES.length - 1 ? "Next" : "Get Started"}</MButton>
    </div>
  );
}
