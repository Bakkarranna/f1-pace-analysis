"""Command line interface.

Usage::

    f1pace report                 # write reports/RESULTS.md from data/processed
    f1pace stints --race monaco   # print the strongest stints for one race
    f1pace stats                  # how many laps each filter rule removed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd  # noqa: E402

from f1pace.filters import racing_laps  # noqa: E402
from f1pace.openf1 import PROCESSED_DIR, load_laps  # noqa: E402
from f1pace.report import build_report  # noqa: E402
from f1pace.stints import best_stints  # noqa: E402


def race_map(slugs: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Load every processed race as ``{slug: laps}``, optionally filtered."""
    data: dict[str, pd.DataFrame] = {}
    for path in sorted(PROCESSED_DIR.glob("*.csv")):
        if path.name == "pit_stops.csv" or path.name.startswith("flags_"):
            continue
        if not path.stem.isdigit():
            continue
        laps = load_laps(int(path.stem))
        if laps.empty or "race_slug" not in laps.columns:
            continue
        slug = str(laps["race_slug"].iloc[0])
        if slugs is None or slug in slugs:
            data[slug] = laps
    return data


def cmd_report(args) -> int:
    data = race_map(args.races)
    if not data:
        print("no data found - run `python scripts/fetch_openf1.py` first", file=sys.stderr)
        return 1
    text = build_report(data)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(text)} chars)")
    return 0


def cmd_stints(args) -> int:
    data = race_map(args.races)
    for race, laps in data.items():
        kept = racing_laps(laps)
        top = best_stints(kept).nsmallest(args.top, "best_rolling")
        print(f"\n=== {race} ({len(kept)} clean laps) ===")
        print(top.to_string(index=False))
    return 0


def cmd_stats(args) -> int:
    data = race_map(args.races)
    rows = []
    for race, laps in data.items():
        kept = racing_laps(laps)
        rows.append(
            {
                "race": race,
                "raw": len(laps),
                "clean": len(kept),
                "removed": len(laps) - len(kept),
                "kept_pct": round(100 * len(kept) / len(laps), 1),
                "drivers": int(kept["driver_number"].nunique()),
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="f1pace", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report", help="build the Markdown report")
    report.add_argument("--races", nargs="*", default=None)
    report.add_argument("--out", default=str(REPO_ROOT / "reports" / "RESULTS.md"))
    report.set_defaults(func=cmd_report)

    stints = sub.add_parser("stints", help="print the strongest stints")
    stints.add_argument("--races", nargs="*", default=None)
    stints.add_argument("--top", type=int, default=10)
    stints.set_defaults(func=cmd_stints)

    stats = sub.add_parser("stats", help="how many laps each filter rule removed")
    stats.add_argument("--races", nargs="*", default=None)
    stats.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
