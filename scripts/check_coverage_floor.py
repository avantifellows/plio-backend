#!/usr/bin/env python
"""Enforce a committed per-lane coverage floor in CI.

Reads a lane's measured coverage from a ``coverage json`` report and the lane's
committed floor, prints a ``measured X% vs floor Y%`` line to the GitHub job
summary (and stdout), nudges when the measured value has pulled well ahead of
the floor, and exits non-zero when measured coverage has dropped below the
floor. Enforcement lives here in CI, not in Codecov (see #382 / PRD #374).

Floors are committed per lane and initialized at that lane's first measured
value minus one percent; they only ratchet upward. A missing/empty floor file
is treated as "not yet initialized" (bootstrap): the run reports the measured
value and passes so the floor can be seeded from it.

Usage:
    python scripts/check_coverage_floor.py \\
        --lane unit \\
        --coverage-json coverage.json \\
        --floor-file coverage_floors/unit
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Nudge when measured coverage exceeds the floor by more than this many points
# -- the signal to bump the committed floor in the PR that added the tests.
NUDGE_GAP = 2.0

# Absorb floating-point noise so an exactly-at-floor run counts as passing.
EPSILON = 1e-9


@dataclass
class Result:
    passed: bool
    nudge: bool
    bootstrap: bool
    gap: float


def evaluate(measured, floor, nudge_gap=NUDGE_GAP):
    """Decide pass/fail/nudge for a measured value against a floor.

    ``floor is None`` means the floor has not been initialized yet (bootstrap):
    the run passes and no comparison is made.
    """
    if floor is None:
        return Result(passed=True, nudge=False, bootstrap=True, gap=0.0)
    gap = measured - floor
    passed = measured + EPSILON >= floor
    nudge = passed and gap > nudge_gap
    return Result(passed=passed, nudge=nudge, bootstrap=False, gap=gap)


def read_measured(coverage_json_path):
    """Read total percent covered from a ``coverage json`` report."""
    data = json.loads(Path(coverage_json_path).read_text())
    return float(data["totals"]["percent_covered"])


def read_floor(floor_file_path):
    """Read the committed floor, or ``None`` if it is missing/empty (bootstrap)."""
    path = Path(floor_file_path)
    if not path.exists():
        return None
    raw = path.read_text().strip()
    if not raw:
        return None
    return float(raw)


def format_summary(lane, measured, floor, result):
    """Build the human-facing summary block for a lane."""
    if result.bootstrap:
        seed = measured - 1
        return (
            "### Coverage floor: {lane}\n\n"
            "measured {measured:.1f}% vs floor (uninitialized)\n\n"
            "Floor not yet initialized -- seed it at {seed:.1f}% "
            "(first measured {measured:.1f}% minus 1%) in this PR.\n"
        ).format(lane=lane, measured=measured, seed=seed)

    lines = [
        "### Coverage floor: {}".format(lane),
        "",
        "measured {:.1f}% vs floor {:.1f}%".format(measured, floor),
        "",
    ]
    if not result.passed:
        lines.append(
            ":x: **{lane}** coverage {measured:.1f}% is below the committed "
            "floor {floor:.1f}% -- add tests or justify the drop.".format(
                lane=lane, measured=measured, floor=floor
            )
        )
    elif result.nudge:
        lines.append(
            ":arrow_up: **{lane}** coverage exceeds the floor by {gap:.1f}% "
            "-- bump the floor in this PR to lock the gain in.".format(
                lane=lane, gap=result.gap
            )
        )
    else:
        lines.append(":white_check_mark: **{}** coverage meets the floor.".format(lane))
    return "\n".join(lines) + "\n"


def write_summary(text):
    """Append the summary to the GitHub job summary if available, else stdout."""
    print(text)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as handle:
            handle.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Enforce a per-lane coverage floor.")
    parser.add_argument(
        "--lane", required=True, help="lane name, e.g. unit or integration"
    )
    parser.add_argument(
        "--coverage-json", required=True, help="path to a `coverage json` report"
    )
    parser.add_argument(
        "--floor-file",
        required=True,
        help="path to the committed floor file for this lane",
    )
    args = parser.parse_args(argv)

    measured = read_measured(args.coverage_json)
    floor = read_floor(args.floor_file)
    result = evaluate(measured, floor)
    write_summary(format_summary(args.lane, measured, floor, result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
