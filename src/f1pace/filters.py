"""Lap filtering: decide which laps actually say something about race pace.

A raw lap table is full of laps that would corrupt a degradation estimate: the
formation lap, the standing start, in/out laps, laps under yellow or safety car,
and laps ruined by traffic or a driver error. :func:`racing_laps` strips them
with explicit, documented rules so the analysis is repeatable and defensible.
"""

from __future__ import annotations

import pandas as pd


def racing_laps(
    laps: pd.DataFrame,
    *,
    drop_first_lap: bool = True,
    outlier_band: float = 1.05,
) -> pd.DataFrame:
    """Return only the laps that are fair game for a pace comparison.

    Rules applied, in order:

    1. ``race_lap <= 0`` - the formation lap and any lap the timer did not count.
    2. ``is_pit_out_lap`` - the first lap after a stop: cold tyres, dirty air and
       a fresh set that is not yet up to temperature.
    3. In-laps - the lap immediately before a pit stop, where the driver is
       already saving the car and preparing the stop.
    4. Laps touched by a yellow, red or safety-car flag, from the race control
       feed (`under_yellow`).
    5. Lap 1 of the race, optionally: the standing start clumps the field behind
       the leader, so those laps are traffic-dominated rather than tyre-limited.
    6. Laps slower than ``outlier_band`` times that driver's own median lap,
       which catches slow laps from any cause the flag feed does not record.
    """
    if laps.empty:
        return laps.copy()

    kept = laps.copy()
    required = ["race_lap", "is_pit_out_lap", "lap_duration", "lap_number"]
    if not set(required).issubset(kept.columns):
        raise ValueError(f"lap table is missing columns: {set(required) - set(kept.columns)}")

    kept["race_lap"] = kept["race_lap"].astype(int)
    kept["is_pit_out_lap"] = kept["is_pit_out_lap"].fillna(False).astype(bool)

    kept = kept[kept["race_lap"] > 0]
    kept = kept[~kept["is_pit_out_lap"]]
    kept = kept[~_in_lap_mask(kept)]

    if "under_yellow" in kept.columns:
        kept = kept[~kept["under_yellow"].fillna(False).astype(bool)]
    if drop_first_lap:
        kept = kept[kept["race_lap"] > 1]

    # Tyre age is only known for laps the stints feed covers; a lap without it
    # cannot contribute to a degradation fit.
    if "tyre_age" in kept.columns:
        kept = kept[kept["tyre_age"].notna()]

    kept = kept[kept["lap_duration"].notna() & (kept["lap_duration"] > 0)]
    kept = _drop_slow_laps(kept, band=outlier_band)

    return kept.sort_values(["session_key", "driver_number", "lap_number"]).reset_index(drop=True)


def _in_lap_mask(laps: pd.DataFrame) -> pd.Series:
    """Flag the lap immediately before each pit-out lap, per driver."""
    mask = pd.Series(False, index=laps.index)
    ordered = laps.sort_values(["driver_number", "lap_number"])
    next_is_out = ordered["is_pit_out_lap"].shift(-1, fill_value=False)
    same_driver = ordered["driver_number"] == ordered["driver_number"].shift(-1)
    contiguous = ordered["lap_number"] + 1 == ordered["lap_number"].shift(-1)
    mask.loc[ordered.index[next_is_out & same_driver & contiguous]] = True
    return mask


def _drop_slow_laps(laps: pd.DataFrame, *, band: float) -> pd.DataFrame:
    """Remove laps much slower than the driver's own median.

    Tyre degradation is a few percent of lap time, so a 5% band removes
    incident, traffic and slow-out laps without touching the signal.
    """
    if laps.empty:
        return laps
    medians = laps.groupby("driver_number")["lap_duration"].transform("median")
    return laps[laps["lap_duration"] <= medians * band]


def summary(laps: pd.DataFrame, cleaned: pd.DataFrame) -> dict:
    """Count how many laps each removal rule actually dropped.

    The rules are replayed one at a time in the same order as
    :func:`racing_laps`, so the counts are attributable rather than a single
    unexplained ``raw - clean`` number.
    """
    if laps.empty:
        return {"raw": 0, "clean": 0, "pct": 0.0, "dropped": {}}

    remaining = laps.copy()
    dropped: dict[str, int] = {}

    def _drop(mask: pd.Series, label: str) -> None:
        """Record how many rows this rule removed, then remove them."""
        nonlocal remaining
        aligned = mask.reindex(remaining.index, fill_value=False)
        removed = int(aligned.sum())
        if removed:
            dropped[label] = dropped.get(label, 0) + removed
        remaining = remaining[~aligned]

    work = remaining
    work["race_lap"] = work["race_lap"].astype(int)
    work["is_pit_out_lap"] = work["is_pit_out_lap"].fillna(False).astype(bool)

    _drop(work["race_lap"] <= 0, "formation / uncounted lap")
    _drop(work["is_pit_out_lap"], "pit out lap")
    _drop(_in_lap_mask(work), "in lap")
    if "under_yellow" in work.columns:
        _drop(work["under_yellow"].fillna(False).astype(bool), "under yellow / safety car")
    _drop(work["race_lap"] <= 1, "race lap 1")
    if "tyre_age" in work.columns:
        _drop(work["tyre_age"].isna(), "missing tyre age")
    _drop(work["lap_duration"].isna() | (work["lap_duration"] <= 0), "no lap time")
    medians = work.groupby("driver_number")["lap_duration"].transform("median")
    _drop(work["lap_duration"] > medians * 1.05, "slower than 105% of own median")

    return {
        "raw": int(len(laps)),
        "clean": int(len(cleaned)),
        "pct": round(100 * len(cleaned) / len(laps), 1),
        "dropped": dropped,
    }
