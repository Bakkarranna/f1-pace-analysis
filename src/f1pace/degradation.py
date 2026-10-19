"""Tyre degradation: how lap time actually changes with tyre age.

The model is deliberately simple and interpretable, because in a strategy
interview the slope *is* the answer: "how many seconds per lap does this tyre
cost?" is answered by one coefficient with a confidence interval.

``lap_time = b0 + b_deg * tyre_age + b_fuel * fuel_effect + b_compound + ...``

Fuel effect matters more than people expect. A car gets lighter as the race
runs, so it gets faster, and that trend fights the tyre getting worse. Fitting
tyre age without fuel shows up as a *softer* (smaller) degradation slope, which
is exactly the kind of systematic error a strategy team cannot afford. The model
therefore includes a fuel term derived from the fuel load carried on each lap.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

#: Seconds gained per lap of fuel mass burned (typical F1 range: 0.03-0.05 s/lap).
DEFAULT_FUEL_GAIN_PER_LAP = 0.035


def fit_degradation(
    laps: pd.DataFrame,
    *,
    fuel_gain_per_lap: float = DEFAULT_FUEL_GAIN_PER_LAP,
) -> dict:
    """Fit the degradation model on one stint group.

    Returns a dict with the per-compound slope, standard error, 95% confidence
    interval, and the R-squared of the fit, plus the residual standard error.
    """
    if len(laps) < 4:
        return _empty_fit()

    frame = laps[["lap_duration", "tyre_age"]].copy()
    frame["fuel_laps_remaining"] = _fuel_laps_remaining(laps)
    if "compound" in laps.columns:
        frame["compound"] = laps["compound"].values
    if frame["lap_duration"].notna().sum() < 4 or frame["tyre_age"].nunique() < 2:
        return _empty_fit()

    formula = "lap_duration ~ tyre_age + fuel_laps_remaining"
    if "compound" in frame.columns and frame["compound"].nunique() > 1:
        formula += " + C(compound)"

    try:
        model = smf.ols(formula, data=frame).fit()
    except Exception:  # noqa: BLE001 - a failed fit must not abort a report
        return _empty_fit()

    slope = _coef(model, "tyre_age")
    fuel = _coef(model, "fuel_laps_remaining")
    return {
        "laps": int(len(frame)),
        "deg_s_per_lap": float(slope),
        "deg_stderr": float(model.bse.get("tyre_age", np.nan)),
        "deg_ci_low": float(model.conf_int().loc["tyre_age", 0]),
        "deg_ci_high": float(model.conf_int().loc["tyre_age", 1]),
        "deg_p_value": float(model.pvalues.get("tyre_age", np.nan)),
        "fuel_gain_s_per_lap": float(fuel),
        "r2": float(model.rsquared),
        "resid_s": float(np.sqrt(model.mse_resid)),
        "_model": model,
    }


def degradation_table(
    laps: pd.DataFrame,
    *,
    group_by: tuple[str, ...] = ("compound",),
    fuel_gain_per_lap: float = DEFAULT_FUEL_GAIN_PER_LAP,
) -> pd.DataFrame:
    """Fit the model separately per group and return a tidy summary table."""
    if laps.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for keys, group in laps.groupby(list(group_by), sort=True):
        fit = fit_degradation(group, fuel_gain_per_lap=fuel_gain_per_lap)
        if not np.isfinite(fit["deg_s_per_lap"]):
            continue
        fit.pop("_model", None)
        row = dict(zip(group_by, keys if isinstance(keys, tuple) else (keys,), strict=True))
        row.update(fit)
        rows.append(row)

    return pd.DataFrame(rows).sort_values("deg_s_per_lap").reset_index(drop=True)


def _fuel_laps_remaining(laps: pd.DataFrame) -> pd.Series:
    """Fuel laps remaining on each lap, derived from the field's lap span."""
    race_lap = laps["race_lap"]
    total = int(race_lap.max())
    remaining = (total - race_lap).clip(lower=0)
    return pd.Series(remaining, index=laps.index, name="fuel_laps_remaining")


def _coef(model, name: str) -> float:
    if name in model.params.index:
        return float(model.params[name])
    return float("nan")


def _empty_fit() -> dict:
    return {
        "laps": 0,
        "deg_s_per_lap": float("nan"),
        "deg_stderr": float("nan"),
        "deg_ci_low": float("nan"),
        "deg_ci_high": float("nan"),
        "deg_p_value": float("nan"),
        "fuel_gain_s_per_lap": float("nan"),
        "r2": float("nan"),
        "resid_s": float("nan"),
    }
