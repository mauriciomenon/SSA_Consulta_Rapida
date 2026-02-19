"""Tab context sync mixin extracted from SSAMainWindow."""
from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class _TabContextHostProtocol(Protocol):
    _tab_contexts: Any

    def __getattr__(self, name: str) -> Any: ...


class TabContextGUISSAMixin:
    @staticmethod
    def _is_bindable_context_key(name: str) -> bool:
        if not name:
            return False
        if name == "tab_kind":
            return False
        return not name.startswith("_")

    def _bump_data_revision(self: _TabContextHostProtocol, reason: str = "") -> int:
        try:
            next_rev = int(self._data_revision or 0) + 1
        except (AttributeError, TypeError, ValueError):
            next_rev = 1
        setattr(self, "_data_revision", next_rev)
        try:
            setattr(
                self,
                "_data_revision_df_ids",
                (
                id(self.df_completo),
                id(self.df_exibido),
                ),
            )
        except AttributeError:
            pass
        if reason:
            logger.debug("Data revision bump (%s): %s", reason, next_rev)
        return next_rev

    def _ensure_data_revision(self: _TabContextHostProtocol) -> None:
        try:
            current_ids = (
                id(self.df_completo),
                id(self.df_exibido),
            )
        except AttributeError:
            return
        try:
            previous_ids = self._data_revision_df_ids
        except AttributeError:
            previous_ids = None
        if previous_ids != current_ids:
            self._bump_data_revision("df_identity_change")

    def _sync_bind_search_state(self: _TabContextHostProtocol, ctx: dict) -> None:
        try:
            self.clear_filter_button.setEnabled(self._has_any_active_filters())
        except Exception as exc:
            logger.debug("Falha ao sincronizar estado do botao limpar filtro no bind de aba: %s", exc)
        try:
            if ctx.get("tab_kind") == "filters":
                try:
                    debounce_timer = self._debounce_timer
                    if debounce_timer is not None:
                        debounce_timer.stop()
                except AttributeError:
                    pass
                except Exception as exc:
                    logger.debug("Falha ao parar debounce no bind da aba de filtros: %s", exc)
                self.search_input.blockSignals(True)
                self.search_input.clear()
        except Exception as exc:
            logger.debug("Falha ao limpar busca durante bind da aba de filtros: %s", exc)
        finally:
            try:
                if ctx.get("tab_kind") == "filters":
                    self.search_input.blockSignals(False)
            except Exception as exc:
                logger.debug("Falha ao reativar sinais da busca no bind da aba de filtros: %s", exc)
        try:
            self.clear_filter_button.setEnabled(self._has_any_active_filters())
        except Exception as exc:
            logger.debug("Falha ao atualizar estado do botao limpar apos bind de aba: %s", exc)

    def _sync_bind_filter_options(self: _TabContextHostProtocol, tab_kind: str | None) -> None:
        try:
            if tab_kind == "filters" and self.adv_filters_group is not None:
                if self._adv_options_dirty or not self._adv_values_cache:
                    try:
                        self._refresh_advanced_filter_options()
                        setattr(self, "_adv_options_dirty", False)
                    except Exception as exc:
                        logger.warning("Falha ao atualizar opcoes avancadas no bind da aba filtros: %s", exc)
        except AttributeError:
            pass
        except Exception as exc:
            logger.debug("Falha no bloco de refresh de opcoes avancadas no bind de aba: %s", exc)

        try:
            if not self.exclude_ste_checkbox.isVisible():
                setattr(self, "_exclude_ste_sca", False)
        except AttributeError:
            pass
        except Exception as exc:
            logger.debug("Falha ao normalizar estado exclude_ste no bind de aba: %s", exc)

    def _sync_bind_profile_selector(self: _TabContextHostProtocol) -> None:
        try:
            if self.current_filter_profile:
                idx = self.profile_selector.findData(self.current_filter_profile)
            else:
                idx = 0
            if idx >= 0:
                self.profile_selector.blockSignals(True)
                self.profile_selector.setCurrentIndex(idx)
        except Exception as exc:
            logger.debug("Falha ao sincronizar seletor de perfil no bind de aba: %s", exc)
        finally:
            try:
                self.profile_selector.blockSignals(False)
            except Exception as exc:
                logger.debug("Falha ao reativar sinais do seletor de perfil no bind de aba: %s", exc)

    def _sync_bind_table_state(self: _TabContextHostProtocol, ctx: dict, tab_kind: str | None) -> None:
        try:
            self.column_selector.set_selected_columns(self.visible_columns)
        except Exception as exc:
            logger.debug("Falha ao sincronizar colunas visiveis no seletor da aba: %s", exc)

        try:
            df_id = id(self.df_exibido)
            if ctx.get("_paginator_df_id") != df_id:
                self.paginator.set_dataframe(self.df_exibido)
                ctx["_paginator_df_id"] = df_id
        except Exception as exc:
            logger.debug("Falha ao sincronizar dataframe no paginator durante bind de aba: %s", exc)
        try:
            if tab_kind != "filters":
                self._build_column_filters_panel()
        except Exception as exc:
            logger.debug("Falha ao reconstruir painel de filtros por coluna no bind de aba: %s", exc)
        try:
            if tab_kind != "filters" and self._pending_theme_refresh_column_filters:
                self._refresh_column_filter_widgets()
                setattr(self, "_pending_theme_refresh_column_filters", None)
        except AttributeError:
            pass
        except Exception as exc:
            logger.debug("Falha ao aplicar refresh pendente de tema nos filtros por coluna: %s", exc)
        try:
            if tab_kind != "filters":
                self._update_col_filter_indicator()
        except Exception as exc:
            logger.debug("Falha ao atualizar indicador de filtros por coluna no bind de aba: %s", exc)
        try:
            self._update_filters_summary()
        except Exception as exc:
            logger.debug("Falha ao atualizar resumo de filtros no bind de aba: %s", exc)
        try:
            self._update_undo_button_state()
        except Exception as exc:
            logger.debug("Falha ao atualizar estado do botao undo no bind de aba: %s", exc)
        try:
            if tab_kind != "filters":
                self.update_filter_tags()
        except Exception as exc:
            logger.debug("Falha ao atualizar tags de filtros no bind de aba: %s", exc)

    def _sync_bind_theme_and_render(self: _TabContextHostProtocol, ctx: dict) -> None:
        try:
            current_theme = self._current_theme
            if current_theme and ctx.get("_theme_name") != current_theme:
                self.apply_theme(current_theme)
                ctx["_theme_name"] = current_theme
        except AttributeError:
            pass
        except Exception as exc:
            logger.warning("Falha ao reaplicar tema no bind de aba: %s", exc)
        try:
            current_page = max(1, self.paginator.current_page)
            render_key = (id(self.df_exibido), current_page, tuple(self.visible_columns))
            if ctx.get("_last_render_key") != render_key:
                self.display_current_page(current_page)
                ctx["_last_render_key"] = render_key
        except Exception as exc:
            logger.warning("Falha ao renderizar pagina no bind de aba: %s", exc)

    def _bind_tab_context(self: _TabContextHostProtocol, ctx: dict) -> None:
        setattr(self, "_current_tab_kind", ctx.get("tab_kind"))
        for name, value in ctx.items():
            if not self._is_bindable_context_key(name):
                continue
            setattr(self, name, value)
        tab_kind = ctx.get("tab_kind")
        self._sync_bind_search_state(ctx)
        self._sync_bind_filter_options(tab_kind)
        self._sync_bind_profile_selector()
        self._sync_bind_table_state(ctx, tab_kind)
        self._sync_bind_theme_and_render(ctx)

    def _sync_checks_to_tab_context(self: _TabContextHostProtocol):
        """Mantem o contexto da aba Filtros com as listas de checkboxes reconstruidas."""
        try:
            if not hasattr(self, "_tab_contexts"):
                return
            filters_ctx = None
            for ctx in self._tab_contexts:
                if ctx.get("tab_kind") == "filters":
                    filters_ctx = ctx
                    break
            if filters_ctx is None:
                return

            synced = 0
            for attr, value in vars(self).items():
                if not attr.startswith("adv_") or not attr.endswith("_checks"):
                    continue
                if value is None:
                    continue
                filters_ctx[attr] = value
                synced += 1
            logger.debug("_sync_checks_to_tab_context: %s atributos sincronizados", synced)
        except Exception as e:
            logger.error("Erro em _sync_checks_to_tab_context: %s", e)
