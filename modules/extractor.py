import base64
import json
import os
import anthropic

SYSTEM_PROMPT = """Du bist ein präziser Datenextraktor für Bankdepot-Auszüge.
Lies den Depotauszug und extrahiere alle Wertschriften- und Cash-Positionen.
Gib ausschliesslich valides JSON zurück — kein Markdown, keine Erklärungen, nur JSON."""

USER_PROMPT = """Extrahiere alle Positionen aus diesem Depotauszug.

Ausgabe-Schema (strikt einhalten):
{
  "bank": "Name der Bank",
  "depot_nummer": "Depotnummer oder null",
  "auszugsdatum": "YYYY-MM-DD oder null",
  "waehrung_basis": "CHF",
  "positionen": [
    {
      "isin": "12-stelliger ISIN-Code oder null",
      "bezeichnung": "Vollständige Bezeichnung",
      "typ": "Aktie|ETF|Fonds|Anleihe|Cash|Unbekannt",
      "menge": 100.0,
      "marktwert": 38500.00,
      "waehrung": "CHF",
      "einstandswert": 32000.00,
      "rendite_chf": 6500.00
    }
  ]
}

Regeln:
- typ: "ETF" wenn ETF/ETP im Name; "Fonds" wenn Fonds/Fund/SICAV; "Aktie" für Einzeltitel; "Anleihe" für Bond/Obligation; "Cash" für Kontokorrent/Girokonto/Liquidität
- marktwert: Aktueller Marktwert in der Positionswährung — niemals schätzen, nur lesen
- menge: Anzahl Stücke/Anteile; für Cash die Kontostand-Zahl; null wenn nicht lesbar
- einstandswert: Gesamter Einstandswert/Kaufwert der Position in Positionswährung — aus dem PDF lesen, null wenn nicht vorhanden
- rendite_chf: Unrealisierter Gewinn/Verlust in Positionswährung — positiv = Gewinn, negativ = Verlust; null wenn nicht vorhanden
- Rendite-% niemals selber berechnen — direkt aus dem PDF lesen
- Fehlende/unleserliche Felder → null, nicht raten
- Zahlenwerte immer als Zahl (nicht String), keine Tausendertrennzeichen
"""


def extract_depot(pdf_bytes: bytes) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY nicht gesetzt.")

    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
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
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if model wraps in ```json ... ```
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
