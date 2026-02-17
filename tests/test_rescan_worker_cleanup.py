import pytest

pytest.importorskip("PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste")
from PyQt6.QtWidgets import QApplication

import gui.workers.rescan_worker as rescan_worker_mod  # noqa: E402
from gui.workers.rescan_worker import RescanWorker  # noqa: E402

project_root = "pythonpath-configured"

@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_rescan_worker_cleanup_does_not_hang_when_logger_cleanup_fails(monkeypatch):
    baseline_refcount = rescan_worker_mod._LOGGER_REFCOUNT
    worker = RescanWorker("main.py", project_root)
    emitted = []
    worker.finished_error.connect(emitted.append)

    def _boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(rescan_worker_mod, "run_importer_logic", _boom)

    real_remove = worker.logger.removeHandler

    def _bad_remove(_handler):
        raise ValueError("remove failed")

    monkeypatch.setattr(worker.logger, "removeHandler", _bad_remove)
    try:
        worker.run()
    finally:
        monkeypatch.setattr(worker.logger, "removeHandler", real_remove)
        try:
            worker.logger.removeHandler(worker.log_handler)
        except Exception:
            pass

    assert emitted
    assert emitted[0] == "Erro ao executar reescaneamento."
    assert worker._logger_attached is False
    assert rescan_worker_mod._LOGGER_REFCOUNT == baseline_refcount
