"""
Erstellt realistische Beispiel-Depotauszüge als PDF.
Ausführen: python test_data/create_test_pdfs.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

OUT_DIR = os.path.dirname(__file__)


def _base_style():
    styles = getSampleStyleSheet()
    return styles


def make_ubs_depot():
    """UBS Schweiz — gemischtes Depot: CH-Aktien + MSCI World ETF + Anleihe + Cash"""
    path = os.path.join(OUT_DIR, "depot_ubs_schweiz.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _base_style()
    story = []

    NAVY = colors.HexColor("#002244")
    LIGHT = colors.HexColor("#F0F4F8")

    title_style = ParagraphStyle("T", parent=styles["Heading1"], textColor=NAVY, fontSize=16)
    sub_style = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    normal = styles["Normal"]

    story.append(Paragraph("UBS Switzerland AG", title_style))
    story.append(Paragraph("Depotauszug", ParagraphStyle("D", parent=styles["Heading2"],
                                                          textColor=NAVY, fontSize=13)))
    story.append(Spacer(1, 0.3*cm))

    meta = [
        ["Depot-Nr.", "231-456789.01A", "Datum", "31.05.2026"],
        ["Inhaber", "Max Mustermann", "Währung", "CHF"],
        ["Adresse", "Bahnhofstrasse 1, 8001 Zürich", "Berater", "P. Meier"],
    ]
    t_meta = Table(meta, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    t_meta.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Wertschriften-Positionen", ParagraphStyle("H",
                            parent=styles["Heading3"], textColor=NAVY)))
    story.append(Spacer(1, 0.2*cm))

    positions_header = ["ISIN", "Bezeichnung", "Stücke", "Kurs", "Marktwert CHF", "Typ"]
    positions = [
        ["CH0012221716", "ABB Ltd, Namenaktie", "200", "CHF 51.82", "10'364.00", "Aktie"],
        ["CH0012032048", "Roche Holding AG, Genussschein", "50", "CHF 268.50", "13'425.00", "Aktie"],
        ["CH0038863350", "Nestlé SA, Namenaktie", "150", "CHF 74.30", "11'145.00", "Aktie"],
        ["IE00B4L5Y983", "iShares Core MSCI World UCITS ETF USD (Acc)", "500", "USD 103.20", "46'152.00", "ETF"],
        ["IE00B3RBWM25", "Vanguard FTSE All-World UCITS ETF USD (Dist)", "300", "USD 118.40", "31'363.20", "ETF"],
        ["CH0224397009", "Eidgenossenschaft 0.5% 2031 CHF", "10'000", "97.25%", "9'725.00", "Anleihe"],
        ["—", "Kontokorrent CHF", "—", "—", "18'430.00", "Cash"],
    ]
    all_rows = [positions_header] + positions
    col_widths = [3.2*cm, 6.5*cm, 1.8*cm, 2.5*cm, 2.8*cm, 1.8*cm]
    t_pos = Table(all_rows, colWidths=col_widths)
    t_pos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
    ]))
    story.append(t_pos)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Gesamtwert Portfolio", ParagraphStyle("H2",
                            parent=styles["Heading3"], textColor=NAVY)))
    total_table = Table([
        ["Aktien CH", "CHF 34'934.00"],
        ["ETFs", "CHF 77'515.20"],
        ["Anleihen", "CHF 9'725.00"],
        ["Liquidität", "CHF 18'430.00"],
        ["", ""],
        ["Total Depot", "CHF 140'604.20"],
    ], colWidths=[8*cm, 5*cm])
    total_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("LINEABOVE", (0, 5), (-1, 5), 1, NAVY),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(total_table)

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "Dieser Auszug dient zu Informationszwecken. Massgeblich sind die Angaben in Ihrem e-Banking.",
        sub_style
    ))

    doc.build(story)
    print(f"✓ {path}")


def make_swissquote_depot():
    """Swissquote — ETF-fokussiertes Depot + EM-ETF + Tech-ETF"""
    path = os.path.join(OUT_DIR, "depot_swissquote.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _base_style()
    story = []

    ORANGE = colors.HexColor("#E8620A")
    LIGHT = colors.HexColor("#FFF3EC")

    story.append(Paragraph("Swissquote Bank AG", ParagraphStyle("T",
                            parent=styles["Heading1"], textColor=ORANGE, fontSize=16)))
    story.append(Paragraph("Depot-Übersicht / Relevé de dépôt",
                            ParagraphStyle("S", parent=styles["Normal"], fontSize=10,
                                           textColor=colors.grey)))
    story.append(Spacer(1, 0.4*cm))

    meta = [
        ["Konto-Nr.", "SQ-748291-X", "Datum:", "31.05.2026"],
        ["Name:", "Anna Muster", "Basiswährung:", "CHF"],
    ]
    t_meta = Table(meta, colWidths=[3*cm, 7*cm, 3*cm, 4*cm])
    t_meta.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Depotpositionen", ParagraphStyle("H",
                            parent=styles["Heading3"], textColor=ORANGE)))

    header = ["ISIN", "Bezeichnung", "Anzahl", "Kurs (USD)", "Kurs CHF", "Wert CHF"]
    rows = [
        ["IE00B3RBWM25", "Vanguard FTSE All-World ETF (VWRL)", "1'200", "118.40", "104.52", "125'424.00"],
        ["IE00BKM4GZ66", "iShares MSCI EM IMI ETF (EIMI)", "800", "34.20", "30.20", "24'156.80"],
        ["IE00B53SZB19", "iShares Nasdaq 100 ETF (CNDX)", "150", "542.80", "479.28", "71'892.00"],
        ["LU0629459743", "UBS ETF MSCI Switzerland", "400", "—", "CHF 143.70", "57'480.00"],
        ["—", "Cash USD", "—", "—", "—", "8'320.00"],
        ["—", "Cash CHF", "—", "—", "—", "5'102.50"],
    ]
    all_rows = [header] + rows
    col_w = [3.2*cm, 5.8*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm]
    t = Table(all_rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (5, 0), (5, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    summary = Table([
        ["Gesamtwert Depot", "CHF 292'375.30"],
        ["davon Cash", "CHF 13'422.50"],
        ["davon Wertschriften", "CHF 278'952.80"],
    ], colWidths=[8*cm, 5*cm])
    summary.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(summary)

    doc.build(story)
    print(f"✓ {path}")


def make_neobroker_depot():
    """Yuh/Neobroker — einfaches Depot, abweichendes Layout"""
    path = os.path.join(OUT_DIR, "depot_neobroker_yuh.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _base_style()
    story = []

    PURPLE = colors.HexColor("#5B2D8E")

    story.append(Paragraph("yuh — Depot Report", ParagraphStyle("T",
                            parent=styles["Heading1"], textColor=PURPLE, fontSize=18)))
    story.append(Paragraph("Erstellt am 31.05.2026 | Konto: YUH-20291847",
                            ParagraphStyle("S", parent=styles["Normal"], fontSize=9,
                                           textColor=colors.grey)))
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Deine Investments", ParagraphStyle("H",
                            parent=styles["Heading2"], textColor=PURPLE)))
    story.append(Spacer(1, 0.2*cm))

    rows = [
        ["Name", "ISIN", "Stücke", "Aktueller Kurs", "Marktwert"],
        ["iShares Core MSCI World ETF", "IE00B4L5Y983", "250", "USD 103.20", "CHF 22'806.00"],
        ["Vanguard FTSE All-World ETF", "IE00B3RBWM25", "180", "USD 118.40", "CHF 18'817.92"],
        ["Apple Inc.", "US0378331005", "30", "USD 198.50", "CHF 5'258.55"],
        ["Microsoft Corp.", "US5949181045", "20", "USD 455.20", "CHF 8'037.73"],
        ["Spareinlage CHF", "—", "—", "—", "CHF 3'200.00"],
    ]
    col_w = [5*cm, 3.2*cm, 2*cm, 3*cm, 4.3*cm]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F0FA")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Gesamtwert: CHF 58'120.20",
                            ParagraphStyle("Total", parent=styles["Heading3"],
                                           textColor=PURPLE)))

    doc.build(story)
    print(f"✓ {path}")


def make_vwrl_factsheet():
    """Beispiel-Factsheet für Vanguard FTSE All-World ETF"""
    path = os.path.join(OUT_DIR, "factsheet_vwrl_vanguard.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = _base_style()
    story = []

    RED = colors.HexColor("#961B1E")
    LIGHT = colors.HexColor("#FDECEA")

    story.append(Paragraph("Vanguard FTSE All-World UCITS ETF",
                            ParagraphStyle("T", parent=styles["Heading1"],
                                           textColor=RED, fontSize=15)))
    story.append(Paragraph("ISIN: IE00B3RBWM25 | Ticker: VWRL | Fondswährung: USD",
                            ParagraphStyle("S", parent=styles["Normal"], fontSize=9,
                                           textColor=colors.grey)))
    story.append(Paragraph("Holdings per 31. Mai 2026",
                            ParagraphStyle("D", parent=styles["Normal"], fontSize=9,
                                           textColor=RED)))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Sektoraufteilung", ParagraphStyle("H",
                            parent=styles["Heading3"], textColor=RED)))
    sector_data = [
        ["Sektor", "Anteil"],
        ["Technologie", "23.2%"],
        ["Finanzen", "16.3%"],
        ["Gesundheit", "11.6%"],
        ["Zyklischer Konsum", "11.2%"],
        ["Industrie", "10.8%"],
        ["Kommunikation", "8.3%"],
        ["Basiskonsumgüter", "6.2%"],
        ["Energie", "4.7%"],
        ["Versorger", "2.8%"],
        ["Immobilien", "2.5%"],
        ["Rohstoffe", "2.4%"],
        ["Total", "100.0%"],
    ]
    t_s = Table(sector_data, colWidths=[8*cm, 4*cm])
    t_s.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT]),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, RED),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(t_s)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Regionale Aufteilung", ParagraphStyle("H",
                            parent=styles["Heading3"], textColor=RED)))
    region_data = [
        ["Region", "Anteil"],
        ["Nordamerika", "63.2%"],
        ["Europa", "16.6%"],
        ["Asien-Pazifik (Industrieländer)", "12.8%"],
        ["Schwellenländer", "7.4%"],
        ["Total", "100.0%"],
    ]
    t_r = Table(region_data, colWidths=[8*cm, 4*cm])
    t_r.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT]),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, RED),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(t_r)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "Quelle: Vanguard Asset Management. Nur zu Informationszwecken.",
        ParagraphStyle("Disc", parent=styles["Normal"], fontSize=7, textColor=colors.grey)
    ))

    doc.build(story)
    print(f"✓ {path}")


if __name__ == "__main__":
    print("Erstelle Test-PDFs...")
    make_ubs_depot()
    make_swissquote_depot()
    make_neobroker_depot()
    make_vwrl_factsheet()
    print("\nAlle Test-PDFs erstellt.")
