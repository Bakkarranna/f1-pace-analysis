"""Report assembly: turn the analysis tables into a readable Markdown report."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from .degradation import degradation_table
from .filters import racing_laps
from .pitstops import pit_stop_effects, summarise_pit_stops
from .stints import best_stints

COMPOUND_LABELS = {"SOFT": "Soft", "MEDIUM": "Medium", "HARD": "Hard"}


def build_report(laps_by_race: dict[str, pd.DataFrame], *, top_n: int = 5) -> str:
    """Build the full Markdown report for a set of races."""
    clean = {}
    for race, laps in laps_by_race.items():
        kept = racing_laps(laps)
        if kept is not None and not kept.empty:
            clean[race] = kept

    parts = [_header(len(clean), sum(len(v) for v in clean.values()))]
    for race, laps in clean.items():
        parts.append(_race_section(race, laps, top_n=top_n))
    parts.append(_cross_race_section(clean))
    return "\n\n".join(p for p in parts if p)


def _header(race_count: int, lap_count: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "# Race pace, stint and tyre-age analysis\n\n"
        f"Formula 1, {race_count} Grands Prix, {lap_count} clean racing laps. "
        f"Generated {stamp}.\n\n"
        "This report answers three questions with the measured lap data:\n\n"
        "1. **Which driver had the strongest pace over a stint?**\n"
        "2. **How does lap time change as tyre age increases?**\n"
        "3. **How does pace change before and after a pit stop?**\n"
    )


def _race_section(race: str, laps: pd.DataFrame, *, top_n: int) -> str:
    stints = best_stints(laps)
    lines = [f"## {race.title()}", ""]
    if stints.empty:
        return "\n".join(lines + ["_No stint long enough to analyse._"])

    top = stints.nsmallest(top_n, "best_rolling")
    lines.append(
        f"**{len(laps)} clean laps, {laps['driver_number'].nunique()} drivers, "
        f"{int(stints['stint'].nunique())} stints analysed.**\n"
    )
    lines.append("### Strongest pace over a stint\n")
    lines.append(
        "| Driver | Tyre | Clean laps | Median lap (s) | Best 3-lap mean (s) | vs own stint |"
    )
    lines.append("|---|---|---|---|---|---|")
    for _, row in top.iterrows():
        lines.append(
            f"| {_driver(row)} | {row['compound']} | {int(row['laps'])} | "
            f"{row['median_lap']:.3f} | {row['best_rolling']:.3f} | "
            f"{100 * row['pace_vs_own_stint']:.2f}% |"
        )
    lines.append(
        "\n*Best 3-lap mean* is the trailing 3-lap rolling average, which is how a "
        "stint is judged on the pit wall: one fast lap can be a tow or a fuel "
        "effect, three in a row is pace. *vs own stint* expresses that as a "
        "percentage of the driver's own stint median, so stints from different "
        "cars are comparable.\n"
    )

    deg = degradation_table(laps, group_by=("compound",))
    if not deg.empty:
        lines.append("### Tyre degradation\n")
        lines.append("| Compound | Laps | s per lap of tyre age | 95% CI | R-squared |")
        lines.append("|---|---|---|---|---|")
        for _, row in deg.iterrows():
            lines.append(
                f"| {COMPOUND_LABELS.get(row['compound'], row['compound'])} | "
                f"{int(row['laps'])} | {row['deg_s_per_lap']:.4f} | "
                f"{row['deg_ci_low']:.4f} to {row['deg_ci_high']:.4f} | {row['r2']:.3f} |"
            )
        lines.append(
            "\nThe fuel term is fitted alongside tyre age: a car gets lighter "
            "through the race and therefore faster, which would otherwise mask "
            "some of the tyre degradation.\n"
        )

    effects = pit_stop_effects(laps)
    summary = summarise_pit_stops(effects)
    if not effects.empty:
        lines.append("### Pit stops: pace before vs after\n")
        lines.append(
            f"{summary['stops']} stops analysed. Mean normalised lap time before "
            f"the stop {summary['mean_normalised_before']:.4f}, after "
            f"{summary['mean_normalised_after']:.4f} "
            f"(mean change {summary['mean_delta']:+.4f}, "
            f"{summary['faster_after_share'] * 100:.0f}% of stops were faster).\n"
        )
    return "\n".join(lines)


def _cross_race_section(clean: dict[str, pd.DataFrame]) -> str:
    if len(clean) < 2:
        return ""
    frames = []
    for race, laps in clean.items():
        table = degradation_table(laps, group_by=("compound",))
        if table.empty:
            continue
        table.insert(0, "race", race)
        frames.append(table)
    if not frames:
        return ""
    combined = pd.concat(frames, ignore_index=True)
    lines = ["## Degradation across races", ""]
    lines.append("| Race | Compound | Laps | s per lap of tyre age | 95% CI |")
    lines.append("|---|---|---|---|---|")
    for _, row in combined.iterrows():
        lines.append(
            f"| {row['race']} | {COMPOUND_LABELS.get(row['compound'], row['compound'])} | "
            f"{int(row['laps'])} | {row['deg_s_per_lap']:.4f} | "
            f"{row['deg_ci_low']:.4f} to {row['deg_ci_high']:.4f} |"
        )
    return "\n".join(lines)


def _driver(row) -> str:
    acronym = row.get("name_acronym")
    return str(acronym) if pd.notna(acronym) else str(int(row["driver_number"]))
