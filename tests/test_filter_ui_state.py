from __future__ import annotations

import pytest

from gui.ssa.filter_ui_state import FilterUiStatePresenter


class _Widget:
    def __init__(self) -> None:
        self.visible = None
        self.enabled = None
        self.text = ""

    def setVisible(self, visible: bool) -> None:
        self.visible = visible

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def setText(self, text: str) -> None:
        self.text = text


class _Logger:
    def debug(self, *_args, **_kwargs) -> None:
        raise AssertionError("unexpected UI state failure")


def test_filter_ui_state_idle_resets_status_text() -> None:
    progress = _Widget()
    load_button = _Widget()
    search_button = _Widget()
    status = _Widget()
    presenter = FilterUiStatePresenter(
        progress_bar=progress,
        load_button=load_button,
        search_button=search_button,
        status_label=status,
        logger=_Logger(),
    )

    presenter.set_busy()
    presenter.set_idle()

    assert status.text == "Status: Pronto."
    assert progress.visible is False
    assert load_button.enabled is True
    assert search_button.enabled is True


@pytest.mark.parametrize("preserve_feedback", [False, True])
def test_filter_ui_state_feedback_and_buttons_across_transitions(
    preserve_feedback: bool,
) -> None:
    progress = _Widget()
    load_button = _Widget()
    search_button = _Widget()
    status = _Widget()
    progress.visible = True
    status.text = "Status: Importando dados."
    presenter = FilterUiStatePresenter(
        progress_bar=progress,
        load_button=load_button,
        search_button=search_button,
        status_label=status,
        logger=_Logger(),
        preserve_operation_feedback=lambda: preserve_feedback,
    )

    transitions = (
        (presenter.set_busy, "Status: Filtrando dados.", True, False),
        (presenter.set_error, "Status: Erro ao aplicar filtro.", False, True),
        (presenter.set_busy, "Status: Filtrando dados.", True, False),
        (presenter.set_cleanup, "Status: Filtrando dados.", False, True),
        (presenter.set_idle, "Status: Pronto.", False, True),
    )
    for transition, filter_status, filter_progress, buttons_enabled in transitions:
        transition()
        assert status.text == (
            "Status: Importando dados." if preserve_feedback else filter_status
        )
        assert progress.visible is (True if preserve_feedback else filter_progress)
        assert load_button.enabled is buttons_enabled
        assert search_button.enabled is buttons_enabled
