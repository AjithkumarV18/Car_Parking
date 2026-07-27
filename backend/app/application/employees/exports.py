from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

EXPORT_COLUMNS = [
    ("Employee ID", "employee_id"),
    ("Name", "name"),
    ("Gender", "gender"),
    ("Email", "email"),
    ("Phone", "phone"),
    ("Designation", "designation"),
    ("Role", "role_name"),
    ("Parking Location", "parking_location_name"),
    ("Salary", "salary"),
    ("Joining Date", "joining_date"),
    ("Status", "status"),
]


def create_excel_csv(rows: list[dict[str, Any]]) -> bytes:
    """Create UTF-8 CSV that opens directly in Excel without extra dependencies."""

    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([title for title, _ in EXPORT_COLUMNS])
    for row in rows:
        writer.writerow([row.get(key, "") for _, key in EXPORT_COLUMNS])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def create_employee_pdf(rows: list[dict[str, Any]]) -> bytes:
    """Create a printable, paginated PDF listing of employee records."""

    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    table_data = [[Paragraph(title, styles["BodyText"]) for title, _ in EXPORT_COLUMNS]]
    for row in rows:
        table_data.append([Paragraph(str(row.get(key, "")), styles["BodyText"]) for _, key in EXPORT_COLUMNS])
    table = Table(table_data, repeatRows=1, colWidths=[22 * mm, 34 * mm, 16 * mm, 43 * mm, 28 * mm, 30 * mm, 25 * mm, 32 * mm, 20 * mm, 25 * mm, 19 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B4F6C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    document.build([Paragraph("Employee Directory", styles["Title"]), Spacer(1, 6 * mm), table])
    return stream.getvalue()
