from __future__ import annotations

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
