"""Member payment receipt PDF (A5, branded) rendered with reportlab."""
import io
from datetime import datetime

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

BRAND = colors.HexColor("#5B21B6")
MUTED = colors.HexColor("#64748B")
INK = colors.HexColor("#0F172A")
GREEN = colors.HexColor("#059669")
RED = colors.HexColor("#DC2626")


def _inr(v) -> str:
    v = float(v or 0)
    s = f"{v:,.2f}".rstrip("0").rstrip(".")
    return f"Rs. {s}"


def _date(v) -> str:
    if not v:
        return "-"
    if isinstance(v, datetime):
        return v.strftime("%d %b %Y")
    try:
        return datetime.fromisoformat(str(v)[:10]).strftime("%d %b %Y")
    except ValueError:
        return str(v)[:10]


def build_receipt_pdf(r: dict) -> bytes:
    p, m, gym, outlet = r["payment"], r.get("member") or {}, r.get("gym") or {}, r.get("outlet") or {}
    buf = io.BytesIO()
    W, H = A5
    c = canvas.Canvas(buf, pagesize=A5)
    c.setTitle(f"Receipt {p.get('receipt_no', '')}")

    c.setFillColor(BRAND)
    c.rect(0, H - 34 * mm, W, 34 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(14 * mm, H - 15 * mm, (gym.get("name") or "Gym")[:38])
    c.setFont("Helvetica", 9)
    c.drawString(14 * mm, H - 21 * mm, ", ".join(x for x in [outlet.get("name"), gym.get("city")] if x)[:70])
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - 14 * mm, H - 15 * mm, "PAYMENT RECEIPT")
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 14 * mm, H - 21 * mm, f"No. {p.get('receipt_no', '-')}")
    c.drawRightString(W - 14 * mm, H - 26 * mm, _date(p.get("created_at")))

    y = H - 48 * mm
    rows = [
        ("Member", m.get("full_name")), ("Member ID", m.get("member_code")), ("Phone", m.get("phone")),
        ("Plan / Item", p.get("plan_name")),
        ("Payment Type", {"admission": "Admission", "renewal": "Renewal"}.get(p.get("type"), "Due Payment")),
        ("Payment Method", p.get("method")), ("Payment Date", _date(p.get("payment_date") or p.get("created_at"))),
        ("Valid Until", _date(m.get("membership_expiry"))),
    ]
    for label, val in rows:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 10)
        c.drawString(14 * mm, y, label)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(W - 14 * mm, y, str(val or "-")[:48])
        y -= 8 * mm

    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setDash(3, 3)
    c.line(14 * mm, y + 3 * mm, W - 14 * mm, y + 3 * mm)
    c.setDash()
    y -= 6 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(14 * mm, y, "Amount Paid")
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(W - 14 * mm, y, _inr(p.get("amount")))
    if (m.get("due_amount") or 0) > 0:
        y -= 8 * mm
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 10)
        c.drawString(14 * mm, y, "Outstanding Balance")
        c.setFillColor(RED)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(W - 14 * mm, y, _inr(m.get("due_amount")))

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(W / 2, 20 * mm, f"Thank you for training with {gym.get('name') or 'us'}.")
    c.drawCentredString(W / 2, 15 * mm, "This is a computer-generated receipt. Powered by GymBoss_VVO.")
    c.showPage()
    c.save()
    return buf.getvalue()


def build_saas_invoice_pdf(rec: dict, org: dict, plan: dict) -> bytes:
    """GymBoss_VVO subscription invoice issued by BuildVVO to the gym."""
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"GymBoss_VVO Invoice {rec.get('payment_id', '')}")
    c.setFillColor(BRAND)
    c.rect(0, H - 34 * mm, W, 34 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(18 * mm, H - 17 * mm, "GymBoss_VVO")
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, H - 24 * mm, "BuildVVO Technologies Private Limited · India · buildvvotechnologies@gmail.com")
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(W - 18 * mm, H - 17 * mm, "TAX INVOICE / RECEIPT")
    y = H - 50 * mm
    rows = [
        ("Billed to", org.get("name") or "-"),
        ("City", org.get("city") or "-"),
        ("Invoice date", _date(rec.get("paid_at") or rec.get("created_at"))),
        ("Payment ID", rec.get("payment_id") or "-"),
        ("Reference", rec.get("order_id") or "-"),
        ("Plan", f"GymBoss_VVO {plan.get('name', 'Monthly')} ({plan.get('months', 1)} month{'s' if plan.get('months', 1) > 1 else ''})"),
        ("Billing", "Auto-renewing subscription" if str(rec.get("kind", "")).startswith("autodebit") else "One-time payment"),
    ]
    for label, value in rows:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 10)
        c.drawString(18 * mm, y, label)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60 * mm, y, str(value))
        y -= 8 * mm
    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.line(18 * mm, y, W - 18 * mm, y)
    y -= 12 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(18 * mm, y, "Amount paid")
    c.setFillColor(GREEN)
    c.drawRightString(W - 18 * mm, y, _inr(rec.get("amount")))
    y -= 14 * mm
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    for line in [
        "Paid via Razorpay. Prices are inclusive of applicable taxes unless stated otherwise.",
        "Auto-renewing plans renew at the same price each period until cancelled. Cancel anytime from the billing portal;",
        "access continues until the end of the paid period. This is a computer-generated invoice and needs no signature.",
    ]:
        c.drawString(18 * mm, y, line)
        y -= 5 * mm
    c.showPage()
    c.save()
    return buf.getvalue()



TYPE_LABELS = {"admission": "Admissions", "renewal": "Renewals", "due": "Due payments", "reversal": "Reversals"}


def build_monthly_report_pdf(s: dict, meta: dict) -> bytes:
    """A4 monthly finance statement: collections, expenses, net and outstanding dues (transaction dates, IST)."""
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Finance report {meta['month']}")
    c.setFillColor(BRAND)
    c.rect(0, H - 32 * mm, W, 32 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(16 * mm, H - 15 * mm, (meta.get("gym") or "Gym")[:50])
    c.setFont("Helvetica", 9)
    c.drawString(16 * mm, H - 22 * mm, ", ".join(x for x in [meta.get("outlet"), meta.get("city")] if x)[:80])
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - 16 * mm, H - 15 * mm, "MONTHLY FINANCE REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 16 * mm, H - 22 * mm, meta["month"])

    y = H - 46 * mm
    cards = [("Collections", s["revenue"], GREEN), ("Expenses", s["expenses"], RED),
             ("Net", s["net"], BRAND if s["net"] >= 0 else RED), ("Outstanding dues", s["outstanding"], RED)]
    cw = (W - 32 * mm - 9 * mm) / 4
    for i, (label, val, col) in enumerate(cards):
        x = 16 * mm + i * (cw + 3 * mm)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.roundRect(x, y - 16 * mm, cw, 18 * mm, 3 * mm, stroke=1, fill=0)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(x + 3 * mm, y - 3 * mm, label.upper())
        c.setFillColor(col)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 3 * mm, y - 11 * mm, _inr(val) if val >= 0 else f"- {_inr(abs(val))}")
    y -= 26 * mm
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(16 * mm, y, f"{s['transaction_count']} transactions  |  {s['due_member_count']} members with dues (current balance)")
    y -= 10 * mm

    def table(title, rows, total_label, total):
        nonlocal y
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(16 * mm, y, title)
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        for k, v in rows or [("None", 0)]:
            if y < 30 * mm:
                c.showPage()
                y = H - 20 * mm
                c.setFont("Helvetica", 10)
            c.setFillColor(INK)
            c.drawString(20 * mm, y, str(k)[:60])
            c.setFillColor(RED if v < 0 else INK)
            c.drawRightString(W - 16 * mm, y, _inr(v) if v >= 0 else f"- {_inr(abs(v))}")
            y -= 5.5 * mm
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(16 * mm, y + 3 * mm, W - 16 * mm, y + 3 * mm)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(INK)
        c.drawString(20 * mm, y - 1 * mm, total_label)
        c.drawRightString(W - 16 * mm, y - 1 * mm, _inr(total))
        y -= 12 * mm

    table("Collections by method", sorted(s["by_method"].items()), "Total collections", s["revenue"])
    table("Collections by type", [(TYPE_LABELS.get(k, k.title()), v) for k, v in sorted(s["by_type"].items())], "Total collections", s["revenue"])
    table("Expenses by category", sorted(s["expense_by_category"].items()), "Total expenses", s["expenses"])
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(16 * mm, 14 * mm, f"Amounts use each transaction's own date (IST, {s['date_from']} to {s['date_to']}). Reversals are shown on the day they were made.")
    c.drawString(16 * mm, 10 * mm, f"Generated {meta['generated']} by GymBoss_VVO")
    c.save()
    return buf.getvalue()
