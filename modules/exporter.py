"""
Export: Excel (.xlsx) und PDF-Report.
"""

import io
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)


ALLOKAT_NAVY = colors.HexColor("#1B4F72")
ALLOKAT_TEAL = colors.HexColor("#148F77")
ALLOKAT_LIGHT = colors.HexColor("#EBF5FB")


def export_excel(portfolio: dict, depots: list[dict]) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Übersicht
        overview_data = {
            "Kategorie": ["Gesamtvermögen CHF", "Nicht durchgerechnet CHF", "Auszugsdatum"],
            "Wert": [
                f"{portfolio['total_chf']:,.0f}",
                f"{portfolio['nicht_durchgerechnet_chf']:,.0f}",
                date.today().isoformat(),
            ],
        }
        pd.DataFrame(overview_data).to_excel(writer, sheet_name="Übersicht", index=False)

        # Sheet 2: Asset-Klassen
        _dict_to_sheet(portfolio["asset_klassen"], "Asset-Klassen", writer)

        # Sheet 3: Sektoren
        _dict_to_sheet(portfolio["sektoren"], "Sektoren", writer)

        # Sheet 4: Währungen
        _dict_to_sheet(portfolio["waehrungen"], "Währungen", writer)

        # Sheet 5: Banken
        _dict_to_sheet(portfolio["banken"], "Banken", writer)

        # Sheet 6: Positionen Detail
        rows = []
        for p in portfolio["positionen_detail"]:
            rows.append(
                {
                    "Bank": p["bank"],
                    "ISIN": p["isin"],
                    "Bezeichnung": p["bezeichnung"],
                    "Typ": p["typ"],
                    "Marktwert orig.": p["marktwert_orig"],
                    "Währung": p["waehrung"],
                    "Marktwert CHF": round(p["marktwert_chf"], 2),
                    "Datenbasis": p["confidence"],
                }
            )
        if rows:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Positionen", index=False)

    return output.getvalue()


def _dict_to_sheet(data: dict, sheet_name: str, writer) -> None:
    rows = [
        {"Kategorie": k, "Anteil %": f"{v * 100:.1f}%"}
        for k, v in data.items()
    ]
    if rows:
        pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)


def export_pdf(portfolio: dict) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AllokatTitle",
        parent=styles["Heading1"],
        textColor=ALLOKAT_NAVY,
        fontSize=20,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "AllokatH2",
        parent=styles["Heading2"],
        textColor=ALLOKAT_TEAL,
        fontSize=13,
        spaceBefore=14,
        spaceAfter=4,
    )
    normal = styles["Normal"]

    story = []

    story.append(Paragraph("Allokat — Portfolio-Allokation", title_style))
    story.append(Paragraph(f"Stand: {date.today().strftime('%d.%m.%Y')}", normal))
    story.append(Spacer(1, 0.5 * cm))

    # Gesamtübersicht
    story.append(Paragraph("Gesamtübersicht", h2_style))
    overview = [
        ["Gesamtvermögen (CHF)", f"CHF {portfolio['total_chf']:,.0f}"],
        [
            "Nicht durchgerechnet",
            f"CHF {portfolio['nicht_durchgerechnet_chf']:,.0f} "
            f"({portfolio['nicht_durchgerechnet_pct'] * 100:.1f}%)",
        ],
    ]
    story.append(_make_table(overview))
    story.append(Spacer(1, 0.4 * cm))

    for title, data_key in [
        ("Asset-Klassen", "asset_klassen"),
        ("Sektoren", "sektoren"),
        ("Währungen", "waehrungen"),
        ("Banken", "banken"),
    ]:
        story.append(Paragraph(title, h2_style))
        rows = [
            [k, f"{v * 100:.1f}%"] for k, v in portfolio[data_key].items()
        ]
        if rows:
            story.append(_make_table(rows))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Allokat zeigt den Ist-Zustand Ihres Portfolios. "
            "Dies ist keine Anlageberatung.",
            ParagraphStyle("Disclaimer", parent=normal, fontSize=8, textColor=colors.grey),
        )
    )

    doc.build(story)
    return output.getvalue()


def _make_table(rows: list[list]) -> Table:
    t = Table(rows, colWidths=[10 * cm, 5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ALLOKAT_LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1C2833")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, ALLOKAT_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t
