"""Display configuration for SSA details rendering."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DetailsDisplayConfig:
    details_dialog_font_size: int = 10
    table_padding: int = 8
    border_color: str = "#ccc"
    field_priority: list[str] = field(default_factory=list)
    display_overrides: dict[str, str] = field(default_factory=dict)
    label_line_breaks: dict[str, str] = field(
        default_factory=lambda: {
            "grau_prioridade_emissao": "Grau de Prioridade<br/>(Emissao)",
            "data_arquivo_origem": "Data do Arquivo<br/>de Origem",
        }
    )
    highlight_background_color: str = "yellow"
    highlight_text_color: str = ""
    highlight_font_weight: str = "bold"
    mono_font_family: str = "monospace"

    def update(
        self,
        *,
        details_dialog_font_size,
        details_dialog_table_padding,
        details_dialog_border_color,
        detail_field_priority,
        detail_display_overrides,
        highlight_background_color,
        highlight_font_weight,
        mono_font_family,
        highlight_text_color=None,
    ) -> None:
        if details_dialog_font_size is not None:
            self.details_dialog_font_size = details_dialog_font_size
        if details_dialog_table_padding is not None:
            self.table_padding = details_dialog_table_padding
        if details_dialog_border_color is not None:
            self.border_color = details_dialog_border_color
        if detail_field_priority is not None:
            self.field_priority = list(detail_field_priority)
        if detail_display_overrides is not None:
            self.display_overrides = dict(detail_display_overrides)
        if highlight_background_color is not None:
            self.highlight_background_color = highlight_background_color
        if highlight_text_color is not None:
            self.highlight_text_color = highlight_text_color
        if highlight_font_weight is not None:
            self.highlight_font_weight = highlight_font_weight
        if mono_font_family is not None:
            self.mono_font_family = mono_font_family
