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


def test_rescan_progress_dialog_reject_emits_cancel_once_and_keeps_open_until_finished():
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

    # Second reject should keep dialog open while process is not finished.
    dlg.reject()
    assert dlg.isVisible() is True
    assert len(emitted) == 1

    # After process finishes, reject should close.
    dlg.set_finished(False, "Processo cancelado pelo usuario")
    dlg.reject()
    assert _spin_until(lambda: dlg.result() == int(QDialog.DialogCode.Rejected))


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
    assert _spin_until(
        lambda: "Operacao falhou (Reescaneamento)" in dlg.status_label.text()
    )

    assert dlg.status_label.text() == (
        "Operacao falhou (Reescaneamento). Veja detalhes abaixo."
    )
    assert "Erro nao detalhado" not in dlg.status_label.text()
    assert "ERRO FINAL" in dlg.error_text.toPlainText()
    assert "Erro nao detalhado" in dlg.error_text.toPlainText()
    assert "Erro nao detalhado" in dlg.status_label.toolTip()


def test_rescan_progress_dialog_failure_keeps_long_detail_out_of_status_label():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    long_message = (
        "Erro ao executar operacao de importacao: "
        "Erro critico no processo de importacao. "
        "Causa raiz: PermissionError: acesso negado ao banco de runtime"
    )

    dlg.set_finished(False, long_message)

    assert dlg.status_label.text() == (
        "Operacao falhou (Reescaneamento). Veja detalhes abaixo."
    )
    assert long_message not in dlg.status_label.text()
    assert long_message in dlg.error_text.toPlainText()
    assert dlg.status_label.toolTip() == long_message


def test_rescan_progress_dialog_failure_does_not_duplicate_existing_error_detail():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    message = "Erro ao executar operacao de importacao: falha real"
    dlg.append_error(message)

    dlg.set_finished(False, message)

    assert dlg.error_text.toPlainText().count(message) == 1


def test_rescan_progress_dialog_set_finished_is_idempotent():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()
    dlg.set_finished(False, "Primeira falha")
    first_text = dlg.status_label.text()
    first_errors = dlg.error_text.toPlainText()

    dlg.set_finished(True, "Nao deve sobrescrever")

    assert dlg.status_label.text() == first_text
    assert dlg.error_text.toPlainText() == first_errors


def test_rescan_progress_dialog_update_progress_clamps_percentage():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()

    dlg.update_progress(-10, "negativo")
    assert dlg.progress_bar.value() == 0

    dlg.update_progress(150, "alto")
    assert dlg.progress_bar.value() == 100


def test_rescan_progress_dialog_starts_non_modal():
    from gui.widgets.rescan_progress_dialog import RescanProgressDialog  # noqa: E402

    dlg = RescanProgressDialog()

    assert dlg.isModal() is False
