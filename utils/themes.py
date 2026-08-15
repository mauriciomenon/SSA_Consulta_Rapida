"""
Sistema de temas para a interface PyQt6 do SSA Consulta Rapida.

Define paletas de cores e roles para multiplos temas visuais, incluindo
temas claros, escuros e populares como Dracula, Gruvbox, Tokyo Night, etc.
"""

from PyQt6.QtGui import QColor, QPalette

# Definicao de roles (papeis) de cores para cada tema
THEME_ROLES: dict[str, dict[str, str]] = {
    "grayscale": {
        # Accents
        "accent": "#e6e6e6",
        "accent_soft": "#cfd3d6",
        # Text
        # "label_color": "#f0f0f0",
        "label_color": "#f0f0f0",
        "support_text_color": "#cdd0d4",
        "indicator_text_color": "#f0f0f0",
        "summary_text_color": "#f0f0f0",
        # Panels & Frames
        "panel_bg": "#2b2e33",
        "panel_text": "#f0f0f0",
        "panel_border": "#4a4d52",
        "summary_frame_bg": "#31343a",
        "summary_frame_border": "#4a4d52",
        # Inputs
        "input_bg": "#2f3238",
        "input_text": "#f0f0f0",
        "input_border": "#4a4d52",
        "input_border_focus": "#e6e6e6",
        "input_placeholder": "#9aa0aa",
        # Tags
        "tag_normal_bg": "transparent",
        "tag_border": "#6b6e74",
        "tag_hover": "#2f3238",
        "tag_pressed": "#3a3d44",
    },
    "windows7": {
        "accent": "#2b6cc0",
        "accent_soft": "#4b76c2",
        "label_color": "#1a1a1a",
        "support_text_color": "#3c4a6f",
        "indicator_text_color": "#1a1a1a",
        "summary_text_color": "#1a1a1a",
        "panel_bg": "#f8fbff",
        "panel_text": "#1a1a1a",
        "panel_border": "#d8e5fb",
        "summary_frame_bg": "#f8fbff",
        "summary_frame_border": "#d8e5fb",
        "input_bg": "#ffffff",
        "input_text": "#1a1a1a",
        "input_border": "#c2d6f6",
        "input_border_focus": "#2b6cc0",
        "input_placeholder": "#5d6f89",
        "tag_normal_bg": "transparent",
        "tag_border": "#909090",
        "tag_hover": "#f0f7ff",
        "tag_pressed": "#d9ecff",
    },
    "classico": {
        "accent": "#3584e4",
        "accent_soft": "#5a96e9",
        "label_color": "#2e3436",
        "support_text_color": "#4c5153",
        "indicator_text_color": "#2e3436",
        "summary_text_color": "#2e3436",
        "panel_bg": "#f6f5f4",
        "panel_text": "#2e3436",
        "panel_border": "#d7d4d1",
        "summary_frame_bg": "#f6f5f4",
        "summary_frame_border": "#d7d4d1",
        "input_bg": "#fdfdfd",
        "input_text": "#2e3436",
        "input_border": "#c9cdce",
        "input_border_focus": "#3584e4",
        "input_placeholder": "#6d7173",
        "tag_normal_bg": "transparent",
        "tag_border": "#909090",
        "tag_hover": "#f0f7ff",
        "tag_pressed": "#d9ecff",
    },
    "gruvbox": {
        "accent": "#fabd2f",
        "accent_soft": "#ebdbb2",
        "label_color": "#fabd2f",
        "support_text_color": "#d5c4a1",
        "indicator_text_color": "#ebdbb2",
        "summary_text_color": "#ebdbb2",
        "panel_bg": "#3c3836",
        "panel_text": "#ebdbb2",
        "panel_border": "#665c54",
        "summary_frame_bg": "#3c3836",
        "summary_frame_border": "#665c54",
        "input_bg": "#3c3836",
        "input_text": "#ebdbb2",
        "input_border": "#665c54",
        "input_border_focus": "#fabd2f",
        "input_placeholder": "#d5c4a1",
        "tag_normal_bg": "transparent",
        "tag_border": "#665c54",
        "tag_hover": "#3c3836",
        "tag_pressed": "#504945",
    },
    "dark": {
        "accent": "#7a7a7a",
        "accent_soft": "#9c9c9c",
        "label_color": "#f0f0f0",
        "support_text_color": "#c2c2c2",
        "indicator_text_color": "#c2c2c2",
        "summary_text_color": "#f0f0f0",
        "panel_bg": "#2a2a2a",
        "panel_text": "#f0f0f0",
        "panel_border": "#4d4d4d",
        "summary_frame_bg": "#2a2a2a",
        "summary_frame_border": "#4d4d4d",
        "input_bg": "#2b2b2b",
        "input_text": "#f0f0f0",
        "input_border": "#4d4d4d",
        "input_border_focus": "#4a90e2",
        "input_placeholder": "#b0b0b0",
        "tag_normal_bg": "transparent",
        "tag_border": "#4d4d4d",
        "tag_hover": "#333333",
        "tag_pressed": "#3f3f3f",
    },
    "dracula": {
        "accent": "#bd93f9",
        "accent_soft": "#c7b3ff",
        "label_color": "#f8f8f2",
        "support_text_color": "#bcb0ff",
        "indicator_text_color": "#bcb0ff",
        "summary_text_color": "#f8f8f2",
        "panel_bg": "#303446",
        "panel_text": "#f8f8f2",
        "panel_border": "#6272a4",
        "summary_frame_bg": "#303446",
        "summary_frame_border": "#6272a4",
        "input_bg": "#303446",
        "input_text": "#f8f8f2",
        "input_border": "#6272a4",
        "input_border_focus": "#bd93f9",
        "input_placeholder": "#9ea3d1",
        "tag_normal_bg": "transparent",
        "tag_border": "#6272a4",
        "tag_hover": "#303446",
        "tag_pressed": "#303446",
    },
    "solarized-dark": {
        "accent": "#268bd2",
        "accent_soft": "#93a1a1",
        "label_color": "#eee8d5",
        "support_text_color": "#93a1a1",
        "indicator_text_color": "#93a1a1",
        "summary_text_color": "#eee8d5",
        "panel_bg": "#002b36",
        "panel_text": "#eee8d5",
        "panel_border": "#586e75",
        "summary_frame_bg": "#002b36",
        "summary_frame_border": "#586e75",
        "input_bg": "#073642",
        "input_text": "#eee8d5",
        "input_border": "#586e75",
        "input_border_focus": "#2aa198",
        "input_placeholder": "#839496",
        "tag_normal_bg": "transparent",
        "tag_border": "#586e75",
        "tag_hover": "#002b36",
        "tag_pressed": "#002b36",
    },
    "solarized-light": {
        "accent": "#268bd2",
        "accent_soft": "#859900",
        "label_color": "#586e75",
        "support_text_color": "#657b83",
        "indicator_text_color": "#586e75",
        "summary_text_color": "#586e75",
        "panel_bg": "#fdf6e3",
        "panel_text": "#586e75",
        "panel_border": "#d9d1be",
        "summary_frame_bg": "#fdf6e3",
        "summary_frame_border": "#d9d1be",
        "input_bg": "#f5ecd3",
        "input_text": "#586e75",
        "input_border": "#d9d1be",
        "input_border_focus": "#268bd2",
        "input_placeholder": "#7a8a8a",
        "tag_normal_bg": "transparent",
        "tag_border": "#909090",
        "tag_hover": "#f0f7ff",
        "tag_pressed": "#d9ecff",
    },
    "mint-light": {
        "accent": "#2f8f83",
        "accent_soft": "#6fc5b6",
        "label_color": "#233138",
        "support_text_color": "#4b5b61",
        "indicator_text_color": "#354248",
        "summary_text_color": "#233138",
        "panel_bg": "#eef6f4",
        "panel_text": "#233138",
        "panel_border": "#d4e5e1",
        "summary_frame_bg": "#e6f1ef",
        "summary_frame_border": "#d4e5e1",
        "input_bg": "#ffffff",
        "input_text": "#233138",
        "input_border": "#d4e5e1",
        "input_border_focus": "#2f8f83",
        "input_placeholder": "#6a7a80",
        "tag_normal_bg": "transparent",
        "tag_border": "#c6dad5",
        "tag_hover": "#f3faf8",
        "tag_pressed": "#e6f1ef",
    },
    "paper": {
        "accent": "#c07a3a",
        "accent_soft": "#d7b08a",
        "label_color": "#3b3a36",
        "support_text_color": "#6f6559",
        "indicator_text_color": "#5a5248",
        "summary_text_color": "#3b3a36",
        "panel_bg": "#f5f2e9",
        "panel_text": "#3b3a36",
        "panel_border": "#e0d7c7",
        "summary_frame_bg": "#efe9dc",
        "summary_frame_border": "#e0d7c7",
        "input_bg": "#ffffff",
        "input_text": "#3b3a36",
        "input_border": "#e0d7c7",
        "input_border_focus": "#c07a3a",
        "input_placeholder": "#8a8073",
        "tag_normal_bg": "transparent",
        "tag_border": "#d6ccb8",
        "tag_hover": "#f0e8da",
        "tag_pressed": "#e6dccb",
    },
    "tokyo-night": {
        "accent": "#7aa2f7",
        "accent_soft": "#9fb4ff",
        "label_color": "#c0caf5",
        "support_text_color": "#9aa5d0",
        "indicator_text_color": "#9aa5d0",
        "summary_text_color": "#c0caf5",
        "panel_bg": "#1f2335",
        "panel_text": "#c0caf5",
        "panel_border": "#394260",
        "summary_frame_bg": "#1f2335",
        "summary_frame_border": "#394260",
        "input_bg": "#1f2335",
        "input_text": "#c0caf5",
        "input_border": "#394260",
        "input_border_focus": "#7aa2f7",
        "input_placeholder": "#6d7595",
        "tag_normal_bg": "transparent",
        "tag_border": "#394260",
        "tag_hover": "#1f2335",
        "tag_pressed": "#1f2335",
    },
    "catppuccin": {
        "accent": "#cba6f7",
        "accent_soft": "#f2d0ff",
        "label_color": "#f2cdcd",
        "support_text_color": "#e8d7ff",
        "indicator_text_color": "#e8d7ff",
        "summary_text_color": "#f5e0dc",
        "panel_bg": "#1e1e2e",
        "panel_text": "#f5e0dc",
        "panel_border": "#585b70",
        "summary_frame_bg": "#1e1e2e",
        "summary_frame_border": "#585b70",
        "input_bg": "#1e1e2e",
        "input_text": "#f5e0dc",
        "input_border": "#45475a",
        "input_border_focus": "#cba6f7",
        "input_placeholder": "#a6adc8",
        "tag_normal_bg": "transparent",
        "tag_border": "#45475a",
        "tag_hover": "#1e1e2e",
        "tag_pressed": "#1e1e2e",
    },
    "nord": {
        "accent": "#88c0d0",
        "accent_soft": "#81a1c1",
        "label_color": "#e5e9f0",
        "support_text_color": "#d8dee9",
        "indicator_text_color": "#c1d0e0",
        "summary_text_color": "#e5e9f0",
        "panel_bg": "#2e3440",
        "panel_text": "#e5e9f0",
        "panel_border": "#4c566a",
        "summary_frame_bg": "#303747",
        "summary_frame_border": "#4c566a",
        "input_bg": "#3b4252",
        "input_text": "#e5e9f0",
        "input_border": "#4c566a",
        "input_border_focus": "#88c0d0",
        "input_placeholder": "#8b9bb1",
        "tag_normal_bg": "transparent",
        "tag_border": "#4c566a",
        "tag_hover": "#3b4252",
        "tag_pressed": "#3b4252",
    },
}

# Tema padrao usado como fallback quando roles especificos nao estao definidos
THEME_ROLES_DEFAULT = {
    "accent": "#4a90e2",
    "accent_soft": "#9ec5ff",
    "label_color": "#e0e0e0",
    "support_text_color": "#c8c8c8",
    "indicator_text_color": "#c8c8c8",
    "summary_text_color": "#e0e0e0",
    "panel_bg": "#2a2a2a",
    "panel_text": "#e0e0e0",
    "panel_border": "#555555",
    "summary_frame_bg": "#2a2a2a",
    "summary_frame_border": "#555555",
    "input_bg": "#2b2b2b",
    "input_text": "#e0e0e0",
    "input_border": "#555555",
    "input_border_focus": "#4a90e2",
    "input_placeholder": "#aaaaaa",
    "popup_bg": "#2a2a2a",
    "popup_text": "#e0e0e0",
    "popup_border": "#555555",
    "popup_header_text": "#e0e0e0",
    "checkbox_border": "#6b6b6b",
    "checkbox_bg": "#2a2a2a",
    "checkbox_checked_bg": "#4a90e2",
    "checkbox_checked_fg": "#ffffff",
    "tag_normal_bg": "transparent",
    "tag_border": "#6b6b6b",
    "tag_hover": "#2a2a2a",
    "tag_pressed": "#3a3a3a",
}


def get_theme_roles(name: str) -> dict[str, str]:
    """
    Retorna os roles (papeis) de cores para um tema especifico.

    Args:
        name: Nome do tema (ex: 'dark', 'gruvbox', 'dracula')

    Returns:
        Dicionario com os roles de cores, usando THEME_ROLES_DEFAULT
        como base e sobrescrevendo com roles especificos do tema.
    """
    normalized = normalize_theme(name)
    roles = THEME_ROLES_DEFAULT.copy()
    specific = THEME_ROLES.get(normalized)
    if specific:
        roles.update(specific)
    # Keep popup/checkbox colors coherent with the active theme.
    # Avoid a fixed dark popup fallback when the selected theme is light.
    if not specific or "popup_bg" not in specific:
        roles["popup_bg"] = (
            roles.get("input_bg") or roles.get("panel_bg") or roles["popup_bg"]
        )
    if not specific or "popup_text" not in specific:
        roles["popup_text"] = (
            roles.get("input_text") or roles.get("panel_text") or roles["popup_text"]
        )
    if not specific or "popup_border" not in specific:
        roles["popup_border"] = (
            roles.get("input_border")
            or roles.get("panel_border")
            or roles["popup_border"]
        )
    if not specific or "popup_header_text" not in specific:
        roles["popup_header_text"] = (
            roles.get("popup_text")
            or roles.get("panel_text")
            or roles["popup_header_text"]
        )
    if not specific or "checkbox_border" not in specific:
        roles["checkbox_border"] = (
            roles.get("input_border")
            or roles.get("panel_border")
            or roles["checkbox_border"]
        )
    if not specific or "checkbox_bg" not in specific:
        roles["checkbox_bg"] = (
            roles.get("popup_bg") or roles.get("input_bg") or roles["checkbox_bg"]
        )
    if not specific or "checkbox_checked_bg" not in specific:
        roles["checkbox_checked_bg"] = (
            roles.get("accent") or roles["checkbox_checked_bg"]
        )
    if not specific or "checkbox_checked_fg" not in specific:
        roles["checkbox_checked_fg"] = "#ffffff"
    return roles


def get_palette(name: str) -> QPalette:
    """
    Cria uma paleta QPalette completa para um tema especifico.

    Args:
        name: Nome do tema (ex: 'dark', 'grayscale', 'tokyo-night')

    Returns:
        QPalette configurada com as cores do tema selecionado.
        Usa tema 'dark' como fallback se o tema nao for encontrado.
    """
    key = normalize_theme(name)
    pal = QPalette()

    if key in {"grayscale", "escala de cinza", "escala_de_cinza"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#2b2e33"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#2f3238"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#31343a"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#3a3d44"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#3a3d44"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#e6e6e6"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1c1c1c"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#cfd3d6"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#b5bcc4"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9aa0aa"))
        return pal

    if key in {"windows7", "win7"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#eef4ff"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f8fbff"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1b1b1b"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1b1b1b"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#e3ecff"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1b1b1b"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#fffff7"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#1b1b1b"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#2b6cc0"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#2b6cc0"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#4b76c2"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#5d6f89"))
        return pal

    if key in {"classico"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#f7f6f5"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0efed"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#dfe2e4"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#fefefe"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#3584e4"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#3584e4"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#5a96e9"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6d7173"))
        return pal

    if key in {"gruvbox", "vim", "vim-dark"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#282828"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#1d2021"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#32302f"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#ebdbb2"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#ebdbb2"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#3c3836"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#ebdbb2"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#3c3836"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#ebdbb2"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#d79921"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#282828"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#83a598"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#b16286"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#bdae93"))
        return pal
    # Dracula
    if key in {"dracula"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#282a36"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#1e1f29"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#303241"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#f8f8f2"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#f8f8f2"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#44475a"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#f8f8f2"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#44475a"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#f8f8f2"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#bd93f9"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#282a36"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#bd93f9"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#ff79c6"))
        return pal

    # Solarized Dark
    if key in {"solarized-dark", "solarized dark"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#002b36"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#073642"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#003845"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#93a1a1"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#93a1a1"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#073642"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#93a1a1"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#268bd2"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#002b36"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#2aa198"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#6c71c4"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#657b83"))
        return pal

    # Solarized Light
    if key in {"solarized-light", "solarized light"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#fdf6e3"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#f3ebd6"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f8f1da"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#586e75"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#586e75"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#e7dfc6"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#586e75"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#268bd2"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#fdf6e3"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#268bd2"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#859900"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#7a8a8a"))
        return pal

    # Mint Light
    if key in {"mint-light", "mint light", "mintlight"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#eef6f4"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#e6f1ef"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#233138"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#233138"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#e6f1ef"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#233138"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#2f8f83"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#eef6f4"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#2f8f83"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#6fc5b6"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6a7a80"))
        return pal

    # Paper
    if key in {"paper"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#f5f2e9"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#efe9dc"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#3b3a36"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#3b3a36"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#efe9dc"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#3b3a36"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#c07a3a"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#b36b2f"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#d7b08a"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8a8073"))
        return pal

    # Tokyo Night
    if key in {"tokyo-night", "tokyonight", "tokyo night"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#1a1b26"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#16161e"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1f2335"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#c0caf5"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#c0caf5"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#1f2335"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#c0caf5"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#7aa2f7"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#16161e"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#9fb4ff"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#9aa5d0"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6d7595"))
        return pal

    # Catppuccin Mocha
    if key in {"catppuccin", "catppuccin-mocha", "catppuccin mocha"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#181825"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#313244"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#cdd6f4"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#cdd6f4"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#313244"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#cdd6f4"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#cba6f7"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1e1e2e"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#cba6f7"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#f2d0ff"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9399b2"))
        return pal

    # Nord
    if key in {"nord"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#2e3440"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#3b4252"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#434c5e"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#e5e9f0"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#e5e9f0"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#3b4252"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e5e9f0"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#88c0d0"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#2e3440"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#88c0d0"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#81a1c1"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8b9bb1"))
        return pal

    # dark padr?o (fallback)
    pal.setColor(QPalette.ColorRole.Window, QColor("#121212"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#252525"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#2a2a2a"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#5a5a5a"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#f0f0f0"))
    pal.setColor(QPalette.ColorRole.Link, QColor("#7a7a7a"))
    pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#9c9c9c"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9e9e9e"))
    return pal


def normalize_theme(name: str) -> str:
    """
    Normaliza nomes de temas para suas formas canonicas.

    Permite aliases e variacoes de nomes (ex: 'win7' -> 'windows7',
    'escala de cinza' -> 'grayscale').

    Args:
        name: Nome do tema (pode ser alias ou variacao)

    Returns:
        Nome canonico do tema, ou 'dark' se nao reconhecido.
    """
    name = (name or "dark").lower()
    if name in ("grayscale", "escala de cinza", "escala_de_cinza"):
        return "grayscale"
    if name in ("windows7", "win7", "windows 7"):
        return "windows7"
    if name in ("classico", "claro", "gnome", "adwaita"):
        return "classico"
    if name in ("gruvbox", "vim", "vim-dark", "vim dark", "vim hard"):
        return "gruvbox"
    if name in ("dracula",):
        return "dracula"
    if name in ("solarized-dark", "solarized dark"):
        return "solarized-dark"
    if name in ("solarized-light", "solarized light"):
        return "solarized-light"
    if name in ("mint-light", "mint light", "mintlight"):
        return "mint-light"
    if name in ("paper",):
        return "paper"
    if name in ("tokyo-night", "tokyonight", "tokyo night"):
        return "tokyo-night"
    if name in ("catppuccin", "catppuccin-mocha", "catppuccin mocha"):
        return "catppuccin"
    if name in ("nord",):
        return "nord"
    return "dark"
