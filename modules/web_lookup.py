"""
Automatischer ETF-Daten-Lookup via justETF.
Ablauf: justETF-Seite fetchen → Claude parst Sektor/Region-Tabellen.
Fallback: "nicht durchgerechnet"
"""

import os
import requests
import anthropic


def fetch_etf_data(isin: str) -> dict | None:
    """
    Holt Sektor- und Regionendaten für eine ISIN von justETF.
    Gibt dict mit sektoren/regionen zurück, oder None bei Fehler.
    """
    url = f"https://www.justetf.com/de/etf-profile.html?isin={isin}"

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    # Claude parst die HTML-Seite
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""Extrahiere aus diesem justETF HTML die Sektor- und Regionenaufteilung für ISIN {isin}.

Gib nur valides JSON zurück, kein Markdown:
{{
  "fonds_name": "Name des ETF",
  "daten_stand": "YYYY-MM",
  "sektoren": {{"Technologie": 0.232, "Finanzen": 0.163}},
  "regionen": {{"Nordamerika": 0.632, "Europa": 0.166}}
}}

Regeln:
- Anteile als Dezimalzahl (23.2% → 0.232)
- Sektornamen auf Deutsch normalisieren
- Wenn keine Sektordaten gefunden: sektoren = null
- Wenn keine Regionsdaten gefunden: regionen = null

HTML:
{html[:15000]}""",
                }
            ],
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        import json
        result = json.loads(raw)

        # Normalisiere falls Prozent statt Dezimal
        for key in ("sektoren", "regionen"):
            if result.get(key):
                total = sum(result[key].values())
                if total > 1.5:
                    result[key] = {k: round(v / 100, 4) for k, v in result[key].items()}

        return result

    except Exception:
        return None
