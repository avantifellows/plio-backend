"""Regression tests for environment-driven Django settings.

The settings module is imported in a fresh interpreter for every case so the
test exercises the same environment parsing path used by the application.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "raw_value, expected",
    [
        (None, False),
        ("", False),
        ("False", False),
        (" fAlSe ", False),
        ("0", False),
        (" 0 ", False),
        ("True", True),
        (" tRuE ", True),
        ("1", True),
        (" 1 ", True),
        ("yes", False),
        ("on", False),
        ("2", False),
        ("unexpected", False),
    ],
)
def test_debug_setting_parses_environment_value(raw_value, expected):
    environment = os.environ.copy()
    environment.pop("DEBUG", None)
    environment["APP_ENV"] = "local"
    environment["SENTRY_DSN"] = ""
    if raw_value is not None:
        environment["DEBUG"] = raw_value

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from plio import settings; print(settings.DEBUG)",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == str(expected)
