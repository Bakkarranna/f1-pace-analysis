"""Level 1: race pace, stint and tyre-age analysis on real F1 lap data."""

from .degradation import degradation_table, fit_degradation
from .filters import racing_laps
from .openf1 import load_laps
from .pitstops import pit_stop_effects
from .stints import best_stints, stint_summary

__all__ = [
    "best_stints",
    "degradation_table",
    "fit_degradation",
    "load_laps",
    "pit_stop_effects",
    "racing_laps",
    "stint_summary",
]

__version__ = "1.0.0"
