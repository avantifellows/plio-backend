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
