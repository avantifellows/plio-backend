"""Tests for the per-lane coverage floor-check tool (scripts/check_coverage_floor.py).

This tool is the CI enforcement seam for #382: it reads a lane's measured
coverage (from ``coverage json``) and the lane's committed floor, prints a
"measured X% vs floor Y%" summary, nudges when the gap is large, and exits
non-zero when measured coverage drops below the floor. Expected pass/fail/nudge
outcomes below are stated from the spec, not recomputed from the tool's logic.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_coverage_floor.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_coverage_floor", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


floor_tool = _load_module()


def _write_coverage_json(path, percent):
    path.write_text(json.dumps({"totals": {"percent_covered": percent}}))


# --- pure decision logic -------------------------------------------------


def test_fails_when_measured_below_floor():
    result = floor_tool.evaluate(measured=90.0, floor=95.0)
    assert result.passed is False


def test_passes_when_measured_equals_floor():
    result = floor_tool.evaluate(measured=95.0, floor=95.0)
    assert result.passed is True


def test_passes_when_measured_above_floor():
    result = floor_tool.evaluate(measured=96.0, floor=95.0)
    assert result.passed is True


def test_nudges_when_gap_exceeds_two_percent():
    result = floor_tool.evaluate(measured=98.0, floor=95.0)
    assert result.passed is True
    assert result.nudge is True


def test_no_nudge_when_gap_within_two_percent():
    result = floor_tool.evaluate(measured=96.5, floor=95.0)
    assert result.nudge is False


def test_bootstrap_when_floor_unset():
    result = floor_tool.evaluate(measured=80.0, floor=None)
    assert result.bootstrap is True
    assert result.passed is True


# --- file reading --------------------------------------------------------


def test_read_measured_from_coverage_json(tmp_path):
    cov = tmp_path / "coverage.json"
    _write_coverage_json(cov, 84.25)
    assert floor_tool.read_measured(cov) == pytest.approx(84.25)


def test_read_floor_returns_none_when_file_missing(tmp_path):
    assert floor_tool.read_floor(tmp_path / "does-not-exist") is None


def test_read_floor_parses_committed_value(tmp_path):
    floor_file = tmp_path / "unit"
    floor_file.write_text("72.5\n")
    assert floor_tool.read_floor(floor_file) == pytest.approx(72.5)


# --- summary formatting --------------------------------------------------


def test_summary_reports_measured_and_floor():
    result = floor_tool.evaluate(measured=96.5, floor=95.5)
    summary = floor_tool.format_summary("unit", 96.5, 95.5, result)
    assert "measured 96.5% vs floor 95.5%" in summary
    assert "unit" in summary


# --- CLI enforcement seam (what CI actually invokes) ---------------------


def _run_cli(tmp_path, measured, floor_value, lane="unit"):
    cov = tmp_path / "coverage.json"
    _write_coverage_json(cov, measured)
    floor_file = tmp_path / lane
    if floor_value is not None:
        floor_file.write_text(str(floor_value))
    summary = tmp_path / "summary.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            lane,
            "--coverage-json",
            str(cov),
            "--floor-file",
            str(floor_file),
        ],
        capture_output=True,
        text=True,
        env={"GITHUB_STEP_SUMMARY": str(summary), "PATH": ""},
    )
    return proc, summary


def test_cli_exits_nonzero_when_below_floor(tmp_path):
    proc, summary = _run_cli(tmp_path, measured=90.0, floor_value=95.0)
    assert proc.returncode != 0
    assert "measured 90.0% vs floor 95.0%" in summary.read_text()


def test_cli_exits_zero_when_above_floor(tmp_path):
    proc, summary = _run_cli(tmp_path, measured=96.0, floor_value=95.0)
    assert proc.returncode == 0
    assert "measured 96.0% vs floor 95.0%" in summary.read_text()


def test_cli_bootstrap_passes_when_floor_missing(tmp_path):
    proc, _ = _run_cli(tmp_path, measured=80.0, floor_value=None)
    assert proc.returncode == 0


# --- upward-only ratchet against the base branch --------------------------


def test_ratchet_passes_when_floor_unchanged():
    assert floor_tool.check_ratchet(floor=95.0, base_floor=95.0) is None


def test_ratchet_passes_when_floor_raised():
    assert floor_tool.check_ratchet(floor=96.0, base_floor=95.0) is None


def test_ratchet_fails_when_floor_lowered():
    error = floor_tool.check_ratchet(floor=90.0, base_floor=95.0)
    assert error is not None
    assert "ratchet" in error or "lowered" in error


def test_ratchet_fails_when_floor_deleted():
    error = floor_tool.check_ratchet(floor=None, base_floor=95.0)
    assert error is not None
    assert "missing" in error


def test_ratchet_skipped_when_base_has_no_floor():
    assert floor_tool.check_ratchet(floor=95.0, base_floor=None) is None
    assert floor_tool.check_ratchet(floor=None, base_floor=None) is None


def _run_cli_with_base(tmp_path, measured, floor_value, base_floor_value):
    coverage_json = tmp_path / "coverage.json"
    _write_coverage_json(coverage_json, measured)
    floor_file = tmp_path / "floor"
    if floor_value is not None:
        floor_file.write_text(str(floor_value))
    base_floor_file = tmp_path / "base-floor"
    if base_floor_value is not None:
        base_floor_file.write_text(str(base_floor_value))
    else:
        # mirror CI: `git show ... > file || true` leaves an empty file when
        # the base branch has no floor for this lane
        base_floor_file.write_text("")
    summary = tmp_path / "summary.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "unit",
            "--coverage-json",
            str(coverage_json),
            "--floor-file",
            str(floor_file),
            "--base-floor-file",
            str(base_floor_file),
        ],
        capture_output=True,
        text=True,
        env={"GITHUB_STEP_SUMMARY": str(summary), "PATH": ""},
    )
    return proc, summary


def test_cli_fails_when_pr_lowers_the_floor(tmp_path):
    proc, summary = _run_cli_with_base(
        tmp_path, measured=96.0, floor_value=90.0, base_floor_value=95.0
    )
    assert proc.returncode != 0
    assert "ratchet violation" in summary.read_text()


def test_cli_fails_when_pr_deletes_the_floor(tmp_path):
    proc, summary = _run_cli_with_base(
        tmp_path, measured=96.0, floor_value=None, base_floor_value=95.0
    )
    assert proc.returncode != 0
    assert "ratchet violation" in summary.read_text()


def test_cli_passes_when_pr_raises_the_floor(tmp_path):
    proc, _ = _run_cli_with_base(
        tmp_path, measured=96.0, floor_value=95.5, base_floor_value=95.0
    )
    assert proc.returncode == 0


def test_cli_ratchet_skipped_when_base_floor_empty(tmp_path):
    proc, _ = _run_cli_with_base(
        tmp_path, measured=96.0, floor_value=95.0, base_floor_value=None
    )
    assert proc.returncode == 0


def test_read_floor_record_parses_tool_line(tmp_path):
    floor_file = tmp_path / "floor"
    floor_file.write_text("75.40\ntool: coverage==7.6.1\n")
    floor, tool = floor_tool.read_floor_record(floor_file)
    assert floor == 75.40
    assert tool == "coverage==7.6.1"


def test_read_floor_record_without_tool_line(tmp_path):
    floor_file = tmp_path / "floor"
    floor_file.write_text("95.0\n")
    assert floor_tool.read_floor_record(floor_file) == (95.0, None)


def test_ratchet_skipped_when_measurement_tool_changed():
    # a recalibration: the branch commits a new tool marker, so the numeric
    # comparison against the old-yardstick base floor is meaningless
    assert (
        floor_tool.check_ratchet(
            floor=75.4, base_floor=77.58, tool="coverage==7.6.1", base_tool=None
        )
        is None
    )


def test_ratchet_still_fails_when_tool_unchanged():
    error = floor_tool.check_ratchet(
        floor=75.4,
        base_floor=77.58,
        tool="coverage==7.6.1",
        base_tool="coverage==7.6.1",
    )
    assert error is not None
    assert "lowered" in error


def test_cli_recalibration_lowers_floor_with_new_tool(tmp_path):
    coverage_json = tmp_path / "coverage.json"
    _write_coverage_json(coverage_json, 76.0)
    floor_file = tmp_path / "floor"
    floor_file.write_text("75.40\ntool: coverage==7.6.1\n")
    base_floor_file = tmp_path / "base-floor"
    base_floor_file.write_text("77.58\n")
    summary = tmp_path / "summary.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "integration",
            "--coverage-json",
            str(coverage_json),
            "--floor-file",
            str(floor_file),
            "--base-floor-file",
            str(base_floor_file),
        ],
        capture_output=True,
        text=True,
        env={"GITHUB_STEP_SUMMARY": str(summary), "PATH": ""},
    )
    assert proc.returncode == 0
