from __future__ import annotations

import atexit
import importlib.util
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
from typing import Optional

_STREAMLIT_PROCESSES: list[subprocess.Popen] = []
_STREAMLIT_LOG_MAX_BYTES = 5 * 1024 * 1024
# Capturado na primeira instalacao do handler: chamadas seguintes de
# wait_for_streamlit veriam o nosso proprio handler como "anterior" e
# nunca restaurariam o original do processo.
_STREAMLIT_ORIGINAL_SIGTERM_HANDLER = None
_STREAMLIT_LAUNCHING = False
_STREAMLIT_SIGTERM_PENDING = False
logger = logging.getLogger(__name__)


def _terminate_process(process, *, reap: bool = True) -> None:
    """terminate() com espera curta e kill() de reforco.

    Um filho que ignore SIGTERM sobreviveria segurando a porta; o wait
    tambem colhe o processo para nao deixar zombie. Com reap=False o
    terminate sai imediato — usado no handler de sinal, onde um wait
    disputaria o _waitpid_lock com o wait() interrompido na main thread
    e esgotaria o timeout sem necessidade (o atexit faz a colheita apos
    o unwind liberar o lock). Pelo mesmo motivo esse caminho nao loga:
    o logging pode bloquear no lock interno do handler de log e
    impediria o sys.exit do handler de sinal.
    """
    terminate = getattr(process, "terminate", None)
    if not callable(terminate) or not _is_process_running(process):
        return
    try:
        terminate()
    except OSError as exc:
        if reap:
            logger.warning("Falha ao encerrar Streamlit: %s", exc)
        return
    if not reap:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("Encerramento forcado do Streamlit incompleto: %s", exc)
    except OSError as exc:
        logger.warning("Falha ao aguardar Streamlit: %s", exc)


def _terminate_children_and_exit(*_args) -> None:
    """Handler de SIGTERM: encerra os filhos rastreados e sai com 143.

    SIGTERM nao dispara atexit; sem este handler o filho ficaria orfao
    segurando a porta do servidor. Nao faz wait aqui: o handler pode
    interromper um process.wait() em andamento, cujo _waitpid_lock esta
    preso ate o unwind; a limpeza via atexit colhe e mata depois dele.
    """
    global _STREAMLIT_SIGTERM_PENDING
    if _STREAMLIT_LAUNCHING:
        _STREAMLIT_SIGTERM_PENDING = True
        return
    for process in list(_STREAMLIT_PROCESSES):
        _terminate_process(process, reap=False)
    sys.exit(143)


def _install_sigterm_handler() -> None:
    global _STREAMLIT_ORIGINAL_SIGTERM_HANDLER
    current = signal.getsignal(signal.SIGTERM)
    if current is not _terminate_children_and_exit:
        _STREAMLIT_ORIGINAL_SIGTERM_HANDLER = current
    signal.signal(signal.SIGTERM, _terminate_children_and_exit)


def _restore_sigterm_handler_if_idle() -> None:
    _prune_streamlit_processes()
    if _STREAMLIT_ORIGINAL_SIGTERM_HANDLER is not None and not _STREAMLIT_PROCESSES:
        try:
            signal.signal(signal.SIGTERM, _STREAMLIT_ORIGINAL_SIGTERM_HANDLER)
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("Falha ao restaurar handler SIGTERM: %s", exc)


def wait_for_streamlit() -> None:
    """Bloqueia ate o processo Streamlit mais recente encerrar.

    Em CTRL+C retorna imediatamente; a limpeza registrada em atexit
    encerra o processo filho na saida do interpretador.
    """
    process = _STREAMLIT_PROCESSES[-1] if _STREAMLIT_PROCESSES else None
    if process is None:
        return
    # signal.signal so existe na thread principal. Fora dela a espera
    # continua util, mas sem instalar/restaurar handler aqui: o handler
    # instalado no lancamento e o atexit seguem cobrindo o filho.
    in_main_thread = threading.current_thread() is threading.main_thread()
    if in_main_thread:
        _install_sigterm_handler()
    try:
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if in_main_thread:
            _restore_sigterm_handler_if_idle()


def _is_process_running(process) -> bool:
    poll = getattr(process, "poll", None)
    return callable(poll) and poll() is None


def _prune_streamlit_processes() -> None:
    _STREAMLIT_PROCESSES[:] = [
        process for process in _STREAMLIT_PROCESSES if _is_process_running(process)
    ]


def _cleanup_streamlit_processes() -> None:
    for process in list(_STREAMLIT_PROCESSES):
        _terminate_process(process)
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
    global _STREAMLIT_LAUNCHING, _STREAMLIT_SIGTERM_PENDING
    if threading.current_thread() is not threading.main_thread():
        print("Streamlit deve ser iniciado pela thread principal para tratar sinais.")
        return False
    script_path = os.path.join(project_root, "dev_env", "streamlit_app.py")
    if not os.path.exists(script_path):
        print("Streamlit app nao encontrado em dev_env/streamlit_app.py")
        return False
    launcher_cmd, launcher_source = _resolve_streamlit_launch_command()
    if launcher_cmd is None:
        print("Streamlit nao encontrado no ambiente atual nem no PATH.")
        return False

    cmd = [
        *launcher_cmd,
        "run",
        script_path,
        "--server.headless=true",
        "--server.address=127.0.0.1",
    ]
    if port:
        cmd.append(f"--server.port={port}")

    logs_dir = os.path.join(log_root or project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "streamlit.log")
    try:
        if os.path.getsize(log_path) > _STREAMLIT_LOG_MAX_BYTES:
            os.replace(log_path, f"{log_path}.1")
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"Aviso: rotacao de {log_path} falhou ({exc}); log seguira em append")

    try:
        _install_sigterm_handler()
        # Adia apenas a saida do handler ate registrar o filho. Nao altera
        # a mascara herdada nem executa Python entre fork e exec.
        _STREAMLIT_LAUNCHING = True
        try:
            with open(log_path, "ab") as log_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=log_file,
                    cwd=project_root,
                )
                _STREAMLIT_PROCESSES.append(process)
            _prune_streamlit_processes()
        finally:
            _STREAMLIT_LAUNCHING = False
            if _STREAMLIT_SIGTERM_PENDING:
                _STREAMLIT_SIGTERM_PENDING = False
                _terminate_children_and_exit()
        display_port = port or 8501
        print(f"Origem do launcher Streamlit: {launcher_source}")
        print(
            f"Streamlit iniciado em background (PID {process.pid}). Acesse http://localhost:{display_port}/"
        )
        print(f"Logs: {log_path}")
        return True
    except Exception as exc:  # noqa: BLE001
        _restore_sigterm_handler_if_idle()
        print(f"Falha ao iniciar Streamlit: {exc}")
        return False
