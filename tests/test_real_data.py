"""Sanity checks on the downloaded data itself.

These run against the CSVs in ``data/processed`` and would fail if the fetch
script silently produced a broken table, so they act as a data contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from f1pace.openf1 import PROCESSED_DIR, load_laps, load_sessions  # noqa: E402

REQUIRED_COLUMNS = {
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
}


@pytest.mark.skipif(not PROCESSED_DIR.exists(), reason="run scripts/fetch_openf1.py first")
def test_every_session_in_the_manifest_has_a_csv():
    sessions = load_sessions()
    assert sessions["races"], "the manifest must list at least one race"
    for race in sessions["races"]:
        assert (PROCESSED_DIR / f"{race['session_key']}.csv").exists()


@pytest.mark.skipif(not PROCESSED_DIR.exists(), reason="run scripts/fetch_openf1.py first")
def test_downloaded_laps_are_usable():
    for race in load_sessions()["races"]:
        laps = load_laps(race["session_key"])
        assert REQUIRED_COLUMNS.issubset(laps.columns), REQUIRED_COLUMNS - set(laps.columns)
        assert not laps.duplicated(subset=["driver_number", "lap_number"]).any()
        assert laps["driver_number"].nunique() >= 15
        assert (laps["lap_duration"] > 0).mean() > 0.5
        assert set(laps["compound"].dropna()) <= {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
        assert laps["tyre_age"].dropna().ge(0).all()


@pytest.mark.skipif(not PROCESSED_DIR.exists(), reason="run scripts/fetch_openf1.py first")
def test_tyre_age_restarts_at_each_stop():
    for race in load_sessions()["races"]:
        laps = load_laps(race["session_key"])
        for _, stint in laps.groupby(["driver_number", "stint"]):
            first_stint_lap = stint.loc[stint["lap_number"].idxmin()]
            if int(first_stint_lap["stint"]) > 1:
                assert first_stint_lap["tyre_age"] in (0, 1)
