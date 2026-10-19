"""Regenerate the Markdown report from the downloaded data.

Usage::

    python scripts/build_report.py                 # all races -> reports/RESULTS.md
    python scripts/build_report.py --out out.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1pace.cli import main  # noqa: E402


def _run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "reports" / "RESULTS.md"))
    args, _ = parser.parse_known_args()
    return main(["report", "--out", args.out])


if __name__ == "__main__":
    raise SystemExit(_run())
