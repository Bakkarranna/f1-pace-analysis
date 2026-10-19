"""Synthetic fixture tables used by the unit tests.

The tests deliberately do not read the downloaded CSVs: every module is checked
against hand-built tables where the true answer is known exactly.
"""

from __future__ import annotations

import pandas as pd
import pytest


def make_laps(laps=(), *, session_key: int = 99) -> pd.DataFrame:
    """Build a lap table from (driver, lap, stint, lap_time, compound, pit_out)."""
    rows = []
    for driver, lap, stint, lap_time, compound, pit_out in laps:
        rows.append(
            {
                "session_key": session_key,
                "driver_number": driver,
                "lap_number": lap,
                "race_lap": lap,
                "lap_duration": lap_time,
                "stint": stint,
                "compound": compound,
                "is_pit_out_lap": pit_out,
                "green_flag": True,
                "name_acronym": f"D{driver}",
            }
        )
    frame = pd.DataFrame(rows)
    ages = []
    for _, group in frame.groupby(["driver_number", "stint"], sort=False):
        ages.extend(range(len(group)))
    frame["tyre_age"] = ages
    return frame


@pytest.fixture
def laps_table():
    """Two drivers, one stop each, a known degradation slope of 0.1 s/lap."""
    rows = []
    for driver in (1, 2):
        base = 90.0 + driver
        for stint in (1, 2):
            for lap in range(1, 13):
                lap_number = lap if stint == 1 else lap + 20
                pit_out = stint == 2 and lap == 1
                lap_time = base + 0.1 * (lap - 1)
                rows.append((driver, lap_number, stint, lap_time, "MEDIUM", pit_out))
    return make_laps(rows)
