import time

import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _spin_until(predicate, timeout_s: float = 0.25) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    QApplication.processEvents()
    return bool(predicate())


def test_rescan_progress_dialog_reject_emits_cancel_once_and_closes():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    emitted = []
    dlg.cancel_requested.connect(lambda: emitted.append(1))

    dlg.show()
    assert _spin_until(lambda: dlg.isVisible())

    dlg.reject()
    assert _spin_until(lambda: dlg._cancel_requested is True)

    assert len(emitted) == 1
    assert dlg._cancel_requested is True
    assert dlg.cancel_button.isEnabled() is False
    assert dlg.close_button.isEnabled() is False
    assert "Cancelamento solicitado" in dlg.status_label.text()
    assert dlg.isVisible() is True

    # Second reject should close without emitting cancel again.
    dlg.reject()
    assert _spin_until(lambda: dlg.result() == int(QDialog.DialogCode.Rejected))
    assert len(emitted) == 1


def test_rescan_progress_dialog_reject_after_finished_does_not_emit_cancel():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    emitted = []
    dlg.cancel_requested.connect(lambda: emitted.append(1))

    dlg.set_finished(True)
    dlg.reject()
    assert _spin_until(lambda: dlg.result() == int(QDialog.DialogCode.Rejected))

    assert emitted == []


def test_rescan_progress_dialog_set_finished_failure_without_message_shows_default_error():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    dlg.set_finished(False, "")
    assert _spin_until(lambda: "Reescaneamento falhou" in dlg.status_label.text())

    assert "Reescaneamento falhou" in dlg.status_label.text()
    assert "Erro nao detalhado" in dlg.status_label.text()
    assert "ERRO FINAL" in dlg.error_text.toPlainText()


def test_rescan_progress_dialog_update_progress_clamps_percentage():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()

    dlg.update_progress(-10, "negativo")
    assert dlg.progress_bar.value() == 0

    dlg.update_progress(150, "alto")
    assert dlg.progress_bar.value() == 100
