"""
Smart Lookup — findet Sektor-/Regionendaten für jedes Finanzinstrument.

Strategie (in Reihenfolge):
1. Cache (lokale JSON-Datei, TTL 30/90d)         → sofort, gratis
2. OpenFIGI API (ISIN → Typ + Ticker)             → gratis, kein API-Key
3a. yfinance (für Aktien: GICS-Sektor)            → gratis, 100% Coverage
3b. Claude Haiku Oracle (für ETFs + Fonds)        → Training-Wissen, ~$0.001/lookup
4. Fallback: None                                 → UI zeigt "nicht_durchgerechnet"

Kein Scraping. Kein manuelles Datenbankpflegen.
"""

import json
import os
import requests
import anthropic
from modules.cache import get as cache_get, put as cache_put
from modules.sektor_mapping import normalize as _norm, normalize_dict as _norm_dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Allokat/1.0)",
    "Accept": "application/json",
}


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY nicht gesetzt.")
    return anthropic.Anthropic(api_key=api_key)


# ── Schritt 2: OpenFIGI — ISIN → Typ + Ticker ────────────────────────────────

def _resolve_isin(isin: str) -> dict | None:
    """
    OpenFIGI: ISIN → {type, ticker, name, exchange}
    Kostenlos, kein API-Key nötig.
    Instrument-Types: "ETP" = ETF, "Common Stock", "Mutual Fund", etc.
    """
    try:
        resp = requests.post(
            "https://api.openfigi.com/v3/mapping",
            json=[{"idType": "ID_ISIN", "idValue": isin}],
            headers=HEADERS,
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        results = resp.json()
        if not results or not results[0].get("data"):
            return None

        # Bevorzuge: Hauptbörse (SIX, XSWX, LSE, NYSE, XETRA)
        preferred_exchanges = {"SW", "LN", "UN", "UW", "GY", "FP", "VX"}
        entries = results[0]["data"]

        best = None
        for entry in entries:
            exchange = entry.get("exchCode", "")
            if exchange in preferred_exchanges:
                best = entry
                break
        if not best:
            best = entries[0]

        sec_type = best.get("securityType", "")
        sec_type2 = best.get("securityType2", "")
        name = best.get("name", "")
        ticker = best.get("ticker", "")
        exchange = best.get("exchCode", "")

        # Typ bestimmen
        if "ETP" in sec_type or "ETF" in sec_type.upper() or "Fund" in sec_type2:
            instrument_type = "etf"
        elif "Common Stock" in sec_type or "Equity" in sec_type2:
            instrument_type = "stock"
        elif "Mutual Fund" in sec_type:
            instrument_type = "fund"
        else:
            instrument_type = "unknown"

        return {
            "type": instrument_type,
            "ticker": ticker,
            "name": name,
            "exchange": exchange,
            "sec_type": sec_type,
        }
    except Exception:
        return None


# ── Schritt 3a: yfinance — Sektor für Aktien ─────────────────────────────────

def _yfinance_sector(ticker: str, exchange: str) -> dict | None:
    """
    yfinance: Ticker → GICS-Sektor.
    Mappt Börsencode auf Yahoo-Suffix (z.B. SW → .SW für SIX).
    """
    try:
        import yfinance as yf

        exchange_suffix = {
            "SW": ".SW", "VX": ".SW",
            "LN": ".L",
            "GY": ".DE", "GF": ".F",
            "FP": ".PA",
            "NA": ".AS",
            "BB": ".BR",
            "IM": ".MI",
            "SM": ".MC",
        }
        suffix = exchange_suffix.get(exchange, "")
        symbol = f"{ticker}{suffix}"

        info = yf.Ticker(symbol).info
        sector_en = info.get("sector", "")
        if not sector_en:
            # Fallback ohne Suffix
            info = yf.Ticker(ticker).info
            sector_en = info.get("sector", "")

        if not sector_en:
            return None

        sector_de = _norm(sector_en)
        return {
            "fonds_name": info.get("longName") or info.get("shortName", ""),
            "daten_stand": None,
            "sektoren": {sector_de: 1.0},
            "regionen": None,
        }
    except Exception:
        return None


# ── Schritt 3b: Claude Oracle — Sektor für ETFs + Fonds ──────────────────────

def _claude_oracle(isin: str, bezeichnung: str, instrument_type: str, client: anthropic.Anthropic) -> dict | None:
    """
    Claude Haiku als Finanz-Oracle.
    Für Aktien: gibt 100% einen Sektor zurück.
    Für ETFs/Fonds: gibt Sektor-Allokation zurück.
    """
    if instrument_type == "stock":
        # Einzelaktie: nur GICS-Sektor ermitteln
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": f"""Du bist ein Finanz-Experte. Bestimme den GICS-Sektor dieser Aktie.

ISIN: {isin}
Name/Bezeichnung: {bezeichnung}

Antworte NUR mit diesem JSON (kein Text drumherum):
{{"sektor": "Finanzen"}}

Mögliche Sektoren (auf Deutsch): Technologie, Finanzen, Gesundheit, Konsum (zyklisch), Konsum (defensiv), Industrie, Kommunikation, Energie, Rohstoffe, Immobilien, Versorger

Auch wenn du dir nicht 100% sicher bist: gib trotzdem den wahrscheinlichsten Sektor. Nur wenn die Bezeichnung absolut nichts verrät: gib {{"sektor": null}}""",
            }],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            data = json.loads(raw)
            sektor = data.get("sektor")
            if not sektor:
                return None
            sektor_norm = _norm(sektor)
            return {
                "fonds_name": bezeichnung,
                "daten_stand": None,
                "sektoren": {sektor_norm: 1.0},
                "regionen": None,
            }
        except Exception:
            return None

    type_hint = {
        "etf": "ETF / Indexfonds",
        "fund": "aktiv verwalteter Fonds",
        "unknown": "Fonds oder ETF",
    }.get(instrument_type, "Fonds oder ETF")

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": f"""Du bist ein Finanz-Experte. Liefere die Sektor-Allokation für dieses Instrument.

ISIN: {isin}
Name: {bezeichnung}
Typ: {type_hint}

Aufgabe: Gib die Sektor-Allokation als JSON zurück. Nutze dein Wissen über diesen Fonds/ETF.
- Für ETFs wie MSCI World, S&P 500, Sektor-ETFs etc. kennst du die typische Zusammensetzung.
- Für aktiv verwaltete Fonds: schätze basierend auf Fondsnamen und Anlagestrategie.
- Gib IMMER eine Schätzung — auch wenn unsicher. Nur wenn die Bezeichnung absolut nichts verrät: null.

Antwortformat — nur reines JSON:
{{
  "fonds_name": "Vollständiger Name",
  "sektoren": {{
    "Technologie": 0.25,
    "Finanzen": 0.15,
    "Gesundheit": 0.12
  }},
  "regionen": {{
    "Nordamerika": 0.70,
    "Europa": 0.18,
    "Asien-Pazifik": 0.12
  }},
  "confidence": "hoch"
}}

Sektor-Namen auf Deutsch. Summe ≈ 1.0. Null nur wenn wirklich unbekannt.""",
        }],
    )

    raw = msg.content[0].text.strip()
    # JSON aus Antwort extrahieren
    if raw == "null":
        return None

    # Markdown-Fences entfernen
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
        if not data or not data.get("sektoren"):
            return None
        # Summe normalisieren
        total = sum(data["sektoren"].values())
        if total > 0 and abs(total - 1.0) > 0.05:
            data["sektoren"] = {k: round(v / total, 4) for k, v in data["sektoren"].items()}
        # Sektornamen vereinheitlichen
        data["sektoren"] = _norm_dict(data["sektoren"])
        data["daten_stand"] = None
        return data
    except Exception:
        return None


# ── SwissFundData — Echte Daten für CH-Fonds ─────────────────────────────────

class _SFDSession:
    """Singleton-Session für SwissFundData (hält Disclaimer-Cookie am Leben)."""
    _session: requests.Session | None = None

    @classmethod
    def get(cls) -> requests.Session:
        if cls._session is None:
            s = requests.Session()
            s.headers.update(HEADERS)
            # Disclaimer einmalig akzeptieren
            s.get("https://www.swissfunddata.ch/sfdpub/sfd-eingang?url=%2Fde%2Ffunds", timeout=8)
            s.post(
                "https://www.swissfunddata.ch/sfdpub/sfd-eingang/qualified?url=%2Fde%2Ffunds",
                data={"_action_set": "einverstanden"},
                timeout=8, allow_redirects=True,
            )
            s.get("https://www.swissfunddata.ch/sfdpub/de/funds", timeout=8)
            cls._session = s
        return cls._session

    @classmethod
    def reset(cls):
        cls._session = None


def _sfd_lookup(isin: str) -> dict | None:
    """
    SwissFundData: sucht CH-Fonds per ISIN und extrahiert Sektordaten
    aus eingebetteten JavaScript Chart-Daten.
    Coverage: alle in der Schweiz zugelassenen Anlagefonds.
    """
    import re, json as _json
    try:
        s = _SFDSession.get()

        # 1. ISIN suchen → Fund ID
        r_search = s.post(
            "https://www.swissfunddata.ch/sfdpub/de/funds/overview",
            data={"text": isin},
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://www.swissfunddata.ch/sfdpub/de/funds"},
            timeout=10, allow_redirects=True,
        )
        if r_search.status_code != 200 or len(r_search.text) < 100:
            _SFDSession.reset()
            return None

        fund_id_m = re.search(r"/sfdpub/de/funds/show/(\d+)", r_search.text)
        if not fund_id_m:
            return None
        fund_id = fund_id_m.group(1)

        # Fondsnamen extrahieren
        name_m = re.search(
            r'/sfdpub/de/funds/show/' + fund_id + r'[^>]*>\s*([^<]{2,80}?)\s*</a>',
            r_search.text
        )
        fonds_name = name_m.group(1).strip() if name_m else ""

        # 2. Detailseite laden
        r_detail = s.get(
            f"https://www.swissfunddata.ch/sfdpub/de/funds/show/{fund_id}",
            timeout=15,
        )
        if r_detail.status_code != 200 or len(r_detail.text) < 1000:
            _SFDSession.reset()
            return None

        # 3. Chart-Daten extrahieren
        charts = re.findall(
            r"createBreakdownChart\('([^']+)',\s*(\[.*?\])\)",
            r_detail.text, re.DOTALL
        )
        if not charts:
            return None

        sektoren = {}
        regionen = {}

        for chart_id, data_raw in charts:
            pairs = re.findall(r"name:\s*'([^']+)',\s*value:\s*([\d.]+)", data_raw)
            if not pairs:
                continue
            total = sum(float(v) for _, v in pairs)
            if total <= 0:
                continue

            if chart_id == "funds-stockSectorBreakdowns":
                # Equity-Sektoren: Summe normalisieren
                for name_en, val in pairs:
                    name_de = _norm(name_en)
                    sektoren[name_de] = round(float(val) / total, 4)

            elif chart_id == "funds-countryBreakdowns":
                # Regionen
                for name_en, val in pairs:
                    regionen[name_en] = round(float(val) / total, 4)

            elif chart_id == "funds-bondSectorBreakdowns" and not sektoren:
                # Fallback: Anleihen-Sektoren wenn keine Equity-Sektoren
                for name_en, val in pairs:
                    name_de = _norm(name_en)
                    sektoren[name_de] = round(float(val) / total, 4)

        if not sektoren and not regionen:
            return None

        return {
            "fonds_name": fonds_name,
            "daten_stand": None,
            "sektoren": sektoren,
            "regionen": regionen if regionen else None,
        }

    except Exception:
        _SFDSession.reset()
        return None


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def smart_lookup(isin: str, bezeichnung: str) -> dict | None:
    """
    Findet automatisch Sektor-/Regionendaten für ein beliebiges Finanzinstrument.
    Ergebnis wird gecacht — jede ISIN wird nur einmal nachgeschlagen.
    """
    if not isin or not isin.strip():
        return None
    isin = isin.strip().upper()

    # 1. Cache prüfen
    cached = cache_get(isin)
    if cached:
        return cached

    def _return(data: dict, source: str) -> dict:
        data["source"] = source
        cache_put(isin, data, source=source)
        return data

    # 2. ISIN auflösen → Typ + Ticker (kein API-Key nötig)
    resolved = _resolve_isin(isin)
    instrument_type = resolved.get("type", "unknown") if resolved else "unknown"
    ticker = resolved.get("ticker", "") if resolved else ""
    exchange = resolved.get("exchange", "") if resolved else ""

    # 3a. CH-Fonds → SwissFundData (echte Daten, kein LLM, kein API-Key nötig)
    if isin.startswith("CH"):
        try:
            result = _sfd_lookup(isin)
            if result:
                return _return(result, "swissfunddata")
        except Exception:
            pass

    # 3b. Aktie → yfinance (kein API-Key nötig)
    if instrument_type == "stock" and ticker:
        try:
            result = _yfinance_sector(ticker, exchange)
            if result:
                return _return(result, "yfinance")
        except Exception:
            pass

    # 3c. ETF / Fonds → Claude Oracle (braucht API-Key)
    try:
        client = _get_client()
        if instrument_type in ("etf", "fund", "unknown"):
            result = _claude_oracle(isin, bezeichnung, instrument_type, client)
            if result:
                return _return(result, "oracle")

        # Fallback: Aktie ohne yfinance-Treffer → Oracle
        if instrument_type == "stock":
            result = _claude_oracle(isin, bezeichnung, "stock", client)
            if result:
                return _return(result, "oracle")
    except Exception:
        pass

    return None
