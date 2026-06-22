"""
Allokations-Engine — Kernlogik von Allokat.

Aggregiert Depot-Positionen (inkl. ETF-Durchrechnung) zu einer
einheitlichen Portfolio-Allokation in CHF.
"""

from collections import defaultdict
from config.settings import FX_RATES_TO_CHF
from modules.sektor_mapping import normalize, normalize_dict


def to_chf(marktwert: float, waehrung: str) -> float:
    rate = FX_RATES_TO_CHF.get(waehrung.upper(), 1.0)
    return marktwert * rate


def compute_portfolio(depots: list[dict], lookup_results: dict) -> dict:
    """
    depots: Liste von Depot-Dicts (Output von extractor + user-edits)
    lookup_results: {isin: LookupResult} für ETF/Fonds-Positionen

    Gibt zurück:
    {
      "total_chf": 450000.0,
      "asset_klassen": {"ETF": 0.55, "Aktie": 0.30, ...},
      "sektoren": {"Technologie": 0.28, ...},
      "waehrungen": {"CHF": 0.72, "USD": 0.18, ...},
      "banken": {"UBS": 0.60, "Swissquote": 0.40},
      "nicht_durchgerechnet_chf": 50000.0,
      "positionen_detail": [...],
    }
    """
    total_chf = 0.0
    asset_klassen_chf: dict[str, float] = defaultdict(float)
    sektoren_chf: dict[str, float] = defaultdict(float)
    waehrungen_chf: dict[str, float] = defaultdict(float)
    banken_chf: dict[str, float] = defaultdict(float)
    nicht_durchgerechnet_chf = 0.0
    positionen_detail = []
    rendite_chf_total = 0.0
    einstandswert_chf_total = 0.0

    for depot in depots:
        bank = depot.get("bank", "Unbekannt")
        for pos in depot.get("positionen", []):
            raw_mw = pos.get("marktwert")
            mw = 0.0 if (raw_mw is None or (isinstance(raw_mw, float) and raw_mw != raw_mw)) else float(raw_mw)
            raw_esw = pos.get("einstandswert")
            esw = None if (raw_esw is None or (isinstance(raw_esw, float) and raw_esw != raw_esw)) else float(raw_esw)
            raw_rendite = pos.get("rendite_chf")
            rendite = None if (raw_rendite is None or (isinstance(raw_rendite, float) and raw_rendite != raw_rendite)) else float(raw_rendite)
            waehrung = str(pos.get("waehrung") or "CHF")
            typ = str(pos.get("typ") or "Unbekannt")
            isin = str(pos.get("isin") or "")
            if isin.lower() in ("nan", "none"):
                isin = ""
            bezeichnung = str(pos.get("bezeichnung") or "")
            chf_wert = to_chf(mw, waehrung)
            esw_chf = to_chf(esw, waehrung) if esw is not None else None
            rendite_chf_pos = to_chf(rendite, waehrung) if rendite is not None else None

            if chf_wert <= 0:
                continue

            total_chf += chf_wert
            asset_klassen_chf[typ] += chf_wert
            waehrungen_chf[waehrung] += chf_wert
            banken_chf[bank] += chf_wert
            if esw_chf is not None:
                einstandswert_chf_total += esw_chf
            if rendite_chf_pos is not None:
                rendite_chf_total += rendite_chf_pos

            rendite_pct_pos = None
            if rendite_chf_pos is not None and esw_chf is not None and esw_chf != 0:
                rendite_pct_pos = round(rendite_chf_pos / esw_chf * 100, 2)

            pos_detail = {
                "bank": bank,
                "isin": isin,
                "bezeichnung": bezeichnung,
                "typ": typ,
                "marktwert_orig": mw,
                "waehrung": waehrung,
                "marktwert_chf": chf_wert,
                "einstandswert_chf": esw_chf,
                "rendite_chf": rendite_chf_pos,
                "rendite_pct": rendite_pct_pos,
                "sektoren_beitrag": {},
                "confidence": "direkt",
            }

            if typ in ("ETF", "Fonds", "Aktie") and isin in lookup_results:
                lr = lookup_results[isin]
                if lr.gefunden and lr.sektoren:
                    for sektor, anteil in lr.sektoren.items():
                        beitrag = chf_wert * anteil
                        sektoren_chf[normalize(sektor)] += beitrag
                        pos_detail["sektoren_beitrag"][normalize(sektor)] = anteil
                    pos_detail["confidence"] = lr.confidence
                else:
                    # Kein Lookup-Treffer → nicht durchgerechnet (gilt auch für Aktien)
                    nicht_durchgerechnet_chf += chf_wert
                    pos_detail["confidence"] = "nicht_durchgerechnet"
            elif typ == "Aktie":
                # Aktie ohne ISIN oder ohne Lookup → nicht durchgerechnet
                nicht_durchgerechnet_chf += chf_wert
                pos_detail["confidence"] = "nicht_durchgerechnet"
            elif typ == "Anleihe":
                sektoren_chf[normalize("Anleihen")] += chf_wert
                pos_detail["sektoren_beitrag"][normalize("Anleihen")] = 1.0
                pos_detail["confidence"] = "direkt"
            elif typ == "Cash":
                sektoren_chf[normalize("Cash")] += chf_wert
                pos_detail["sektoren_beitrag"][normalize("Cash")] = 1.0
                pos_detail["confidence"] = "direkt"
            else:
                nicht_durchgerechnet_chf += chf_wert
                pos_detail["confidence"] = "nicht_durchgerechnet"

            positionen_detail.append(pos_detail)

    def to_pct(d: dict[str, float]) -> dict[str, float]:
        t = sum(d.values())
        if t == 0:
            return {}
        return {k: round(v / t, 4) for k, v in sorted(d.items(), key=lambda x: -x[1])}

    einstandswert_basis = total_chf - rendite_chf_total if rendite_chf_total else None
    rendite_pct_total = None
    if rendite_chf_total and einstandswert_basis and einstandswert_basis != 0:
        rendite_pct_total = round(rendite_chf_total / einstandswert_basis * 100, 2)

    return {
        "total_chf": round(total_chf, 2),
        "asset_klassen": to_pct(asset_klassen_chf),
        "sektoren": to_pct(sektoren_chf),
        "waehrungen": to_pct(waehrungen_chf),
        "banken": to_pct(banken_chf),
        "nicht_durchgerechnet_chf": round(nicht_durchgerechnet_chf, 2),
        "nicht_durchgerechnet_pct": (
            round(nicht_durchgerechnet_chf / total_chf, 4) if total_chf > 0 else 0
        ),
        "rendite_chf": round(rendite_chf_total, 2) if rendite_chf_total else None,
        "rendite_pct": rendite_pct_total,
        "einstandswert_chf": round(einstandswert_chf_total, 2) if einstandswert_chf_total else None,
        "positionen_detail": positionen_detail,
    }
