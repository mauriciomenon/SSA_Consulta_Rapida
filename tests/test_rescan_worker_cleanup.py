import os
import sys

import pytest

pytest.importorskip("PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste")
from PyQt6.QtWidgets import QApplication

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import gui.workers.rescan_worker as rescan_worker_mod  # noqa: E402
from gui.workers.rescan_worker import RescanWorker  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_rescan_worker_cleanup_does_not_hang_when_logger_cleanup_fails(monkeypatch):
    worker = RescanWorker("main.py", project_root)
    emitted = []
    worker.finished_error.connect(emitted.append)

    def _boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(rescan_worker_mod, "run_importer_logic", _boom)

    real_remove = worker.logger.removeHandler

    def _bad_remove(_handler):
        raise ValueError("remove failed")

    worker.logger.removeHandler = _bad_remove
    try:
        worker.run()
    finally:
        worker.logger.removeHandler = real_remove
        try:
            worker.logger.removeHandler(worker.log_handler)
        except Exception:
            pass

    assert emitted
    assert "boom" in emitted[0]

