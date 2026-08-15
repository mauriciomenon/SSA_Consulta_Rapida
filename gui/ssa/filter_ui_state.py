"""UI state presenter for SSA filtering actions."""

from __future__ import annotations

from typing import Any, Protocol


class VisibleWidget(Protocol):
    def setVisible(self, visible: bool) -> None: ...


class EnabledWidget(Protocol):
    def setEnabled(self, enabled: bool) -> None: ...


class TextWidget(Protocol):
    def setText(self, text: str) -> None: ...


class FilterUiStatePresenter:
    def __init__(
        self,
        *,
        progress_bar: VisibleWidget | None,
        load_button: EnabledWidget | None,
        search_button: EnabledWidget | None,
        status_label: TextWidget | None,
        logger: Any,
    ) -> None:
        self._progress_bar = progress_bar
        self._buttons = (("load_button", load_button), ("search_button", search_button))
        self._status_label = status_label
        self._logger = logger

    def set_idle(self) -> None:
        self._set_status_text("Status: Pronto.", "idle")
        self._set_progress_visible(False, "idle")
        self._set_buttons_enabled(True, "idle")

    def set_busy(self) -> None:
        self._set_status_text("Status: Filtrando dados.", "busy")
        self._set_progress_visible(True, "busy")
        self._set_buttons_enabled(False, "busy")

    def set_error(self) -> None:
        self._set_status_text("Status: Erro ao aplicar filtro.", "error")
        self._set_progress_visible(False, "error")
        self._set_buttons_enabled(True, "error")

    def set_cleanup(self) -> None:
        self._set_progress_visible(False, "cleanup")
        self._set_buttons_enabled(True, "cleanup")

    def _set_progress_visible(self, visible: bool, context: str) -> None:
        try:
            if self._progress_bar is not None:
                self._progress_bar.setVisible(bool(visible))
        except Exception as exc:
            self._logger.debug(
                "Falha ao atualizar progress bar de filtro em %s: %s",
                context,
                exc,
            )

    def _set_buttons_enabled(self, enabled: bool, context: str) -> None:
        for button_attr, button in self._buttons:
            try:
                if button is not None:
                    button.setEnabled(bool(enabled))
            except Exception as exc:
                self._logger.debug(
                    "Falha ao atualizar botao %s em estado %s de filtro: %s",
                    button_attr,
                    context,
                    exc,
                )

    def _set_status_text(self, text: str, context: str) -> None:
        try:
            if self._status_label is not None:
                self._status_label.setText(text)
        except Exception as exc:
            self._logger.debug(
                "Falha ao atualizar status de filtro em %s: %s",
                context,
                exc,
            )
