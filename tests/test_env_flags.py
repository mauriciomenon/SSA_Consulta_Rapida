"""CF-13: SSA_NON_INTERACTIVE (e flags booleanas) com uma leitura so."""

import subprocess
from pathlib import Path

import pytest

from shared.env_flags import env_truthy, non_interactive_env

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", True), ("true", True), ("YES", True), (" on ", True),
     ("", False), ("0", False), ("false", False), ("no", False), ("off", False)],
)
def test_env_truthy_values(monkeypatch, value, expected):
    monkeypatch.setenv("SSA_NON_INTERACTIVE", value)
    assert env_truthy("SSA_NON_INTERACTIVE") is expected
    assert non_interactive_env() is expected


def test_no_production_code_reads_non_interactive_directly():
    result = subprocess.run(
        ["git", "-C", str(ROOT), "grep", "-n", "SSA_NON_INTERACTIVE", "--", "*.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    offenders = [
        line
        for line in result.stdout.splitlines()
        if "os.environ" in line
        and not line.startswith(("tests/", "shared/env_flags.py", "scripts/run_all_tests.py"))
    ]
    assert offenders == []
