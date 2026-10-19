"""Pit stops: how a driver's pace changes before and after a stop.

For every pit stop in a race this module compares the pace on the laps just
before the stop with the pace on the laps just after it. The comparison is done
on *normalised* lap time - each lap divided by the driver's median lap in that
race - so a fast car and a slow car can be pooled into one distribution.

The pit-lane time loss itself is not measured from lap times here (the in-lap and
out-lap are excluded, so the loss would be badly biased); the loss used for
strategy work comes from the pit-lane model in the Level 3 project. This module
answers the pace question only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Laps on each side of the stop that are compared.
WINDOW = 3


def pit_stop_effects(
    laps: pd.DataFrame,
    *,
    window: int = WINDOW,
) -> pd.DataFrame:
    """For each pit stop, compare normalised pace before and after the stop.

    Returns one row per stop with the mean normalised lap time on each side, the
    difference, the change in compound and the number of laps used on each side.
    """
    if laps.empty:
        return pd.DataFrame()

    events: list[dict] = []
    for session_key, session in laps.groupby("session_key", sort=True):
        for driver, driver_laps in session.groupby("driver_number", sort=True):
            events.extend(_driver_effects(session_key, driver, driver_laps, window))
    if not events:
        return pd.DataFrame()
    return pd.DataFrame(events)


def _driver_effects(
    session_key: int,
    driver: int,
    driver_laps: pd.DataFrame,
    window: int,
) -> list[dict]:
    laps = driver_laps.sort_values("lap_number")
    median = laps["lap_duration"].median()
    if not np.isfinite(median) or median <= 0:
        return []

    laps = laps.assign(normalised_lap=laps["lap_duration"] / median)
    out_laps = laps[laps["is_pit_out_lap"]].sort_values("lap_number")

    events = []
    for _, stop in out_laps.iterrows():
        stop_lap = int(stop["lap_number"])
        before = _side(laps, stop_lap - window, stop_lap - 1)
        after = _side(laps, stop_lap + 1, stop_lap + window)
        if before is None or after is None or len(before) < 2 or len(after) < 2:
            continue
        events.append(
            {
                "session_key": session_key,
                "driver_number": driver,
                "stop_lap": stop_lap,
                "compound_before": _mode_compound(before),
                "compound_after": _mode_compound(after),
                "normalised_before": float(before["normalised_lap"].mean()),
                "normalised_after": float(after["normalised_lap"].mean()),
                "delta": float(after["normalised_lap"].mean() - before["normalised_lap"].mean()),
                "laps_before": len(before),
                "laps_after": len(after),
                "stint_before": int(stop["stint"]) - 1,
                "stint_after": int(stop["stint"]),
            }
        )
    return events


def _side(laps: pd.DataFrame, start: int, end: int) -> pd.DataFrame | None:
    side = laps[(laps["lap_number"] >= start) & (laps["lap_number"] <= end)]
    side = side[~side["is_pit_out_lap"]]
    return side if not side.empty else None


def _mode_compound(laps: pd.DataFrame) -> str:
    if "compound" not in laps.columns:
        return "unknown"
    values = laps["compound"].dropna()
    return values.mode().iat[0] if not values.empty else "unknown"


def summarise_pit_stops(effects: pd.DataFrame) -> dict:
    """Pool every stop into one before/after statement for the report."""
    if effects.empty:
        return {"stops": 0}
    return {
        "stops": int(len(effects)),
        "mean_normalised_before": float(effects["normalised_before"].mean()),
        "mean_normalised_after": float(effects["normalised_after"].mean()),
        "mean_delta": float(effects["delta"].mean()),
        "median_delta": float(effects["delta"].median()),
        "faster_after_share": float((effects["delta"] < 0).mean()),
        "compound_changes": effects.assign(
            changed=effects["compound_before"] != effects["compound_after"]
        )["changed"].mean(),
    }
