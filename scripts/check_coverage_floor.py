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
    return read_floor_record(floor_file_path)[0]


def read_floor_record(floor_file_path):
    """Read ``(floor, tool)`` from a floor file.

    The first non-empty line is the floor value. An optional ``tool: <spec>``
    line records the measurement tool the floor was calibrated against
    (e.g. ``tool: coverage==7.6.1``); absent means the original yardstick.
    """
    path = Path(floor_file_path)
    if not path.exists():
        return None, None
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if not lines:
        return None, None
    tool = None
    for line in lines[1:]:
        if line.startswith("tool:"):
            tool = line[len("tool:") :].strip()
    return float(lines[0]), tool


def check_ratchet(floor, base_floor, tool=None, base_tool=None):
    """Enforce the upward-only ratchet against the base branch's floor.

    Returns an error message when the PR deletes/empties the floor file or
    lowers its value relative to the base branch, else ``None``. ``base_floor
    is None`` (no committed floor on the base branch yet) skips the check.

    When the committed ``tool:`` marker differs between the branch and its
    base, the two floors were calibrated with different measurement tools and
    the numeric comparison is meaningless -- the ratchet is skipped for that
    one recalibration diff (the change is a reviewable line in the PR), while
    the floor itself keeps enforcing measured coverage on every run.
    """
    if base_floor is None:
        return None
    if floor is None:
        return (
            "floor file is missing or empty but the base branch commits "
            "{:.2f} -- floors only ratchet up; restore the file.".format(base_floor)
        )
    if tool != base_tool:
        return None
    if floor + EPSILON < base_floor:
        return (
            "floor lowered from {:.2f} (base branch) to {:.2f} -- floors only "
            "ratchet up; never lower a floor to make a build pass.".format(
                base_floor, floor
            )
        )
    return None


def format_ratchet_failure(lane, error):
    """Build the human-facing summary block for a ratchet violation."""
    return (
        "### Coverage floor: {lane}\n\n:x: **{lane}** ratchet violation: {error}\n"
    ).format(lane=lane, error=error)


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
    parser.add_argument(
        "--base-floor-file",
        help=(
            "path to a copy of the base branch's floor file (e.g. from "
            "`git show origin/main:coverage_floors/<lane>`); when present, "
            "a missing or lowered floor relative to it fails the run"
        ),
    )
    args = parser.parse_args(argv)

    measured = read_measured(args.coverage_json)
    floor, tool = read_floor_record(args.floor_file)

    if args.base_floor_file:
        base_floor, base_tool = read_floor_record(args.base_floor_file)
        ratchet_error = check_ratchet(floor, base_floor, tool, base_tool)
        if ratchet_error:
            write_summary(format_ratchet_failure(args.lane, ratchet_error))
            return 1

    result = evaluate(measured, floor)
    write_summary(format_summary(args.lane, measured, floor, result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
