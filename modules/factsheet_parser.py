"""
Parst Factsheet-PDFs via Claude API.
Extrahiert Sektor- und Regionenverteilung aus Fonds-Factsheets.
Gibt bei Unsicherheit explizit None zurück — niemals raten.
"""

import base64
import json
import os
import anthropic

FACTSHEET_SYSTEM = """Du bist ein Datenextraktor für Fonds-Factsheets.
Gib ausschliesslich valides JSON zurück — kein Markdown, keine Erklärungen."""

FACTSHEET_PROMPT = """Extrahiere die Sektor- und Regionenaufteilung aus diesem Fonds-Factsheet.

Ausgabe-Schema:
{
  "fonds_name": "Vollständiger Fondsname",
  "daten_stand": "YYYY-MM (Datum der Holdings)",
  "sektoren": {
    "Technologie": 0.232,
    "Finanzen": 0.163
  },
  "regionen": {
    "Nordamerika": 0.632,
    "Europa": 0.166
  },
  "konfidenz": "hoch|mittel|niedrig"
}

Regeln:
- Anteile als Dezimalzahl (0.232 = 23.2%), nicht als Prozent
- Sektoren und Regionen summieren sich auf ~1.0 (±2%)
- Wenn keine Sektortabelle erkennbar: sektoren = null
- Wenn keine Regionentabelle erkennbar: regionen = null
- Sektornamen normalisieren auf: Technologie, Finanzen, Gesundheit, Zyklischer Konsum,
  Basiskonsumgüter, Industrie, Kommunikation, Energie, Rohstoffe, Versorger, Immobilien
- konfidenz: "hoch" wenn Tabellen klar lesbar; "mittel" wenn teilweise; "niedrig" wenn geschätzt
"""


def parse_factsheet(pdf_bytes: bytes) -> dict | None:
    """
    Parst ein Factsheet-PDF.
    Gibt dict mit sektoren/regionen zurück, oder None bei Fehler.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY nicht gesetzt.")

    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=FACTSHEET_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {"type": "text", "text": FACTSHEET_PROMPT},
                    ],
                }
            ],
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

        # Normalize percentages if model returned 23.2 instead of 0.232
        for key in ("sektoren", "regionen"):
            if result.get(key):
                total = sum(result[key].values())
                if total > 1.5:
                    result[key] = {k: v / 100 for k, v in result[key].items()}

        return result

    except Exception:
        return None
