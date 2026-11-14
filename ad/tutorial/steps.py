N = lambda name: f'[data-testid="nav-{name}-desktop"]'
I = lambda tid: f'[data-testid="{tid}"]'


def S(id, cap, vo, act):
    return {"id": id, "cap": cap, "vo": vo, "act": act}


async def login(t):
    await t.type(I("login-identifier"), "demo@gymbossvvo.in", delay=0.05)
    await t.type(I("login-password"), "Demo@2026", delay=0.06)
    await t.tap(I("login-submit-button"))
    await t.page.wait_for_url("**/app/**", timeout=30000)
    await t.hold(1.5)


async def dash1(t):
    await t.focus(I("kpi-grid"), 5.5)


async def dash2(t):
    await t.tap(I("outlet-switcher"), hold=1.6)
    await t.esc()


async def dash3(t):
    await t.scroll(650)
    await t.focus(I("quick-actions"), 2.5)
    await t.focus(I("recent-transactions"), 2.5)
    await t.scroll(-2000)


async def plans1(t):
    await t.tap(N("plans-catalogue"))


async def plans2(t):
    await t.focus(I("plans-page") + " table", 4)
    for k in ["pt", "service", "product", "membership"]:
        await t.tap(I(f"tab-{k}"), zoom=False, hold=0.8)


async def plans3(t):
    await t.tap(I("add-membership-button"))
    await t.type(I("plan-form-name"), "Festive 2-Month Offer")
    await t.type(I("plan-form-duration"), "2")
    await t.type(I("plan-form-price"), "2800")
    await t.tap(I("plan-form-submit"))
    await t.hold(1.2)
    await t.focus(I("plans-page") + " table", 2.5)


async def mem1(t):
    await t.tap(N("members"))
    await t.tap(I("add-member-button"))


async def mem2(t):
    await t.type(I("member-form-name"), "Karan Mehra")
    await t.type(I("member-form-phone"), "9845012345")
    await t.select(I("member-form-gender"), "Male")
    await t.tap(I("member-form-batch"), hold=0.6)
    await t.tap(t.page.get_by_role("option").first, hold=0.7)
    await t.focus(I("member-form-code"), 1.8, pad=60)
    await t.tap(I("member-form-next"))


async def mem3(t):
    await t.type(I("member-form-email"), "karan.mehra@gmail.com", delay=0.05)
    await t.type(I("member-form-height"), "175")
    await t.type(I("member-form-weight"), "78")
    await t.type(I("member-form-notes"), "Old knee injury, avoid heavy squats", delay=0.05)
    await t.tap(I("member-form-next"))


async def mem4(t):
    await t.tap(I("member-form-plan"), hold=0.6)
    await t.tap(t.page.locator('[data-testid^="plan-option-"]', has_text="Quarterly").first, hold=0.7)
    await t.type(I("member-form-admission"), "500")
    await t.type(I("member-form-discount"), "300")
    await t.type(I("member-form-amount-paid"), "2000")
    await t.select(I("member-form-method"), "UPI")


async def mem5(t):
    await t.focus(I("payment-summary"), 4.5)
    await t.tap(I("member-form-submit"), hold=1.8)
    await t.focus(I("members-page") + " tbody tr", 2.5, pad=20)


async def pay1(t):
    await t.tap(N("payments"))
    await t.tap(I("record-payment-button"))


async def pay2(t):
    await t.type(I("payment-member-search"), "Karan")
    await t.tap(t.page.locator('[data-testid^="payment-member-search-option-"]').first)
    await t.focus(I("payment-member-due"), 2.2)
    await t.type(I("payment-amount-input"), "2200")
    await t.select(I("payment-method-select"), "Cash")
    await t.tap(I("payment-submit-button"), hold=1.5)


async def pay3(t):
    await t.focus(I("receipt-modal"), 5)
    await t.tap(I("receipt-close"))


async def pay4(t):
    await t.focus(I("payments-page") + " tbody tr", 3, pad=20)


async def att1(t):
    await t.tap(N("attendance"))
    await t.focus(I("att-open-qr"), 1.8)
    await t.focus(I("att-open-bio"), 1.8)


async def att2(t):
    await t.type(I("checkin-search"), "Karan")
    await t.tap(t.page.locator('[data-testid^="checkin-search-option-"]').first)
    await t.tap(I("checkin-button"), hold=1.5)
    await t.focus(I("att-stat-today"), 1.6)
    await t.focus(I("attendance-page") + " tbody tr", 2.4, pad=20)


async def att3(t):
    await t.tap(I("att-open-qr"), hold=3.2)
    await t.esc()


async def att4(t):
    for k in ["staff", "history", "today"]:
        await t.tap(I(f"tab-{k}"), hold=1.2)


async def due1(t):
    await t.tap(N("members"))
    await t.tap(I("members-chip-due"), hold=1.2)
    await t.focus(I("members-page") + " table", 3)


async def due2(t):
    await t.tap(N("reports"))
    await t.tap(I("report-tab-dues"), hold=1.2)
    await t.focus(I("dues-total"), 2.5)


async def open_member(t, q, name):
    await t.tap(N("members"))
    await t.tap(I("members-chip-all"), zoom=False, hold=0.5)
    await t.type(I("members-search"), q)
    await t.hold(1.2)
    await t.tap(t.page.locator("tbody tr", has_text=name).first, hold=1.4)


async def ren1(t):
    await open_member(t, "Dev", "Dev Patil")


async def ren2(t):
    await t.focus(I("drawer-membership-summary"), 3)
    await t.tap(I("action-renew"))


async def ren3(t):
    await t.select(I("renew-plan"), "Monthly")
    await t.type(I("renew-amount"), "1500")
    await t.select(I("renew-method"), "UPI")
    await t.tap(I("renew-submit"), hold=1.5)


async def ren4(t):
    if await t.page.locator(I("receipt-modal")).count():
        await t.focus(I("receipt-modal"), 2.5)
        await t.tap(I("receipt-close"))
    await t.focus(I("drawer-membership-summary"), 3)
    await t.esc()


async def wa1(t):
    await open_member(t, "Nisha", "Nisha Rane")
    await t.tap(I("action-payment-reminder"))


async def wa2(t):
    await t.tap('[data-testid^="reminder-option-"] >> nth=1')
    await t.focus(I("reminder-preview"), 4)


async def wa3(t):
    await t.tap(I("reminder-send"), hold=2.5)
    if await t.page.locator(I("reminder-modal")).count():
        await t.esc()


async def wa4(t):
    await t.tap(I("drawer-whatsapp"))
    await t.tap(I("wa-template"), hold=0.6)
    await t.tap(I("wa-template-custom"), hold=0.7)
    await t.type(I("wa-custom-message"), "Hi Nisha! The gym will be closed on 25 December for Christmas. See you on the 26th! - Iron Paradise Fitness", delay=0.03)
    await t.focus(I("whatsapp-modal"), 3)
    await t.esc()


async def frz1(t):
    await t.tap(I("action-freeze"))
    await t.type(I("freeze-reason"), "Travelling to hometown")
    await t.tap(I("freeze-submit"), hold=1.5)
    await t.focus(I("drawer-membership-summary"), 3)
    await t.esc()


async def enq1(t):
    await t.tap(N("enquiries"))
    await t.tap(I("add-enquiry-button"))


async def enq2(t):
    await t.type(I("enquiry-form-name"), "Pooja Nair")
    await t.type(I("enquiry-form-phone"), "9900112233")
    await t.select(I("enquiry-form-source"), "Instagram")
    await t.type('[placeholder="e.g., Membership, PT"]', "Membership")
    await t.tap(I("enquiry-form-submit"), hold=1.5)


async def enq3(t):
    await t.focus(t.page.locator("tbody tr", has_text="Pooja Nair").first, 4, pad=20)


async def exp1(t):
    await t.tap(N("expenses"))
    await t.tap(I("add-expense-button"))


async def exp2(t):
    await t.type(I("expense-form-name"), "Electricity Bill")
    await t.select(I("expense-form-category"), "Utilities")
    await t.type(I("expense-form-amount"), "8400")
    await t.select(I("expense-form-method"), "UPI")
    await t.tap(I("expense-form-submit"), hold=1.5)
    await t.focus(I("expenses-total"), 2.2)


async def staff1(t):
    await t.tap(N("staff"))
    await t.focus(I("staff-page") + " table", 2.5)
    await t.tap(I("add-staff-button"), hold=1.0)
    await t.focus(I("staff-form-modal"), 3.5)
    await t.esc()


async def out1(t):
    await t.tap(N("outlets"))
    await t.focus("table", 3)


async def fin1(t):
    await t.tap(N("finance"))
    await t.hold(1.2)
    await t.focus("main .grid >> nth=0", 4.5)


async def rep1(t):
    await t.tap(N("reports"))
    for k in ["revenue", "growth", "dues", "expiry", "enquiries"]:
        await t.tap(I(f"report-tab-{k}"), hold=1.1)


async def rep2(t):
    await t.tap(t.page.get_by_role("button", name="Monthly PDF"), hold=2.5)


async def exc1(t):
    await t.tap(N("export-center"))
    await t.focus(I("export-grid"), 2.5)
    await t.tap(I("export-download-members"), hold=2)


async def set1(t):
    await t.tap(N("settings"))
    await t.focus(I("gym-profile-form"), 2)
    await t.tap(I("settings-tab-appearance"))
    await t.tap(I("appearance-dark"), hold=1.6)
    await t.tap(I("appearance-light"), hold=1.0)
    await t.tap(I("settings-tab-integrations"))
    await t.focus(I("integration-whatsapp"), 2.5)


async def set2(t):
    await t.tap(I("user-menu-button"), hold=0.8)
    await t.tap(I("menu-subscription"), hold=1.2)
    await t.focus(I("subscription-plan-card"), 2.5)
    await t.tap(N("help-support"), hold=2.0)


async def set3(t):
    await t.tap(I("user-menu-button"), hold=0.8)
    await t.tap(I("menu-my-profile"), hold=2.5)


async def end1(t):
    await t.tap(N("dashboard"), hold=1.5)
    await t.focus(I("kpi-grid"), 6)


async def end2(t):
    await t.scroll(650)
    await t.focus(I("recent-transactions"), 5)


async def end3(t):
    await t.scroll(-2000)
    await t.hold(2)


CHAPTERS = [
    {"title": "Sign in", "steps": [
        S("c0", "Open GymBoss and sign in", "Hi! In this video, I'll show you how to run your gym day to day with GymBoss. Start by opening GymBoss on your laptop, and sign in with your email and password.", login)]},
    {"title": "Your dashboard", "steps": [
        S("d1", "Today at a glance", "This is your dashboard. The top cards show today's numbers: collection, new admissions, renewals and dues paid. They're at zero because the day has just started.", dash1),
        S("d2", "Switch between branches", "If you run more than one branch, use this outlet switcher to see one branch, or all of them together.", dash2),
        S("d3", "Quick actions and recent payments", "Scroll down for quick actions and your latest transactions. We'll come back here at the end of the day to see everything we did.", dash3)]},
    {"title": "Membership plans", "steps": [
        S("p1", "Tap Plans & Catalogue", "Before adding members, let's check your plans. Tap Plans and Catalogue in the menu.", plans1),
        S("p2", "Your plans and prices", "Here are the gym's membership plans: monthly at fifteen hundred rupees, quarterly at four thousand, half-yearly and annual. The tabs above hold personal training, services and products.", plans2),
        S("p3", "Tap Add Membership to create a plan", "Launching a new offer? Tap Add Membership, enter a name, the duration and the price, and save. Your new plan appears in the list straight away.", plans3)]},
    {"title": "Add a new member", "steps": [
        S("m1", "Tap Members, then Add Member", "A new member has just walked in. Go to Members, and tap Add Member.", mem1),
        S("m2", "Name, phone, gender and batch", "Step one is the basics. Type the member's name and mobile number, choose their gender, and the batch they'll train in. The member ID is created for you.", mem2),
        S("m3", "Optional health details", "Step two is optional. Add an email, height and weight, and any health notes, like an old knee injury, so your trainers know.", mem3),
        S("m4", "Assign a plan and enter the payment", "Step three assigns the plan. Pick Quarterly for four thousand rupees, add a five hundred rupee admission fee, and a three hundred rupee discount. Karan pays two thousand rupees today, by UPI.", mem4),
        S("m5", "Check the summary, then save", "The summary shows a total of four thousand two hundred rupees, two thousand collected, and two thousand two hundred still due. Tap Save, and Karan appears at the top of your member list.", mem5)]},
    {"title": "Record a payment", "steps": [
        S("y1", "Tap Payments, then Record Payment", "Later that evening, Karan comes back to clear his balance. Go to Payments, and tap Record Payment.", pay1),
        S("y2", "Find the member, enter the amount", "Search for Karan. GymBoss shows exactly how much he still owes. Enter two thousand two hundred rupees, pick Cash, and save.", pay2),
        S("y3", "A receipt is created instantly", "A receipt is created instantly. You can download it as a PDF, print it, or share it with the member on WhatsApp.", pay3),
        S("y4", "The payment is in your list", "The payment now sits at the top of your payments list, with its own receipt number.", pay4)]},
    {"title": "Mark attendance", "steps": [
        S("a1", "Tap Attendance", "Now, attendance. Tap Attendance. Members can scan your gym's QR code, punch in on a fingerprint machine, or you can check them in by hand.", att1),
        S("a2", "Search the member, tap Check In", "For a manual check-in, search for Karan and tap Check In. He now shows under Members today, and the check-in count goes up.", att2),
        S("a3", "Show your gym's QR code", "Tap Show QR code to get one QR for your entrance. Print it, and members simply scan it with their phone camera. No app needed.", att3),
        S("a4", "Staff attendance and history", "The Staff today and History tabs show which of your team came in, and past attendance month by month.", att4)]},
    {"title": "Outstanding dues", "steps": [
        S("u1", "Members, then tap Due", "Every gym has members who haven't paid in full. On the Members page, tap Due to see only the people who owe you money.", due1),
        S("u2", "Reports, then Outstanding Dues", "For the full picture, open Reports and choose Outstanding Dues. You'll see the total owed, and each member's balance, so you know who to follow up with.", due2)]},
    {"title": "Renew a membership", "steps": [
        S("r1", "Search the member and tap their name", "Dev's membership is running out soon. Search for him on the Members page, and tap his name to open his profile.", ren1),
        S("r2", "Tap Renew Membership", "His card shows the plan, the expiry date, and how many days are left. Tap Renew Membership.", ren2),
        S("r3", "Choose the plan and payment", "Choose the plan, enter what he's paying, fifteen hundred rupees for another month, pick UPI, and confirm. The new expiry date is worked out for you.", ren3),
        S("r4", "Membership renewed", "Done. His expiry date has moved forward, and the renewal is saved as a payment.", ren4)]},
    {"title": "WhatsApp reminders", "steps": [
        S("w1", "Open the member, tap Send Payment Reminder", "Next, reminders. Nisha still owes a balance. Open her profile and tap Send Payment Reminder.", wa1),
        S("w2", "Pick a reminder and check the message", "Pick the type of reminder. GymBoss writes the message for you, with the member's name and the exact amount due.", wa2),
        S("w3", "Tap Send to open WhatsApp", "Tap Send, and WhatsApp opens with the message already typed. You just press send. Messages go from your own WhatsApp, one member at a time.", wa3),
        S("w4", "Send your own message, like a holiday notice", "You can also write your own message. Tap the WhatsApp button, type a holiday notice, and send it the same way. To message every member at once, you'll need the official WhatsApp Business connection.", wa4)]},
    {"title": "Freeze a membership", "steps": [
        S("f1", "Tap Freeze, add a reason, and save", "If a member is travelling or injured, pause their membership. Tap Freeze, check the dates, add a reason, and save. The days they miss are added back to their expiry.", frz1)]},
    {"title": "Track enquiries", "steps": [
        S("e1", "Tap Enquiries, then Add Enquiry", "When someone walks in asking about prices, save them as an enquiry so you never lose the lead. Tap Enquiries, then Add Enquiry.", enq1),
        S("e2", "Enter the lead's details", "Enter their name and phone number, where they heard about you, and what they're interested in. Then save.", enq2),
        S("e3", "Follow up or convert", "From the list, you can message them on WhatsApp, log a follow-up, or tap Convert when they join, which turns them into a member.", enq3)]},
    {"title": "Record expenses", "steps": [
        S("x1", "Tap Expenses, then Add Expense", "To see your real profit, record your expenses too. Tap Expenses, then Add Expense.", exp1),
        S("x2", "Enter the expense and save", "Enter the name, the category and the amount. Say, the electricity bill, eight thousand four hundred rupees by UPI. Save, and the monthly total updates right away.", exp2)]},
    {"title": "Staff and branches", "steps": [
        S("s1", "Staff: your team and their access", "Under Staff, you'll find your team. Tap Add Staff to add a trainer or receptionist, and choose what they're allowed to see, like keeping finance private.", staff1),
        S("o1", "Outlets: your branches", "Outlets lists your branches. Iron Paradise has two: Indiranagar and HSR Layout.", out1)]},
    {"title": "Finance and reports", "steps": [
        S("n1", "Finance: this month's money", "Finance shows this month's money in one place: revenue, expenses, net cash flow, and outstanding dues.", fin1),
        S("n2", "Reports: charts for everything", "Reports has charts for revenue, member growth, dues, expiring memberships, and how many enquiries you convert.", rep1),
        S("n3", "Tap Monthly PDF", "Tap Monthly PDF to download the full finance report for the month, ready to send to your accountant.", rep2),
        S("n4", "Export Center: download your data", "And Export Center lets you download members, payments, attendance and more, as spreadsheet files, for any dates or branch.", exc1)]},
    {"title": "Settings and help", "steps": [
        S("g1", "Settings: gym profile, theme, integrations", "In Settings, you can update your gym's name and city, switch between light and dark mode, and connect WhatsApp Business and online payments.", set1),
        S("g2", "Subscription and Help & Support", "Your GymBoss plan and billing are under Subscription, and Help and Support connects you to our team on WhatsApp or email.", set2),
        S("g3", "My Profile", "Your own name, phone number and password are under My Profile, in the top-right menu.", set3)]},
    {"title": "End of the day", "steps": [
        S("z1", "Back to the dashboard", "Let's head back to the dashboard. Today's collection now includes Karan's admission, his balance payment, and Dev's renewal. The new admission and renewal are counted too.", end1),
        S("z2", "Every payment from today", "Scroll down, and every payment we recorded today is listed under recent transactions.", end2),
        S("z3", "You're ready to run your gym", "And that's a full day at the gym with GymBoss. Start your free trial today, and run your whole gym from one simple screen.", end3)]},
]
