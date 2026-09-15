from __future__ import annotations

import atexit
import importlib.util
import os
import shutil
import signal
import subprocess
import sys
from typing import Optional

_STREAMLIT_PROCESSES: list[subprocess.Popen] = []
_STREAMLIT_LOG_MAX_BYTES = 5 * 1024 * 1024


def _terminate_process(process, *, reap: bool = True) -> None:
    """terminate() com espera curta e kill() de reforco.

    Um filho que ignore SIGTERM sobreviveria segurando a porta; o wait
    tambem colhe o processo para nao deixar zombie. Com reap=False o
    terminate sai imediato — usado no handler de sinal, onde um wait
    disputaria o _waitpid_lock com o wait() interrompido na main thread
    e esgotaria o timeout sem necessidade (o atexit faz a colheita apos
    o unwind liberar o lock).
    """
    terminate = getattr(process, "terminate", None)
    if not callable(terminate) or not _is_process_running(process):
        return
    try:
        terminate()
    except OSError:
        return
    if not reap:
        return
    try:
        process.wait(timeout=5)
    except Exception:
        kill = getattr(process, "kill", None)
        if callable(kill):
            try:
                kill()
            except OSError:
                pass


def _terminate_children_and_exit(*_args) -> None:
    """Handler de SIGTERM: encerra os filhos rastreados e sai com 143.

    SIGTERM nao dispara atexit; sem este handler o filho ficaria orfao
    segurando a porta do servidor. Nao faz wait aqui: o handler pode
    interromper um process.wait() em andamento, cujo _waitpid_lock esta
    preso ate o unwind; a limpeza via atexit colhe e mata depois dele.
    """
    for process in list(_STREAMLIT_PROCESSES):
        _terminate_process(process, reap=False)
    sys.exit(143)


def _install_sigterm_handler() -> None:
    try:
        signal.signal(signal.SIGTERM, _terminate_children_and_exit)
    except (OSError, RuntimeError, ValueError):
        # Fora da main thread ou sem suporte a sinais: atexit segue como rede.
        pass


def _block_sigterm():
    """Bloqueia SIGTERM nesta thread (POSIX) e retorna a mascara anterior.

    Sem pthread_sigmask (Windows), retorna None: a janela residual e
    tratada pelo handler instalado antes do Popen.
    """
    mask = getattr(signal, "pthread_sigmask", None)
    if not callable(mask):
        return None
    try:
        return mask(signal.SIG_BLOCK, [signal.SIGTERM])
    except (OSError, ValueError):
        return None


def _restore_sigterm_mask(old_mask) -> None:
    if old_mask is None:
        return
    mask = getattr(signal, "pthread_sigmask", None)
    if callable(mask):
        mask(signal.SIG_SETMASK, old_mask)


def _make_child_sigmask_restorer(old_mask):
    """Retorna preexec_fn que restaura a mascara de sinais no filho.

    Sem isso o filho herdaria SIGTERM bloqueado (a mascara e herdada no
    fork e sobrevive ao exec): terminate() ficaria pendente para sempre.
    """
    if old_mask is None or not callable(getattr(signal, "pthread_sigmask", None)):
        return None

    def _restore() -> None:
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

    return _restore


def wait_for_streamlit() -> None:
    """Bloqueia ate o processo Streamlit mais recente encerrar.

    Em CTRL+C retorna imediatamente; a limpeza registrada em atexit
    encerra o processo filho na saida do interpretador.
    """
    process = _STREAMLIT_PROCESSES[-1] if _STREAMLIT_PROCESSES else None
    if process is None:
        return
    previous_handler = None
    try:
        previous_handler = signal.getsignal(signal.SIGTERM)
    except (OSError, ValueError):
        pass
    _install_sigterm_handler()
    try:
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        # Restaura o handler anterior quando nao restam filhos vivos:
        # manter o nosso faria um SIGTERM posterior sair com 143 sem
        # nada para encerrar, ignorando o handler original do chamador.
        _prune_streamlit_processes()
        if previous_handler is not None and not _STREAMLIT_PROCESSES:
            try:
                signal.signal(signal.SIGTERM, previous_handler)
            except (OSError, RuntimeError, ValueError):
                pass


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
    script_path = os.path.join(project_root, "dev_env", "streamlit_app.py")
    if not os.path.exists(script_path):
        print("Streamlit app nao encontrado em dev_env/streamlit_app.py")
        return False
    launcher_cmd, launcher_source = _resolve_streamlit_launch_command()
    if launcher_cmd is None:
        print("Streamlit nao encontrado no ambiente atual nem no PATH.")
        return False

    # 127.0.0.1 explicito: a autorizacao de caminhos digitados na UI usa o
    # allowlist global do processo, entao o servidor nao pode ficar
    # acessivel fora de loopback.
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
        # Handler antes do Popen: cobre a janela entre o append e o wait.
        _install_sigterm_handler()
        # SIGTERM bloqueado ate o filho estar rastreado: um sinal nesse
        # intervalo fica pendente e dispara o handler apos o desbloqueio,
        # com o processo ja em _STREAMLIT_PROCESSES.
        old_mask = _block_sigterm()
        try:
            popen_kwargs: dict = {}
            restorer = _make_child_sigmask_restorer(old_mask)
            if restorer is not None:
                # Sem o restore no filho, o processo herdaria SIGTERM
                # bloqueado e terminate() ficaria pendente para sempre.
                popen_kwargs["preexec_fn"] = restorer
            with open(log_path, "ab") as log_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=log_file,
                    cwd=project_root,
                    **popen_kwargs,
                )
            _prune_streamlit_processes()
            _STREAMLIT_PROCESSES.append(process)
        finally:
            _restore_sigterm_mask(old_mask)
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
