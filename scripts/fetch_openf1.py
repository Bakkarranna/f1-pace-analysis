"""Download race data from the OpenF1 API and write the processed tables.

Usage::

    python scripts/fetch_openf1.py                      # default race list
    python scripts/fetch_openf1.py --races 9523 9590
    python scripts/fetch_openf1.py --slugs monaco monza

The script writes one CSV per race into ``data/processed`` plus
``data/sessions.json`` (the race manifest) and ``data/processed/pit_stops.csv``.
Everything downstream runs offline against these files.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://api.openf1.org/v1"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROCESSED_DIR = DATA_DIR / "processed"

#: Races chosen for contrast in tyre-degradation behaviour. Monaco and
#: Singapore are slow, high-downforce circuits where tyres are the limiting
#: factor; Monza is the fastest lap of the season with very low degradation.
RACES: dict[str, dict] = {
    "bahrain": {"session_key": 9472, "location": "Sakhir", "country": "Bahrain"},
    "monaco": {"session_key": 9523, "location": "Monte Carlo", "country": "Monaco"},
    "monza": {"session_key": 9590, "location": "Monza", "country": "Italy"},
    "singapore": {"session_key": 9606, "location": "Marina Bay", "country": "Singapore"},
}
YEAR = 2024


def _get(endpoint: str, params: dict, retries: int = 5) -> list[dict]:
    """GET one endpoint, paced politely and retrying on rate limits."""
    url = f"{API}/{endpoint}"
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=120)
            if response.status_code == 429:
                time.sleep(5 * (attempt + 1))
            response.raise_for_status()
            time.sleep(0.5)  # OpenF1 rate limit: keep requests spaced out
            return response.json()
        except requests.RequestException as error:
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} after error: {error}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return []


def fetch_race(session_key: int, meta: dict) -> pd.DataFrame:
    print("  laps ... ", end="", flush=True)
    laps = pd.json_normalize(_get("laps", {"session_key": session_key}))
    stints = pd.json_normalize(_get("stints", {"session_key": session_key}))
    drivers = pd.json_normalize(_get("drivers", {"session_key": session_key}))
    pit = pd.json_normalize(_get("pit", {"session_key": session_key}))
    print(f"{len(laps)} laps, {len(stints)} stints, {len(pit)} stops")

    if laps.empty:
        raise RuntimeError(f"no laps returned for session {session_key}")

    laps = _merge_stints(laps, stints)
    laps = _merge_drivers(laps, drivers)
    laps["session_key"] = session_key
    laps["race_slug"] = meta["slug"]
    laps["circuit"] = meta["location"]

    pit = _prepare_pit(pit, session_key, meta)
    return laps, pit


def _merge_stints(laps: pd.DataFrame, stints: pd.DataFrame) -> pd.DataFrame:
    """Attach compound and tyre age by matching lap number inside a stint.

    Stint records can share a boundary lap (the lap where the stop happens
    belongs both to the end of one stint and the start of the next). Expanding
    the intervals to one row per lap and keeping the first claim resolves the
    overlap deterministically.
    """
    stints = stints.copy().rename(columns={"stint_number": "stint"})
    stints["lap_start"] = stints["lap_start"].astype(float)
    stints["lap_end"] = stints["lap_end"].astype(float)
    stints["tyre_age_at_start"] = stints["tyre_age_at_start"].fillna(0).astype(float)

    stints = stints[stints["lap_start"] <= stints["lap_end"]]
    laps_grid = [
        range(int(start), int(end) + 1) for start, end in zip(stints["lap_start"], stints["lap_end"], strict=True)
    ]
    expanded = stints.assign(lap=laps_grid).explode("lap")
    expanded["lap"] = expanded["lap"].astype(int)
    # A boundary lap is resolved in favour of the earlier stint: the lap a driver
    # completes before pitting is still run on the previous tyres, so the stop's
    # in-lap must not count against the new set of tyres.
    expanded = expanded.sort_values("lap_start").drop_duplicates(
        subset=["driver_number", "lap"], keep="first"
    )

    # Count tyre age from the first lap this stint actually owns rather than from
    # its nominal lap_start: a stint's reported starting absolute lap number is
    # unreliable across drivers whose stints were cut short by a safety car or a
    # retirement, which otherwise leaves the first laps of a new set of tyres
    # with a non-zero age.
    expanded = expanded.sort_values(["driver_number", "stint", "lap"])
    expanded["tyre_age"] = (
        expanded.groupby(["driver_number", "stint"]).cumcount()
        + expanded["tyre_age_at_start"]
    ).astype(float)
    lookup = expanded.set_index(["driver_number", "lap"])[
        ["stint", "compound", "tyre_age"]
    ]

    merged = laps.join(
        lookup, on=["driver_number", "lap_number"], how="left"
    )
    merged["stint"] = merged["stint"].astype("Int64")
    merged["tyre_age"] = merged["tyre_age"].astype("Float64")
    return merged


def _merge_drivers(laps: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
    columns = ["driver_number", "name_acronym", "full_name", "team_name"]
    lookup = drivers[[c for c in columns if c in drivers.columns]].drop_duplicates("driver_number")
    return laps.merge(lookup, on="driver_number", how="left")


def _prepare_pit(pit: pd.DataFrame, session_key: int, meta: dict) -> pd.DataFrame:
    if pit.empty:
        return pd.DataFrame(
            columns=[
                "session_key",
                "race_slug",
                "driver_number",
                "lap_number",
                "pit_duration",
                "lane_duration",
                "stop_duration",
            ]
        )
    pit = pit[
        ["session_key", "driver_number", "lap_number", "pit_duration", "lane_duration", "stop_duration"]
    ].copy()
    pit["race_slug"] = meta["slug"]
    return pit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slugs", nargs="*", default=list(RACES), choices=sorted(RACES))
    parser.add_argument("--year", type=int, default=YEAR)
    args = parser.parse_args(argv)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    pit_frames: list[pd.DataFrame] = []

    for slug in args.slugs:
        meta = {**RACES[slug], "slug": slug}
        print(f"{slug} (session {meta['session_key']})")
        laps, pit = fetch_race(meta["session_key"], meta)

        out = PROCESSED_DIR / f"{meta['session_key']}.csv"
        laps.to_csv(out, index=False)
        print(f"  -> {out.relative_to(DATA_DIR.parent)} ({len(laps)} rows)")

        pit_frames.append(pit)
        manifest.append(meta)

    if pit_frames:
        pits = pd.concat(pit_frames, ignore_index=True)
        pits.to_csv(PROCESSED_DIR / "pit_stops.csv", index=False)

    with (DATA_DIR / "sessions.json").open("w", encoding="utf-8") as handle:
        json.dump({"year": args.year, "races": manifest}, handle, indent=2)

    print(f"done: {len(manifest)} races downloaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
