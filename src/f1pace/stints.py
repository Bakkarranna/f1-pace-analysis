"""Stint-level pace.

The question this module answers is the one a race engineer actually asks:
*whose stint fastest*, not whose single lap fastest. Lap time is normalised to a
common reference - the median lap of that driver's own stint - so stints of
different lengths and drivers of different baseline pace are directly comparable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_average(series: pd.Series, window: int = 3) -> pd.Series:
    """Trailing mean of lap time, which is what a stint summary looks like."""
    return series.rolling(window, min_periods=1).mean()


def best_stints(
    laps: pd.DataFrame,
    *,
    min_laps: int = 5,
    rolling_window: int = 3,
    top_n_per_race: int = 5,
) -> pd.DataFrame:
    """Find the strongest pace over a rolling 3-lap window, per driver and stint.

    Returns one row per qualifying stint with: best rolling lap time, best
    single lap, mean pace, number of clean laps, tyre age span, compound, and
    ``pace_vs_own_stint`` (best lap as a fraction of the stint median) so stints
    from different drivers can be ranked on one number.
    """
    if laps.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for (session_key, driver, stint), stint_laps in laps.groupby(
        ["session_key", "driver_number", "stint"], sort=True
    ):
        stint_laps = stint_laps.sort_values("lap_number")
        if len(stint_laps) < min_laps:
            continue

        median = stint_laps["lap_duration"].median()
        if not np.isfinite(median) or median <= 0:
            continue

        rolling = _rolling_average(stint_laps["lap_duration"], rolling_window)
        best_rolling = rolling.min()
        best_single = stint_laps["lap_duration"].min()

        rows.append(
            {
                "session_key": session_key,
                "driver_number": driver,
                "stint": stint,
                "compound": stint_laps["compound"].mode().iat[0],
                "laps": len(stint_laps),
                "lap_start": int(stint_laps["lap_number"].min()),
                "lap_end": int(stint_laps["lap_number"].max()),
                "tyre_age_min": int(stint_laps["tyre_age"].min()),
                "tyre_age_max": int(stint_laps["tyre_age"].max()),
                "median_lap": median,
                "best_lap": best_single,
                "best_rolling": best_rolling,
                "pace_vs_own_stint": best_rolling / median,
            }
        )

    if not rows:
        return pd.DataFrame()

    summary = pd.DataFrame(rows)
    summary["rank_in_race"] = summary.groupby("session_key")["best_rolling"].rank(method="min")
    return summary.sort_values(["session_key", "best_rolling"]).reset_index(drop=True)


def stint_summary(laps: pd.DataFrame) -> pd.DataFrame:
    """One row per (race, driver, stint) with aggregate pace and degradation.

    Degradation here is the slope of lap time against tyre age, fitted on the
    clean laps of that stint alone; it is the number that answers "how does lap
    time change as tyre age increases" for a single stint.
    """
    if laps.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for (session_key, driver, stint), stint_laps in laps.groupby(
        ["session_key", "driver_number", "stint"], sort=True
    ):
        stint_laps = stint_laps.sort_values("lap_number")
        if len(stint_laps) < 3:
            continue

        slope, intercept, r2 = _fit_slope(stint_laps["tyre_age"], stint_laps["lap_duration"])
        rows.append(
            {
                "session_key": session_key,
                "driver_number": driver,
                "stint": stint,
                "compound": stint_laps["compound"].mode().iat[0],
                "laps": len(stint_laps),
                "mean_lap": stint_laps["lap_duration"].mean(),
                "median_lap": stint_laps["lap_duration"].median(),
                "best_lap": stint_laps["lap_duration"].min(),
                "tyre_age_start": int(stint_laps["tyre_age"].min()),
                "tyre_age_end": int(stint_laps["tyre_age"].max()),
                "deg_s_per_lap": slope,
                "deg_r2": r2,
            }
        )
    return pd.DataFrame(rows)


def _fit_slope(x: pd.Series, y: pd.Series) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3 or np.allclose(x, x[0]):
        return float("nan"), float("nan"), float("nan")
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    ss_res = float(((y - predicted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(slope), float(intercept), r2
