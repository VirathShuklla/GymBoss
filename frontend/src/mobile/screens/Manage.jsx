import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Seg } from "../ui";
import Members from "../manage/Members";
import Plans from "../manage/Plans";
import Enquiries from "../manage/Enquiries";
import Expenses from "../manage/Expenses";
import Outlets from "../manage/Outlets";
import Staff from "../manage/Staff";
import Templates from "../manage/Templates";

const TABS = [
  { value: "members", label: "Members", C: Members },
  { value: "plans", label: "Plan / Catalogue", C: Plans },
  { value: "enquiries", label: "Enquiry", C: Enquiries },
  { value: "expenses", label: "Expense", C: Expenses },
  { value: "outlets", label: "Outlet", C: Outlets },
  { value: "staff", label: "Staff / Admin", C: Staff },
  { value: "templates", label: "Templates", C: Templates },
];

export default function Manage() {
  const [sp] = useSearchParams();
  const initTab = TABS.some((t) => t.value === sp.get("tab")) ? sp.get("tab") : "members";
  const [tab, setTab] = useState(initTab);
  const Active = TABS.find((t) => t.value === tab).C;

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
