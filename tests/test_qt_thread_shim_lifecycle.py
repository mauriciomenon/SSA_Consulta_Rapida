from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize("falha", [False, True])
def test_fallback_worker_libera_lifecycle_sem_pyqt(falha):
    script = textwrap.dedent(
        """
        import sys
        import threading
        import importlib
        from types import SimpleNamespace

        import pandas as pd

        import gui.workers.qt_thread_shim as shim
        import gui.workers.advanced_options_worker as advanced
        sys.modules['PyQt6.QtCore'] = None
        importlib.reload(shim)
        importlib.reload(advanced)
        AdvancedOptionsWorker = advanced.AdvancedOptionsWorker

        falha = sys.argv[1] == 'True'
        estado = SimpleNamespace(worker=None, ativo=True)
        eventos = []
        erros = []
        concluido = threading.Event()

        def calcular(*args, **kwargs):
            if falha:
                raise ValueError('falha prevista')
            return 'valores'

        worker = AdvancedOptionsWorker(pd.DataFrame(), {}, {}, 1, sorted, calcular)
        estado.worker = worker
        worker.ui_state_ready.connect(lambda state: eventos.append(state.values))
        worker.error_occurred.connect(erros.append)

        def finalizar():
            assert not worker.isRunning()
            estado.worker = None
            estado.ativo = False
            concluido.set()

        worker.finished.connect(finalizar)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        assert concluido.wait(5)
        assert worker.wait(5000)
        assert estado.worker is None
        assert not estado.ativo
        assert eventos == ([] if falha else ['valores'])
        assert erros == (['falha prevista'] if falha else [])
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(falha)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
