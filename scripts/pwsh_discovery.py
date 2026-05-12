"""
Helpers to discover `pwsh` / `powershell` executables across PATH, common install
locations, VS Code workspace settings, and WSL mounts. Provides normalization
and a small CLI for inspection.

The function is intentionally tolerant: it only *suggests* candidates and does
not modify any system or workspace configuration.
"""
import json
import os
import shlex
import shutil
from typing import List, Optional

COMMON_WINDOWS_PATHS = [
    r"C:\Program Files\PowerShell\7\pwsh.exe",
    r"C:\Program Files\PowerShell\6\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\6\pwsh.exe",
]

# Include common Homebrew / macOS paths and typical Unix locations
COMMON_UNIX_PATHS = [
    "/usr/bin/pwsh",
    "/usr/local/bin/pwsh",
    "/opt/homebrew/bin/pwsh",
    "/snap/bin/pwsh",
]


def _exists(p: str) -> bool:
    try:
        return bool(p) and os.path.exists(p) and os.access(p, os.X_OK)
    except Exception:
        return False


def _normalize_candidate(raw: str) -> Optional[str]:
    """Normalize a raw candidate string: expand vars, ~, strip quotes and
    extract an executable if the string looks like a command with args.
    """
    if not raw or not isinstance(raw, str):
        return None
    s = os.path.expanduser(os.path.expandvars(raw)).strip()
    # Strip surrounding quotes
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    # If it looks like a command line (contains spaces or args), try to extract first token
    # Use shlex to respect quoted paths
    try:
        parts = shlex.split(s, posix=os.name != 'nt')
        if parts:
            candidate = parts[0]
        else:
            candidate = s
    except Exception:
        candidate = s.split()[0] if s else None
    return candidate


def _is_wsl() -> bool:
    # Detect WSL by common indicators
    try:
        if os.name != 'nt' and os.path.exists('/proc/version'):
            with open('/proc/version', 'r', encoding='utf-8', errors='ignore') as f:
                v = f.read()
            return 'microsoft' in v.lower() or 'wsl' in v.lower()
    except Exception:
        pass
    # Also allow environment variable
    return bool(os.environ.get('WSL_DISTRO_NAME'))


def find_pwsh_candidates(workspace_root: Optional[str] = None) -> List[str]:
    """Return a list of possible pwsh/powershell executable paths (best first).

    Checks (in order):
      - `shutil.which` for `pwsh` and `powershell`
      - workspace `.vscode/settings.json` (tolerant to multiple shapes)
      - common install locations for the current OS
      - common Windows Program Files locations mounted under WSL (if running in WSL)
    """
    candidates: List[str] = []

    # 1) which
    for name in ("pwsh", "powershell"):
        path = shutil.which(name)
        if path and _exists(path):
            candidates.append(path)

    # 2) workspace settings - tolerant parsing
    if workspace_root:
        try:
            ws = os.path.join(workspace_root, ".vscode", "settings.json")
            if os.path.exists(ws):
                with open(ws, "r", encoding="utf-8") as f:
                    j = json.load(f)

                # 2a) integrated profiles (may be mapping name->dict or name->string)
                profiles = j.get("terminal.integrated.profiles.windows") or {}
                for name, v in profiles.items():
                    p = None
                    if isinstance(v, dict):
                        # Accept many possible keys that may contain executable information
                        p_raw = v.get("path") or v.get("exe") or v.get("command") or v.get("executable") or v.get("commandline")
                        # If `args` is a list, prefer its first element when it looks like an executable
                        args_list = v.get("args")
                        if not p_raw and isinstance(args_list, (list, tuple)) and args_list:
                            p_raw = args_list[0]
                        p = _normalize_candidate(p_raw) if p_raw else None
                    elif isinstance(v, str):
                        p = _normalize_candidate(v)
                    else:
                        p = None
                    if p and _exists(p) and p not in candidates:
                        candidates.append(p)

                # 2b) legacy keys and other common entries
                legacy_keys = [
                    "terminal.integrated.shell.windows",
                    "terminal.external.windowsExec",
                ]
                for key in legacy_keys:
                    v = j.get(key)
                    p = _normalize_candidate(v) if v else None
                    if p and _exists(p) and p not in candidates:
                        candidates.append(p)

                # 2c) wildcard scan: pick any string value that mentions pwsh/powershell
                for k, v in j.items():
                    if isinstance(v, str) and ("pwsh" in v.lower() or "powershell" in v.lower()):
                        p = _normalize_candidate(v)
                        if p and _exists(p) and p not in candidates:
                            candidates.append(p)
        except Exception:
            pass

    # 3) common locations for current platform
    if os.name == "nt":
        for p in COMMON_WINDOWS_PATHS:
            if _exists(p) and p not in candidates:
                candidates.append(p)
    else:
        for p in COMMON_UNIX_PATHS:
            if _exists(p) and p not in candidates:
                candidates.append(p)

    # 4) if in WSL, also inspect likely Windows Program Files mounts
    if _is_wsl():
        wsl_windows_paths = [
            "/mnt/c/Program Files/PowerShell/7/pwsh.exe",
            "/mnt/c/Program Files/PowerShell/6/pwsh.exe",
            "/mnt/c/Program Files (x86)/PowerShell/7/pwsh.exe",
        ]
        for p in wsl_windows_paths:
            if _exists(p) and p not in candidates:
                candidates.append(p)

    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def pick_pwsh(workspace_root: Optional[str] = None) -> Optional[str]:
    """Return the first found pwsh/powershell path, or None if none found."""
    candidates = find_pwsh_candidates(workspace_root)
    return candidates[0] if candidates else None


def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Discover pwsh/powershell executables")
    parser.add_argument("--workspace", help="path to workspace root (checks .vscode/settings.json)")
    parser.add_argument("--list", action="store_true", help="list all candidates")
    parser.add_argument("--json", action="store_true", help="print JSON array of candidates")
    parser.add_argument("--first", action="store_true", help="print only first candidate")
    args = parser.parse_args()
    c = find_pwsh_candidates(args.workspace)
    if args.json:
        print(json.dumps(c))
    elif args.first:
        print(c[0] if c else "")
    else:
        for p in c:
            print(p)


if __name__ == "__main__":
    _cli()
