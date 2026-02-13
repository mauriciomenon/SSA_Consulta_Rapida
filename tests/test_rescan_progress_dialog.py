import pytest

pytest.importorskip(
    "PyQt6", reason="Dependencia PyQt6 indisponivel no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_rescan_progress_dialog_reject_emits_cancel_once_and_closes():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    emitted = []
    dlg.cancel_requested.connect(lambda: emitted.append(1))

    dlg.show()
    QApplication.processEvents()

    dlg.reject()
    QApplication.processEvents()

    assert len(emitted) == 1
    assert dlg.result() == int(QDialog.DialogCode.Rejected)
    assert not dlg.isVisible()

    # Second reject should not emit cancel again.
    dlg.reject()
    QApplication.processEvents()
    assert len(emitted) == 1


def test_rescan_progress_dialog_reject_after_finished_does_not_emit_cancel():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    emitted = []
    dlg.cancel_requested.connect(lambda: emitted.append(1))

    dlg.set_finished(True)
    dlg.reject()
    QApplication.processEvents()

    assert emitted == []

