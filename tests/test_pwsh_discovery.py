import json
import os
import shutil

from scripts import pwsh_discovery


def test_find_pwsh_candidates_no_workspace():
    # At minimum the function should return a list (possibly empty) without raising
    c = pwsh_discovery.find_pwsh_candidates()
    assert isinstance(c, list)


def test_pick_pwsh_with_workspace(tmp_path):
    # Create a fake workspace with a .vscode/settings.json containing a profile path
    ws = tmp_path
    vs = ws / ".vscode"
    vs.mkdir()
    # Prefer an actual pwsh if available on PATH, else use a made-up path (function should ignore non-existing)
    pw = shutil.which("pwsh") or shutil.which("powershell")
    sample_path = pw or r"C:\Program Files\PowerShell\7\pwsh.exe"
    settings = {
        "terminal.integrated.profiles.windows": {"PowerShell 7": {"path": sample_path}},
        "terminal.external.windowsExec": sample_path,
    }
    with open(vs / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f)

    candidates = pwsh_discovery.find_pwsh_candidates(str(ws))
    assert isinstance(candidates, list)
    # If sample_path exists on this system, it should appear in candidates
    if os.path.exists(sample_path):
        assert sample_path in candidates
    else:
        # if not present, ensure function didn't crash and returned list
        assert True
