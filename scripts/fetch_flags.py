"""Download rate-limit-safe flag events (race control) from the OpenF1 API.

Usage::

    python scripts/fetch_flags.py

Writes ``data/processed/flags_<session_key>.csv`` for every race in the manifest.
Nothing here is needed to run the analysis offline.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://api.openf1.org/v1"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MIN_DELAY = 0.6

COLUMNS = ["session_key", "lap_number", "category", "flag", "scope", "message", "date"]


def _get(endpoint: str, params: dict, retries: int = 5) -> list[dict]:
    url = f"{API}/{endpoint}"
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=120)
            if response.status_code == 429:
                time.sleep(5 * (attempt + 1))
            response.raise_for_status()
            time.sleep(MIN_DELAY)
            return response.json()
        except requests.RequestException as error:
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} after error: {error}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return []


def main() -> int:
    manifest = pd.read_json(DATA_DIR / "sessions.json")["races"].tolist()
    for race in manifest:
        key = race["session_key"]
        rows = pd.json_normalize(_get("race_control", {"session_key": key}))
        rows = rows[[c for c in COLUMNS if c in rows.columns]]
        out = PROCESSED_DIR / f"flags_{key}.csv"
        rows.to_csv(out, index=False)
        print(f"{race['race_slug'] if 'race_slug' in race else key}: {len(rows)} events -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
