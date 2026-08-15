import os

from utils.file_metadata import choose_latest


def test_choose_latest_ignores_protected_files(tmp_path):
    # Create files: a protected README.md with a very new timestamp and an older data file
    protected = tmp_path / "README.md"
    protected.write_text("do not pick me", encoding="utf-8")
    data = tmp_path / "SSAs Pendentes Geral - 15-07-2025_0236PM.xlsx"
    data.write_text("xlsx placeholder", encoding="utf-8")

    # Ensure protected has newer mtime than data
    os.utime(protected, None)

    chosen = choose_latest([str(protected), str(data)])
    assert chosen is not None
    # choose_latest should not pick the protected README, so it must pick the data file
    assert os.path.basename(chosen) == os.path.basename(data)
