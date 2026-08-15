from __future__ import annotations

import atexit
import importlib.util
import os
import shutil
import subprocess
import sys
from typing import Optional

_STREAMLIT_PROCESSES: list[subprocess.Popen] = []


def _is_process_running(process) -> bool:
    poll = getattr(process, "poll", None)
    return callable(poll) and poll() is None


def _prune_streamlit_processes() -> None:
    _STREAMLIT_PROCESSES[:] = [
        process for process in _STREAMLIT_PROCESSES if _is_process_running(process)
    ]


def _cleanup_streamlit_processes() -> None:
    for process in list(_STREAMLIT_PROCESSES):
        terminate = getattr(process, "terminate", None)
        if not callable(terminate):
            continue
        if _is_process_running(process):
            terminate()
    _STREAMLIT_PROCESSES.clear()


atexit.register(_cleanup_streamlit_processes)


def _resolve_streamlit_launch_command() -> tuple[Optional[list[str]], str]:
    is_frozen_mode = bool(
        getattr(sys, "frozen", False)
        or getattr(sys, "oxidized", False)
        or "__compiled__" in globals()
    )
    if not is_frozen_mode and importlib.util.find_spec("streamlit") is not None:
        return [sys.executable, "-m", "streamlit"], "ambiente atual"

    streamlit_path = shutil.which("streamlit")
    if streamlit_path:
        return [os.path.abspath(streamlit_path)], "PATH"

    return None, ""


def launch_streamlit(
    project_root: str, port: Optional[int] = None, log_root: Optional[str] = None
) -> bool:
    script_path = os.path.join(project_root, "dev_env", "streamlit_app.py")
    if not os.path.exists(script_path):
        print("Streamlit app nao encontrado em dev_env/streamlit_app.py")
        return False
    launcher_cmd, launcher_source = _resolve_streamlit_launch_command()
    if launcher_cmd is None:
        print("Streamlit nao encontrado no ambiente atual nem no PATH.")
        return False

    cmd = [*launcher_cmd, "run", script_path, "--server.headless=true"]
    if port:
        cmd.append(f"--server.port={port}")

    logs_dir = os.path.join(log_root or project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "streamlit.log")

    try:
        with open(log_path, "ab") as log_file:
            process = subprocess.Popen(
                cmd, stdout=log_file, stderr=log_file, cwd=project_root
            )
        _prune_streamlit_processes()
        _STREAMLIT_PROCESSES.append(process)
        display_port = port or 8501
        print(f"Origem do launcher Streamlit: {launcher_source}")
        print(
            f"Streamlit iniciado em background (PID {process.pid}). Acesse http://localhost:{display_port}/"
        )
        print(f"Logs: {log_path}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Falha ao iniciar Streamlit: {exc}")
        return False
