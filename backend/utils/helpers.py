"""Reusable helpers: PDF (ReportLab), CSV/Excel export, QR codes, pg_dump backup."""
import csv
import io
import os
import uuid
import subprocess
from datetime import datetime

from werkzeug.utils import secure_filename

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                Spacer, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Circle, Polygon
import qrcode
from openpyxl import Workbook

from config import Config


# ======================================================================= PDFs
# Brand palette
_BROWN = colors.HexColor("#7a4a1e")
_GOLD = colors.HexColor("#c98a3a")
_DARK = colors.HexColor("#3d2a16")
_CREAM = colors.HexColor("#faf3e9")
_LINE = colors.HexColor("#e6dcc9")
_BRAND_NAME = "Smart Jaggery Mart"
_TAGLINE = "pure local jaggery &mdash; from farm to family"


def _doc(buf):
    return SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm,
                             bottomMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm)


def _styles():
    """A fresh stylesheet with our branded paragraph styles added."""
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Brand", parent=ss["Title"], fontName="Helvetica-Bold",
                          fontSize=21, leading=24, textColor=_BROWN, alignment=TA_CENTER, spaceAfter=1))
    ss.add(ParagraphStyle("BrandSub", parent=ss["Normal"], fontName="Helvetica-Oblique",
                          fontSize=9.5, textColor=_GOLD, alignment=TA_CENTER, spaceAfter=2))
    ss.add(ParagraphStyle("DocTitle", parent=ss["Heading1"], fontName="Helvetica-Bold",
                          fontSize=15, textColor=_DARK, alignment=TA_CENTER, spaceBefore=7, spaceAfter=1))
    ss.add(ParagraphStyle("MetaC", parent=ss["Normal"], fontSize=9, textColor=colors.grey,
                          alignment=TA_CENTER, leading=13))
    ss.add(ParagraphStyle("KV", parent=ss["Normal"], fontSize=10, textColor=_DARK, leading=15))
    ss.add(ParagraphStyle("Foot", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey,
                          alignment=TA_CENTER))
    return ss


def _logo(size=40):
    """A drawn 'jaggery disc' emblem logo (concentric amber circles + highlight)."""
    d = Drawing(size, size)
    c = size / 2.0
    rings = [
        (1.00, "#34200d"),  # dark rim
        (0.90, "#6a3f14"),
        (0.66, "#a4641f"),
        (0.40, "#d98e44"),  # warm centre
    ]
    for frac, hexc in rings:
        d.add(Circle(c, c, c * frac, fillColor=colors.HexColor(hexc), strokeColor=None))
    # little jaggery block silhouette + glossy highlight
    d.add(Polygon(points=[c - 5, c - 3, c + 5, c - 3, c + 4, c + 4, c - 4, c + 4],
                  fillColor=colors.HexColor("#5f3a14"), strokeColor=None))
    d.add(Circle(c * 0.72, c * 1.28, c * 0.16, fillColor=colors.HexColor("#fff4dc"), strokeColor=None))
    d.hAlign = "CENTER"
    return d


def _brand_header(styles, doc_title, meta_lines=None):
    """The iconic, branded header used at the top of every PDF."""
    flow = [
        _logo(42),
        Spacer(1, 2 * mm),
        Paragraph(_BRAND_NAME, styles["Brand"]),
        Paragraph("&bull;&nbsp;&nbsp; " + _TAGLINE + " &nbsp;&nbsp;&bull;", styles["BrandSub"]),
        HRFlowable(width="100%", thickness=2.4, color=_BROWN, spaceBefore=5, spaceAfter=9),
        Paragraph(doc_title, styles["DocTitle"]),
    ]
    for m in (meta_lines or []):
        flow.append(Paragraph(m, styles["MetaC"]))
    flow.append(HRFlowable(width="100%", thickness=0.7, color=_GOLD, spaceBefore=7, spaceAfter=9))
    return flow


def _footer(canvas, doc):
    """Branded footer + page number on every page."""
    canvas.saveState()
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(16 * mm, 12 * mm, A4[0] - 16 * mm, 12 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawString(16 * mm, 7.5 * mm, _BRAND_NAME)
    canvas.drawRightString(A4[0] - 16 * mm, 7.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _build(buf, story):
    _doc(buf).build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _table(rows, col_widths=None):
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _BROWN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, _GOLD),
        ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _CREAM]),
        ("TEXTCOLOR", (0, 1), (-1, -1), _DARK),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _totals_table(pairs, col_widths=None):
    """A right-aligned key/value totals block (last row emphasised)."""
    t = Table(pairs, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), _DARK),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, _BROWN),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), _BROWN),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def invoice_pdf(order_dict):
    """Return PDF bytes for a completed order (dict from Order.to_dict())."""
    buf = io.BytesIO()
    styles = _styles()
    meta = [
        f"<b>Invoice</b> &nbsp;·&nbsp; Order #{order_dict['id']} &nbsp;·&nbsp; Status: {order_dict['status']}",
        f"Customer: {order_dict.get('customer_name','')} &nbsp;·&nbsp; Date: {str(order_dict.get('created_at',''))[:10]}",
        f"Deliver to: {order_dict['delivery_address']} ({order_dict.get('pincode') or '-'})",
    ]
    story = _brand_header(styles, "INVOICE", meta)
    rows = [["Product", "Warehouse", "Grade", "Qty (kg)", "Price/kg", "Line (Kyats)"]]
    for it in order_dict["items"]:
        rows.append([it["batch_id"], it.get("warehouse_name") or "-", it["grade"], f"{it['qty_kg']}",
                     f"{it['unit_price']} Kyats", f"{it['line_total']} Kyats"])
    story.append(_table(rows, [115, 100, 45, 55, 70, 75]))
    story.append(Spacer(1, 7 * mm))
    story.append(_totals_table([
        ["Subtotal", f"{order_dict['subtotal']} Kyats"],
        ["Discount", f"- {order_dict['discount_amount']} Kyats"],
        ["Delivery", f"{order_dict['delivery_charge']} Kyats"],
        ["GRAND TOTAL", f"{order_dict['grand_total']} Kyats"],
    ], [330, 130]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Thank you for buying local jaggery!", styles["Foot"]))
    return _build(buf, story)


def packing_slip_pdf(order_dict):
    """Printable packing slip for warehouse."""
    buf = io.BytesIO()
    styles = _styles()
    meta = [
        f"Order #{order_dict['id']} &nbsp;·&nbsp; Warehouse: {order_dict.get('warehouse_name','')}",
        f"Ship to: {order_dict['delivery_address']} ({order_dict.get('pincode') or '-'})",
        f"Preferred date: {order_dict.get('preferred_date') or '-'}",
    ]
    story = _brand_header(styles, "PACKING SLIP", meta)
    rows = [["Product", "Grade", "Qty (kg)", "Packed"]]
    for it in order_dict["items"]:
        rows.append([it["batch_id"], it["grade"], f"{it['qty_kg']}", "[   ]"])
    story.append(_table(rows, [170, 65, 95, 80]))
    return _build(buf, story)


def report_pdf(title, headers, rows, summary_lines=None, period=None):
    """Generic tabular report PDF (used for admin/warehouse exports).

    `period` (e.g. "2023-01-01 - 2023-12-31") shows as the report period line.
    """
    buf = io.BytesIO()
    styles = _styles()
    meta = []
    if period:
        meta.append(f"<b>Period:</b> {period}")
    else:
        meta.append(f"Generated: {datetime.utcnow().isoformat(timespec='seconds')}")
    for line in (summary_lines or []):
        meta.append(line)
    story = _brand_header(styles, title, meta)
    story.append(_table([headers] + [[str(c) for c in r] for r in rows]))
    return _build(buf, story)


def payment_slip_pdf(title, pairs, amount, note=None, items=None, item_headers=None):
    """A payment receipt/slip: detail rows, an optional itemised table, an amount, a note.

    `items`        -> list of rows (each a list of cells) for the category/value table.
    `item_headers` -> the header row for that table.
    """
    buf = io.BytesIO()
    styles = _styles()
    meta = [title, f"Issued: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"]
    story = _brand_header(styles, "PAYMENT RECEIPT", meta)
    story.append(_table([["Detail", "Value"]] + [[str(k), str(v)] for k, v in pairs], [200, 260]))
    if items:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("<b>Items in this order</b>", styles["KV"]))
        story.append(Spacer(1, 2 * mm))
        hdr = item_headers or ["Category", "Grade", "Qty (kg)", "Unit (Kyats)", "Value (Kyats)"]
        story.append(_table([hdr] + [[str(c) for c in r] for r in items]))
    story.append(Spacer(1, 7 * mm))
    story.append(_totals_table([["AMOUNT PAID", f"{amount}"]], [330, 130]))
    if note:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(note, styles["MetaC"]))
    return _build(buf, story)


def backup_slip_pdf(pairs, note=None):
    """A branded receipt/slip confirming a database backup was created."""
    buf = io.BytesIO()
    styles = _styles()
    meta = [f"Issued: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"]
    story = _brand_header(styles, "DATABASE BACKUP RECEIPT", meta)
    story.append(_table([["Detail", "Value"]] + [[str(k), str(v)] for k, v in pairs], [165, 295]))
    story.append(Spacer(1, 7 * mm))
    story.append(_totals_table([["STATUS", "BACKUP SUCCESSFUL"]], [330, 130]))
    if note:
        story.append(Spacer(1, 7 * mm))
        story.append(Paragraph(note, styles["MetaC"]))
    return _build(buf, story)


# ------------------------------------------------------------------ CSV/Excel
def to_csv(headers, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return buf.getvalue()


def to_xlsx(headers, rows, sheet_title="Report", info_lines=None, total_row=None):
    """Excel export. Optional `info_lines` (report details) are written above the
    table, and an optional `total_row` is appended at the bottom."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]
    for line in (info_lines or []):
        ws.append(line if isinstance(line, (list, tuple)) else [line])
    if info_lines:
        ws.append([])  # blank spacer row before the table
    ws.append(headers)
    for r in rows:
        ws.append(list(r))
    if total_row:
        ws.append(list(total_row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------------ QR
def save_image(file, prefix="img"):
    """Validate + save one uploaded image to UPLOAD_FOLDER. Returns the stored
    filename, or raises ValueError on a bad/empty file."""
    if not file or not file.filename:
        raise ValueError("empty file")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in Config.IMAGE_EXTENSIONS:
        raise ValueError("image must be one of: " + ", ".join(sorted(Config.IMAGE_EXTENSIONS)))
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    safe = secure_filename(f"{prefix}_{uuid.uuid4().hex[:10]}.{ext}")
    file.save(os.path.join(Config.UPLOAD_FOLDER, safe))
    return safe


def qr_png(data: str):
    """Return PNG bytes of a QR code encoding `data`."""
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# -------------------------------------------------------------- DB backup
def pg_dump_backup():
    """Run pg_dump and return (path, error). One-click admin backup."""
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(Config.UPLOAD_FOLDER, f"backup_{stamp}.sql")

    # parse db name from URI: postgresql://user:pw@host:port/dbname
    uri = Config.SQLALCHEMY_DATABASE_URI
    dbname = uri.rsplit("/", 1)[-1]
    user = uri.split("://", 1)[1].split(":", 1)[0]
    pw = uri.split("://", 1)[1].split(":", 2)[1].split("@", 1)[0]

    env = dict(os.environ, PGPASSWORD=pw)
    exe = os.path.join(Config.PG_BIN, "pg_dump.exe")
    try:
        subprocess.run(
            [exe, "-U", user, "-p", Config.PG_PORT, "-d", dbname, "-f", out],
            check=True, env=env, capture_output=True, text=True, timeout=120,
        )
        return os.path.basename(out), None
    except FileNotFoundError:
        return None, f"pg_dump not found at {exe}"
    except subprocess.CalledProcessError as e:
        return None, e.stderr or str(e)
