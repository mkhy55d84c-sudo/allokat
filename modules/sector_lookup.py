"""
Sektor-Lookup für ETFs und Fonds.

Lookup-Hierarchie:
1. Curated ETF database (config/settings.py) — sofort, offline
2. Factsheet-geparste Daten (modules/factsheet_parser.py) — wenn vom Nutzer hochgeladen
3. Nicht durchgerechnet — wenn keine Quelle verfügbar

Für Direktaktien: kein Sektor-Lookup nötig, sie zählen direkt
als 100% der jeweiligen Aktien-Allokation.
"""

from config.settings import KNOWN_ETFS


class LookupResult:
    def __init__(
        self,
        isin: str,
        name: str,
        gefunden: bool,
        sektoren: dict | None,
        regionen: dict | None,
        daten_stand: str | None,
        confidence: str,
    ):
        self.isin = isin
        self.name = name
        self.gefunden = gefunden
        self.sektoren = sektoren or {}
        self.regionen = regionen or {}
        self.daten_stand = daten_stand
        # confidence: "automatisch" | "factsheet" | "nutzer_bestätigt" | "nicht_durchgerechnet"
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "isin": self.isin,
            "name": self.name,
            "gefunden": self.gefunden,
            "sektoren": self.sektoren,
            "regionen": self.regionen,
            "daten_stand": self.daten_stand,
            "confidence": self.confidence,
        }


def lookup_etf_sektoren(isin: str, bezeichnung: str) -> LookupResult:
    """Sucht Sektor-Allokation für eine ETF/Fonds-Position."""
    if not isin:
        return LookupResult(
            isin=isin or "",
            name=bezeichnung,
            gefunden=False,
            sektoren=None,
            regionen=None,
            daten_stand=None,
            confidence="nicht_durchgerechnet",
        )

    isin_clean = isin.strip().upper()

    if isin_clean in KNOWN_ETFS:
        data = KNOWN_ETFS[isin_clean]
        return LookupResult(
            isin=isin_clean,
            name=data["name"],
            gefunden=True,
            sektoren=data["sektoren"],
            regionen=data.get("regionen"),
            daten_stand=data["daten_stand"],
            confidence="automatisch",
        )

    # Nicht in curated DB → Smart Agent sucht automatisch die richtige Quelle
    try:
        from modules.smart_lookup import smart_lookup
        data = smart_lookup(isin_clean, bezeichnung)
        if data and (data.get("sektoren") or data.get("regionen")):
            # Source aus Cache übernehmen, für UI-Label
            source = data.get("source", "automatisch")
            confidence = source if source in ("oracle", "yfinance", "factsheet", "swissfunddata") else "automatisch"
            return LookupResult(
                isin=isin_clean,
                name=data.get("fonds_name") or bezeichnung,
                gefunden=True,
                sektoren=data.get("sektoren") or {},
                regionen=data.get("regionen"),
                daten_stand=data.get("daten_stand"),
                confidence=confidence,
            )
    except Exception:
        pass

    return LookupResult(
        isin=isin_clean,
        name=bezeichnung,
        gefunden=False,
        sektoren=None,
        regionen=None,
        daten_stand=None,
        confidence="nicht_durchgerechnet",
    )


def apply_factsheet_data(
    result: LookupResult, sektoren: dict, regionen: dict, daten_stand: str
) -> LookupResult:
    """Überschreibt einen Lookup-Result mit Factsheet-Daten."""
    result.gefunden = True
    result.sektoren = sektoren
    result.regionen = regionen
    result.daten_stand = daten_stand
    result.confidence = "factsheet"
    return result


def mark_user_confirmed(result: LookupResult) -> LookupResult:
    result.confidence = "nutzer_bestätigt"
    return result
