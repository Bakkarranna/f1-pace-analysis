"""Offline access to the downloaded OpenF1 tables.

The fetch scripts in ``scripts/`` write one CSV per race into ``data/processed``.
Everything in the analysis layer reads those CSVs through this module, so the
analysis never needs the network and the data contract is checked in one place.

Two derived columns are added at load time, because the OpenF1 feeds do not
provide them in a form the analysis can use directly:

``race_lap``
    The lap number of the race, which is what the racing-lap filters and the
    fuel term need. OpenF1 counts laps from 1 in a race, so the two are equal
    here; the column exists because it makes the filter rules explicit and
    survives a future switch to a feed that counts differently.

``green_flag``
    False while a yellow, red or double-yellow was being shown. The race control
    feed only records the *start* of each incident and a ``CLEAR`` when it ends,
    so the laps between the two are marked as affected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROCESSED_DIR = DATA_DIR / "processed"

#: Flag states that mean the racing was not green. ``CLEAR`` ends an incident
#: rather than starting one, so it is deliberately absent here.
CAUTION_FLAGS = frozenset({"YELLOW", "DOUBLE YELLOW", "RED", "SAFETY CAR"})

#: Columns the analysis layer relies on; :func:`load_laps` guarantees them.
REQUIRED_COLUMNS = [
    "session_key",
    "driver_number",
    "lap_number",
    "lap_duration",
    "stint",
    "compound",
    "tyre_age",
    "is_pit_out_lap",
    "green_flag",
    "name_acronym",
]


def load_sessions() -> dict:
    """Read the race manifest written by ``scripts/fetch_openf1.py``."""
    path = DATA_DIR / "sessions.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def lap_path(session_key: int) -> Path:
    """Path of the processed lap table for one session."""
    return PROCESSED_DIR / f"{session_key}.csv"


def flag_path(session_key: int) -> Path:
    """Path of the race-control table for one session, if it was downloaded."""
    return PROCESSED_DIR / f"flags_{session_key}.csv"


def load_laps(session_key: int) -> pd.DataFrame:
    """Return the lap table for one session with derived columns attached.

    Rows are returned even when the lap time is missing: a folded/out lap is a
    real event and the filters decide what to do with it.
    """
    path = lap_path(session_key)
    if not path.exists():
        raise FileNotFoundError(f"no lap table for session {session_key}: run scripts/fetch_openf1.py first")

    laps = pd.read_csv(path)
    if laps.empty:
        return _empty_laps()

    laps["session_key"] = laps["session_key"].astype(int)
    laps["driver_number"] = laps["driver_number"].astype(int)
    laps["lap_number"] = laps["lap_number"].astype(int)
    laps["race_lap"] = laps["lap_number"]
    laps["lap_duration"] = pd.to_numeric(laps["lap_duration"], errors="coerce")
    laps["is_pit_out_lap"] = laps["is_pit_out_lap"].fillna(False).astype(bool)
    laps["stint"] = laps["stint"].astype("Int64")
    laps["tyre_age"] = pd.to_numeric(laps["tyre_age"], errors="coerce").astype("Float64")

    laps["green_flag"] = _green_flags(laps, session_key)
    missing = [column for column in REQUIRED_COLUMNS if column not in laps.columns]
    if missing:
        raise ValueError(f"{path.name} is missing columns: {missing}")
    return laps.sort_values(["driver_number", "lap_number"]).reset_index(drop=True)


def _empty_laps() -> pd.DataFrame:
    frame = pd.DataFrame(columns=REQUIRED_COLUMNS)
    frame["race_lap"] = pd.Series(dtype="int64")
    return frame


def _green_flags(laps: pd.DataFrame, session_key: int) -> pd.Series:
    """Mark laps that ran under a yellow, red or safety car."""
    green = pd.Series(True, index=laps.index, name="green_flag")
    for start, end in _caution_laps(session_key):
        affected = (laps["lap_number"] >= start) & (laps["lap_number"] <= end)
        green[affected] = False
    return green


def _caution_laps(session_key: int) -> list[tuple[int, int]]:
    """Infer the laps covered by each caution from the race-control feed.

    The feed records the lap a caution began on and the ``CLEAR`` that ended it,
    but never an explicit end lap, so each interval is reconstructed by pairing a
    caution with the next clear. A caution still open at the end of the feed is
    treated as running to the last lap of the session.
    """
    path = flag_path(session_key)
    if not path.exists():
        return []

    events = pd.read_csv(path)
    if events.empty:
        return []

    order = ["lap_number", "date"]
    events = events.sort_values([column for column in order if column in events.columns])
    events = events[events["lap_number"].notna()]
    events["lap_number"] = events["lap_number"].astype(int)

    intervals: list[tuple[int, int]] = []
    open_lap: int | None = None
    for _, event in events.iterrows():
        flag = event.get("flag")
        flag = flag if isinstance(flag, str) else ""
        lap = int(event["lap_number"])
        if flag in CAUTION_FLAGS:
            if open_lap is None:
                open_lap = lap
        elif flag == "CLEAR" and open_lap is not None:
            intervals.append((open_lap, lap))
            open_lap = None

    if open_lap is not None:
        intervals.append((open_lap, int(events["lap_number"].max())))
    return intervals


def load_race_by_slug(slug: str) -> pd.DataFrame | None:
    """Load one race by its manifest slug, or ``None`` if it is not present."""
    for race in load_sessions().get("races", []):
        if race.get("race_slug", race.get("slug")) == slug:
            return load_laps(int(race["session_key"]))
    return None


def load_all_races() -> dict[str, pd.DataFrame]:
    """Load every race in the manifest as ``{slug: laps}``."""
    races: dict[str, pd.DataFrame] = {}
    for race in load_sessions().get("races", []):
        slug = race.get("race_slug", race.get("slug"))
        laps = load_laps(int(race["session_key"]))
        if not laps.empty:
            races[str(slug)] = laps
    return races


def load_pit_stops() -> pd.DataFrame:
    """Load the pit-stop table, or an empty frame if it is absent."""
    path = PROCESSED_DIR / "pit_stops.csv"
    if not path.exists():
        return pd.DataFrame(
            columns=["session_key", "driver_number", "lap_number", "pit_duration", "lane_duration", "stop_duration"]
        )
    pits = pd.read_csv(path)
    if pits.empty:
        return pits
    pits["session_key"] = pits["session_key"].astype(int)
    pits["driver_number"] = pits["driver_number"].astype(int)
    pits["lap_number"] = pits["lap_number"].astype(int)
    return pits
