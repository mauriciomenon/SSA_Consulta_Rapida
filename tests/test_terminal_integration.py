#!/usr/bin/env python3
"""
Test de integração do terminal do VS Code (seguro, with timeouts and fallbacks).

Este teste verifica várias estratégias para localizar e invocar um shell PowerShell
compatível (`pwsh` preferencialmente, com fallback para `powershell`) e assegura que
comandos básicos terminem dentro de timeouts razoáveis. Ele pode ser executado localmente
com `pytest tests/test_terminal_integration.py`.

Comportamento principal:
- Extrai candidatos de `settings.json` do VS Code (perfil integrado e terminal externo).
- Procura no `PATH` e em locais comuns do Windows como fallback.
- Tenta invocar o shell com timeout e valida saída mínima.
- Valida que `pwsh` consegue invocar `python -c 'print(sys.executable)'` quando aplicável.

Notas:
- O teste faz skips seguros quando o executável não for encontrado.
- Timeouts são controláveis por constantes no arquivo.
"""

import importlib
import json
import os
import shutil
import subprocess
from typing import List

import pytest

try:
    json5 = importlib.import_module("json5")
except Exception:  # noqa: BLE001
    json5 = None

# Timeouts (seconds) - tune as needed
SHELL_ECHO_TIMEOUT = 10
SHELL_PYTHON_TIMEOUT = 10
SHELL_GENERIC_TIMEOUT = 10


def _user_settings_path_windows() -> str:
    appdata = os.environ.get("APPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming"
    )
    return os.path.join(appdata, "Code", "User", "settings.json")


def load_user_settings():
    path = _user_settings_path_windows()
    if not os.path.exists(path):
        pytest.skip(f"VS Code user settings not found at: {path}")
    return _load_json_or_jsonc(path), path


def _load_json_or_jsonc(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        json5_error: Exception | None = None
        if json5 is not None:
            try:
                return json5.loads(raw)
            except Exception as exc:  # noqa: BLE001
                json5_error = exc
        # VS Code settings can be JSONC (line comments + block comments + trailing commas).
        cleaned = _strip_jsonc_comments(raw)
        cleaned = _strip_jsonc_trailing_commas(cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            if json5_error is not None:
                raise json.JSONDecodeError(
                    f"{exc.msg}; json5 fallback failed: {json5_error}",
                    exc.doc,
                    exc.pos,
                ) from json5_error
            raise


def _strip_jsonc_comments(raw: str) -> str:
    out = []
    in_string = False
    escaped = False
    index = 0
    raw_len = len(raw)

    while index < raw_len:
        current = raw[index]
        nxt = raw[index + 1] if index + 1 < raw_len else ""

        if in_string:
            out.append(current)
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                in_string = False
            index += 1
            continue

        if current == '"':
            in_string = True
            out.append(current)
            index += 1
            continue

        if current == "/" and nxt == "/":
            index += 2
            while index < raw_len and raw[index] not in ("\n", "\r"):
                index += 1
            continue

        if current == "/" and nxt == "*":
            index += 2
            comment_closed = False
            while index + 1 < raw_len:
                if raw[index] == "*" and raw[index + 1] == "/":
                    comment_closed = True
                    break
                index += 1
            if comment_closed:
                index += 2
            else:
                # Unterminated block comment: consume remainder safely.
                index = raw_len
            continue

        out.append(current)
        index += 1

    return "".join(out)


def _strip_jsonc_trailing_commas(raw: str) -> str:
    out = []
    in_string = False
    escaped = False
    index = 0
    raw_len = len(raw)

    while index < raw_len:
        current = raw[index]

        if in_string:
            out.append(current)
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                in_string = False
            index += 1
            continue

        if current == '"':
            in_string = True
            out.append(current)
            index += 1
            continue

        if current == ",":
            lookahead = index + 1
            while lookahead < raw_len and raw[lookahead].isspace():
                lookahead += 1
            if lookahead < raw_len and raw[lookahead] in ("}", "]"):
                index += 1
                continue

        out.append(current)
        index += 1

    return "".join(out)


def get_pwsh_candidates(settings: dict) -> List[str]:
    candidates: List[str] = []
    profiles = settings.get("terminal.integrated.profiles.windows", {}) or {}
    default = settings.get("terminal.integrated.defaultProfile.windows")

    # Default profile path (if present)
    if default and default in profiles:
        p = profiles[default].get("path")
        if isinstance(p, list):
            candidates.extend(p)
        elif isinstance(p, str):
            candidates.append(p)

    # Any profile mentioning pwsh
    for _, prof in profiles.items():
        p = prof.get("path")
        if isinstance(p, list):
            for item in p:
                if "pwsh" in str(item).lower() or "powershell" in str(item).lower():
                    candidates.append(item)
        elif isinstance(p, str):
            if "pwsh" in p.lower() or "powershell" in p.lower():
                candidates.append(p)

    # External terminal config
    ext = settings.get("terminal.external.windowsExec")
    if ext and ("pwsh" in str(ext).lower() or "powershell" in str(ext).lower()):
        candidates.append(ext)

    # Also consider the explicit WindowsApps path often used by MS Store
    candidates.extend(
        [
            r"C:\\Program Files\\PowerShell\\7\\pwsh.exe",
            r"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            r"C:\\Windows\\Sysnative\\WindowsPowerShell\\v1.0\\powershell.exe",
        ]
    )

    # Normalize environment variables
    candidates = [os.path.expandvars(str(c)) for c in candidates if c]
    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def test_pwsh_path_discovered_and_exists():
    settings, path = load_user_settings()
    candidates = get_pwsh_candidates(settings)

    which_pwsh = shutil.which("pwsh") or shutil.which("pwsh.exe")
    which_pwsh_fallback = shutil.which("powershell") or shutil.which("powershell.exe")

    exists_any = False
    checked = []
    for c in candidates:
        checked.append(c)
        try:
            if os.path.exists(c):
                exists_any = True
                break
        except OSError as exc:
            checked[-1] = f"{c} ({exc.__class__.__name__})"

    if which_pwsh:
        exists_any = True

    if not exists_any and which_pwsh_fallback:
        # allow fallback to Windows PowerShell
        exists_any = True

    assert exists_any, (
        "Nenhum executável 'pwsh' ou 'powershell' encontrado. "
        f"Candidatos extraídos: {checked}. PATH lookup: pwsh={which_pwsh}, powershell={which_pwsh_fallback}"
    )


def _try_spawn(
    cmd: List[str], timeout: int = SHELL_GENERIC_TIMEOUT
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        # Make timeout explicit so CI or caller can identify a hang
        raise RuntimeError(
            f"Hang detected: command {cmd} timed out after {timeout}s"
        ) from e


def test_spawn_shell_and_invoke_python():
    # Prefer pwsh, fallback to powershell
    pwsh = shutil.which("pwsh") or shutil.which("pwsh.exe")
    powershell = shutil.which("powershell") or shutil.which("powershell.exe")

    if pwsh:
        shell = pwsh
        is_pwsh = True
    elif powershell:
        shell = powershell
        is_pwsh = False
    else:
        pytest.skip(
            "Nem 'pwsh' nem 'powershell' disponíveis no PATH; pulando testes de spawn"
        )

    # Test: simple echo/print command
    if is_pwsh:
        cmd_echo = [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            "Write-Output 'ok'; exit 0",
        ]
    else:
        # powershell.exe uses different quoting semantics
        cmd_echo = [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            "Write-Output 'ok'; exit 0",
        ]

    proc = _try_spawn(cmd_echo, timeout=SHELL_ECHO_TIMEOUT)
    assert proc.returncode == 0, (
        f"Shell retornou código {proc.returncode}; stderr: {proc.stderr}"
    )
    assert "ok" in proc.stdout.strip(), f"Saída inesperada do shell: {proc.stdout!r}"

    # Test: invoke Python via the shell to ensure shell→Python integration
    py_cmd = 'python -c "import sys; print(sys.executable)"'
    cmd_python = [shell, "-NoLogo", "-NoProfile", "-Command", py_cmd]
    proc2 = _try_spawn(cmd_python, timeout=7)

    assert proc2.returncode == 0, (
        f"Invocação python via shell falhou com código {proc2.returncode}; stderr: {proc2.stderr}"
    )
    assert proc2.stdout.strip(), "Python via shell retornou stdout vazio"
    # Basic sanity: printed path contains 'python' or endswith .exe on Windows
    out = proc2.stdout.strip().lower()
    assert "python" in out or out.endswith(".exe"), (
        f"Saída python inesperada: {proc2.stdout!r}"
    )


def test_workspace_vscode_settings_env_vars():
    # Check workspace .vscode/settings.json for SSA_ENV_* variables as a helpful hint
    ws_settings_path = os.path.join(os.getcwd(), ".vscode", "settings.json")
    if not os.path.exists(ws_settings_path):
        pytest.skip(
            "Workspace .vscode/settings.json não existe; pule este teste se não aplicável"
        )

    try:
        ws = _load_json_or_jsonc(ws_settings_path)
    except Exception as exc:
        pytest.skip(f"Workspace settings parsing failed: {exc}")

    envs = ws.get("terminal.integrated.env.windows", {}) or {}
    # Ensure keys exist or skip
    if not envs:
        pytest.skip(
            "Nenhuma variável terminal.integrated.env.windows definida no workspace settings"
        )

    assert "SSA_ENV_REPO_ROOT" in envs, (
        "SSA_ENV_REPO_ROOT ausente em workspace .vscode/settings.json"
    )
    assert envs.get("SSA_ENV_PLATFORM") in (
        "windows",
        "windows-bash",
        None,
    ) or isinstance(envs.get("SSA_ENV_PLATFORM"), str)
