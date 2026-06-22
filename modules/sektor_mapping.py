"""
Normalisiert Sektornamen aus verschiedenen Quellen auf einheitliche Bezeichnungen.

Strategie (in Reihenfolge):
1. Exakter Match (dict lookup)
2. Case-insensitiver Match
3. Semantisches Keyword-Matching (Substring + Priorität)
"""

# ── Exact mapping (case-sensitive) ────────────────────────────────────────────

SEKTOR_MAP: dict[str, str] = {
    # ─── Technologie ───
    "Technology": "Technologie",
    "Information Technology": "Technologie",
    "Informationstechnologie": "Technologie",
    "IT": "Technologie",
    "Tech": "Technologie",
    "Technologie": "Technologie",
    "Informations-technologie": "Technologie",
    "Software": "Technologie",
    "Hardware": "Technologie",
    "Semiconductors": "Technologie",
    "Halbleiter": "Technologie",

    # ─── Finanzen ───
    "Financials": "Finanzen",
    "Financial Services": "Finanzen",
    "Finanzwesen": "Finanzen",
    "Finanzdienstleistungen": "Finanzen",
    "Finanzen": "Finanzen",
    "Finance": "Finanzen",
    "Banks": "Finanzen",
    "Banken": "Finanzen",
    "Versicherungen": "Finanzen",
    "Insurance": "Finanzen",
    "Diversified Financials": "Finanzen",

    # ─── Gesundheit ───
    "Health Care": "Gesundheit",
    "Health care": "Gesundheit",
    "Healthcare": "Gesundheit",
    "Gesundheitswesen": "Gesundheit",
    "Gesundheit": "Gesundheit",
    "Pharma": "Gesundheit",
    "Pharmazeutika": "Gesundheit",
    "Pharmaceuticals": "Gesundheit",
    "Biotechnologie": "Gesundheit",
    "Biotechnology": "Gesundheit",
    "Medizintechnik": "Gesundheit",
    "Medical Devices": "Gesundheit",
    "Life Sciences": "Gesundheit",

    # ─── Konsum (zyklisch) ───
    "Consumer Discretionary": "Konsum (zyklisch)",
    "Consumer Cyclical": "Konsum (zyklisch)",
    "Zyklischer Konsum": "Konsum (zyklisch)",
    "Zyklische Konsumgüter": "Konsum (zyklisch)",
    "Konsumgüter (zyklisch)": "Konsum (zyklisch)",
    "Nicht-Basiskonsumgüter": "Konsum (zyklisch)",
    "Discretionary": "Konsum (zyklisch)",
    "Luxusgüter": "Konsum (zyklisch)",

    # ─── Konsum (defensiv) ───
    "Consumer Staples": "Konsum (defensiv)",
    "Consumer Defensive": "Konsum (defensiv)",
    "Basiskonsumgüter": "Konsum (defensiv)",
    "Nicht-zyklische Konsumgüter": "Konsum (defensiv)",
    "Nicht-zyklischer Konsum": "Konsum (defensiv)",
    "Konsumgüter (nicht-zyklisch)": "Konsum (defensiv)",
    "Konsumgüter (Nicht-zyklisch)": "Konsum (defensiv)",
    "Defensive Konsumgüter": "Konsum (defensiv)",
    "Konsumgüter": "Konsum (defensiv)",
    "Nahrungsmittel": "Konsum (defensiv)",
    "Food & Beverage": "Konsum (defensiv)",

    # ─── Industrie ───
    "Industrials": "Industrie",
    "Industrial": "Industrie",
    "Industrie": "Industrie",
    "Industriegüter": "Industrie",
    "Industrieunternehmen": "Industrie",
    "Manufacturing": "Industrie",

    # ─── Kommunikation ───
    "Communication Services": "Kommunikation",
    "Communication": "Kommunikation",
    "Kommunikation": "Kommunikation",
    "Kommunikationsdienstleistungen": "Kommunikation",
    "Telekommunikation": "Kommunikation",
    "Telecommunications": "Kommunikation",
    "Telecom": "Kommunikation",
    "Medien": "Kommunikation",
    "Media": "Kommunikation",

    # ─── Energie ───
    "Energy": "Energie",
    "Energie": "Energie",
    "Oil & Gas": "Energie",

    # ─── Rohstoffe ───
    "Materials": "Rohstoffe",
    "Basic Materials": "Rohstoffe",
    "Rohstoffe": "Rohstoffe",
    "Materialien": "Rohstoffe",
    "Grundstoffe": "Rohstoffe",
    "Werkstoffe": "Rohstoffe",
    "Chemicals": "Rohstoffe",
    "Chemie": "Rohstoffe",
    "Metals & Mining": "Rohstoffe",

    # ─── Immobilien ───
    "Real Estate": "Immobilien",
    "Immobilien": "Immobilien",
    "Liegenschaften": "Immobilien",
    "REITs": "Immobilien",
    "Property": "Immobilien",

    # ─── Versorger ───
    "Utilities": "Versorger",
    "Versorger": "Versorger",
    "Versorgungsbetriebe": "Versorger",
    "Versorgung": "Versorger",
    "Versorgungsunternehmen": "Versorger",
    "Öffentliche Versorgungsunternehmen": "Versorger",

    # ─── Anleihen ───
    "Corporate": "Unternehmensanleihen",
    "Corporate Bonds": "Unternehmensanleihen",
    "Unternehmensanleihen": "Unternehmensanleihen",
    "Government": "Staatsanleihen",
    "Government Bonds": "Staatsanleihen",
    "Staatsanleihen": "Staatsanleihen",
    "Sovereign": "Staatsanleihen",
    "Anleihen": "Anleihen",
    "Obligationen": "Anleihen",
    "Fixed Income": "Anleihen",
    "Bonds": "Anleihen",

    # ─── Liquidität ───
    "Cash & Equivalents": "Liquidität",
    "Cash": "Liquidität",
    "Liquidität": "Liquidität",
    "Geldmarkt": "Liquidität",
    "Barmittel": "Liquidität",
    "Money Market": "Liquidität",

    # ─── Andere ───
    "Other": "Andere",
    "Andere": "Andere",
    "Others": "Andere",
    "Sonstige": "Andere",
    "Übrige": "Andere",
}

# ── Semantic keyword rules ────────────────────────────────────────────────────
# (keywords_in_lowercase, canonical_name)
# Checked as substrings in lowercased input. ORDER MATTERS.

_KEYWORD_RULES: list[tuple[list[str], str]] = [
    # Technologie — spezifisch zuerst
    (["informationstechnolog", "information technolog"], "Technologie"),
    (["technolog", "software", "halbleiter", "semiconductor", "hardware", "digital"], "Technologie"),

    # Konsum — zyklisch vs. defensiv BEFORE generic "konsum"
    (["zyklisch", "discretionary", "cyclical", "luxury", "luxus", "nicht-basis", "nicht basis"], "Konsum (zyklisch)"),
    (["nicht-zyklisch", "nicht zyklisch", "defensiv", "staples", "basiskons", "lebensmittel",
      "nahrung", "food", "getränk", "beverage"], "Konsum (defensiv)"),

    # Finanzen
    (["finanz", "bank", "versicherung", "insurance", "asset management", "wealth"], "Finanzen"),

    # Gesundheit
    (["gesundheit", "health", "pharma", "biotech", "medizin", "medical", "hospital",
      "life science", "biowiss"], "Gesundheit"),

    # Industrie
    (["industrie", "industrial", "manufactur", "fertig", "maschinen", "aerospace",
      "logistik", "transport"], "Industrie"),

    # Kommunikation
    (["kommunikation", "telecom", "telekommunikation", "medien", "media",
      "internet", "communication"], "Kommunikation"),

    # Energie
    (["energie", "energy", "öl & gas", "oil & gas", "oil gas", "fossil", "petrol"], "Energie"),

    # Rohstoffe
    (["rohstoff", "basic material", "chemie", "chemical", "metall", "metal",
      "mining", "bergbau", "grundstoff", "werkstoff"], "Rohstoffe"),

    # Immobilien
    (["immobilien", "real estate", "reit", "liegenschaft", "property"], "Immobilien"),

    # Versorger
    (["versorger", "versorgung", "utilities", "öffentlich"], "Versorger"),

    # Staatsanleihen
    (["staatsanleihe", "government bond", "sovereign", "staatsobligat"], "Staatsanleihen"),

    # Unternehmensanleihen
    (["unternehmensanleihe", "corporate bond", "firmenanleihe"], "Unternehmensanleihen"),

    # Anleihen (generic)
    (["anleihe", "obligat", "fixed income", "renten"], "Anleihen"),

    # Liquidität
    (["liquidit", "geldmarkt", "money market", "barmittel"], "Liquidität"),

    # Energie (broad — after oil/gas already checked)
    (["energie", "energy"], "Energie"),

    # Konsum generic fallback
    (["konsum", "consumer", "einzelhandel", "retail", "handel"], "Konsum (zyklisch)"),

    # Tech fallback
    (["tech", " it "], "Technologie"),

    # Rohstoffe fallback (material is a common English word — low priority)
    (["material"], "Rohstoffe"),
]


def normalize(sektor: str) -> str:
    """
    Normalisiert einen Sektornamen auf die kanonische deutsche Bezeichnung.

    1. Exakter Match → sofort
    2. Case-insensitiver Match
    3. Semantisches Keyword-Matching (Substring)
    4. Original behalten
    """
    if not sektor or not sektor.strip():
        return sektor

    # 1. Exakt
    if sektor in SEKTOR_MAP:
        return SEKTOR_MAP[sektor]

    # 2. Case-insensitiv
    lower = sektor.strip().lower()
    for k, v in SEKTOR_MAP.items():
        if k.lower() == lower:
            return v

    # 3. Semantisches Keyword-Matching
    for keywords, canonical in _KEYWORD_RULES:
        if any(kw in lower for kw in keywords):
            return canonical

    return sektor


def normalize_dict(sektoren: dict[str, float]) -> dict[str, float]:
    """
    Normalisiert alle Keys und summiert Duplikate.
    """
    result: dict[str, float] = {}
    for key, val in sektoren.items():
        normalized = normalize(key)
        result[normalized] = result.get(normalized, 0.0) + val
    return result
