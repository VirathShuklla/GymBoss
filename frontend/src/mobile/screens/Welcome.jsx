import { useNavigate } from "react-router-dom";
import { Dumbbell } from "lucide-react";
import { MButton } from "../ui";

const HERO = "https://images.unsplash.com/photo-1637430308606-86576d8fef3c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODl8MHwxfHNlYXJjaHwxfHxneW0lMjBpbnRlcmlvciUyMGR1bWJiZWxscyUyMGRhcmt8ZW58MHx8fHwxNzg2MTIwOTIxfDA&ixlib=rb-4.1.0&q=85&w=900";

export default function Welcome() {
  const navigate = useNavigate();
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-[#0B1120]" data-testid="m-welcome">
      <div className="absolute inset-0">
        <img src={HERO} alt="" className="h-full w-full object-cover opacity-60" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0B1120]/40 via-[#0B1120]/70 to-[#0B1120]" />
      </div>

      <div className="relative flex flex-1 flex-col px-6 pb-[calc(32px+env(safe-area-inset-bottom))] pt-[calc(40px+env(safe-area-inset-top))]">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand shadow-lg shadow-brand/40">
            <Dumbbell className="h-5 w-5 text-white" strokeWidth={2.5} />
          </div>
          <span className="font-display text-lg font-extrabold tracking-tight text-white">GymBoss<span className="text-brand">_VVO</span></span>
        </div>

        <div className="mt-auto">
          <h1 className="font-display text-[2.6rem] font-extrabold leading-[1.05] tracking-tight text-white">Simplify Gym Management</h1>
          <p className="mt-4 max-w-xs text-[15px] leading-relaxed text-white/70">
            Members, payments, attendance and reminders — everything your gym needs, right in your pocket.
          </p>

          <div className="mt-9 space-y-3">
            <MButton onClick={() => navigate("/m/login")} data-testid="m-welcome-login">Login</MButton>
            <button onClick={() => navigate("/m/register")} data-testid="m-welcome-register"
              className="h-[52px] w-full rounded-2xl border border-white/25 bg-white/5 text-[15px] font-semibold text-white backdrop-blur-sm transition-all active:scale-[0.98]">
              Register New Account
            </button>
          </div>
          <p className="mt-7 text-center text-xs text-white/50">Powered by GymBoss_VVO · v1.0.0</p>
        </div>
      </div>
    </div>
  );
}
