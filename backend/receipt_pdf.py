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
        ("Payment Method", p.get("method")), ("Payment Date", _date(p.get("created_at"))),
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
