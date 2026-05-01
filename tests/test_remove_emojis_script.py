from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.remove_emojis import remove_emojis_from_text


def test_remove_emojis_ps1_preserves_non_emoji_supplementary_chars(
    tmp_path: Path,
) -> None:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell is not available")

    script_path = Path("scripts/remove_emojis.ps1").resolve()
    sample_path = tmp_path / "sample.md"
    non_emoji = chr(0x20000)
    technical_symbol = chr(0x2713)
    emoji = chr(0x1F600)
    sample_path.write_text(
        f"keep {non_emoji} keep-symbol {technical_symbol} remove {emoji}",
        encoding="utf-8",
    )

    subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-Root",
            str(tmp_path),
            "-Includes",
            "*.md",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    cleaned = sample_path.read_text(encoding="utf-8")
    assert non_emoji in cleaned
    assert technical_symbol in cleaned
    assert emoji not in cleaned


def test_remove_emojis_py_preserves_technical_symbols_and_non_emoji_planes() -> None:
    non_emoji = chr(0x20000)
    technical_symbol = chr(0x2713)
    emoji = chr(0x1F600)

    cleaned = remove_emojis_from_text(
        f"keep {non_emoji} keep-symbol {technical_symbol} remove {emoji}"
    )

    assert non_emoji in cleaned
    assert technical_symbol in cleaned
    assert emoji not in cleaned
