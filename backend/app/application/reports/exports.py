from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_report_csv(columns: list[tuple[str, str]], rows: list[dict[str, Any]]) -> bytes:
    """Generate a BOM-prefixed CSV that opens correctly in Microsoft Excel."""

    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([title for title, _ in columns])
    for row in rows:
        writer.writerow([row.get(key, "") if row.get(key) is not None else "" for _, key in columns])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def create_report_pdf(title: str, columns: list[tuple[str, str]], rows: list[dict[str, Any]]) -> bytes:
    """Create a landscape PDF table for a bounded tenant report export."""

    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=landscape(A4),
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    styles = getSampleStyleSheet()
    body_style = styles["BodyText"]
    body_style.fontSize = 6.5
    body_style.leading = 8
    table_data = [[Paragraph(column, body_style) for column, _ in columns]]
    for row in rows:
        table_data.append([Paragraph(str(row.get(key, "") or ""), body_style) for _, key in columns])

    available_width = landscape(A4)[0] - 16 * mm
    widths = [available_width / len(columns)] * len(columns)
    table = Table(table_data, repeatRows=1, colWidths=widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B4F6C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    document.build([Paragraph(title, styles["Title"]), Spacer(1, 5 * mm), table])
    return stream.getvalue()
