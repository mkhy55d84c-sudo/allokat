"""
Lokaler JSON-Cache für Lookup-Resultate.

Speichert ISIN → Sektor/Regionendaten mit TTL.
Wächst automatisch — keine manuelle Pflege nötig.
"""

import json
import os
import time
from pathlib import Path

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "lookup_cache.json")
TTL_REAL = 30 * 24 * 3600       # 30 Tage für echte Daten (yfinance, APIs)
TTL_ORACLE = 90 * 24 * 3600     # 90 Tage für Claude-Oracle-Schätzungen


def _load() -> dict:
    path = Path(CACHE_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    path = Path(CACHE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def get(isin: str) -> dict | None:
    """Gibt gecachten Eintrag zurück, falls noch gültig."""
    cache = _load()
    entry = cache.get(isin.upper())
    if not entry:
        return None
    ttl = TTL_ORACLE if entry.get("source") == "oracle" else TTL_REAL
    if time.time() - entry.get("ts", 0) > ttl:
        return None  # abgelaufen
    return entry


def put(isin: str, data: dict, source: str) -> None:
    """Schreibt Ergebnis in den Cache."""
    cache = _load()
    cache[isin.upper()] = {**data, "source": source, "ts": time.time()}
    _save(cache)


def invalidate(isin: str) -> None:
    cache = _load()
    cache.pop(isin.upper(), None)
    _save(cache)
