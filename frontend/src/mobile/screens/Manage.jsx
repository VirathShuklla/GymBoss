// Mobile "Manage" hub: a segmented tab bar over the operational modules.
// Finance and Reports tabs are only shown to finance-enabled users (owner/admin/manager
// or a staff account with finance access) — mirroring the web app's gating.
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Seg } from "../ui";
import { useAuth } from "../../contexts/AuthContext";
import Members from "../manage/Members";
import Plans from "../manage/Plans";
import Enquiries from "../manage/Enquiries";
import Expenses from "../manage/Expenses";
import Outlets from "../manage/Outlets";
import Staff from "../manage/Staff";
import Finance from "../manage/Finance";
import Reports from "../manage/Reports";

const BASE_TABS = [
  { value: "members", label: "Members", C: Members },
  { value: "plans", label: "Plan / Catalogue", C: Plans },
  { value: "enquiries", label: "Enquiry", C: Enquiries },
  { value: "expenses", label: "Expense", C: Expenses },
  { value: "outlets", label: "Outlet", C: Outlets },
  { value: "staff", label: "Staff / Admin", C: Staff },
];

const FINANCE_TABS = [
  { value: "finance", label: "Finance", C: Finance },
  { value: "reports", label: "Reports", C: Reports },
];

export default function Manage() {
  const [sp] = useSearchParams();
  const { user } = useAuth();
  const canFinance = ["owner", "admin", "manager"].includes(user?.role) || user?.finance_enabled;
  const TABS = canFinance ? [...BASE_TABS, ...FINANCE_TABS] : BASE_TABS;

  const initTab = TABS.some((t) => t.value === sp.get("tab")) ? sp.get("tab") : "members";
  const [tab, setTab] = useState(initTab);
  const Active = (TABS.find((t) => t.value === tab) || TABS[0]).C;

  return (
    <div data-testid="m-manage">
      <h1 className="mb-4 font-display text-2xl font-extrabold tracking-tight text-foreground">Manage</h1>
      <Seg tabs={TABS} value={tab} onChange={setTab} />
      <div className="mt-5">
        <Active autoAdd={sp.get("add")} />
      </div>
    </div>
  );
}
