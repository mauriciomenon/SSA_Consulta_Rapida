from PyQt6.QtGui import QPalette, QColor

THEME_ROLES: dict[str, dict[str, str]] = {
    "grayscale": {
        "accent": "#0a84ff",
        "accent_soft": "#4b5563",
        "input_bg": "#ffffff",
        "input_text": "#1c1c1c",
        "input_border": "#c7c9cc",
        "input_border_focus": "#0a84ff",
        "input_placeholder": "#6e6e6e",
        "label_color": "#1c1c1c",
        "support_text_color": "#4b5563",
        "panel_bg": "#ffffff",
        "panel_text": "#1c1c1c",
        "panel_border": "#d7d9db",
    },
    "windows7": {
        "accent": "#2b6cc0",
        "accent_soft": "#4b76c2",
        "input_bg": "#ffffff",
        "input_text": "#1a1a1a",
        "input_border": "#c2d6f6",
        "input_border_focus": "#2b6cc0",
        "input_placeholder": "#5d6f89",
        "label_color": "#1a1a1a",
        "support_text_color": "#3c4a6f",
        "panel_bg": "#f8fbff",
        "panel_text": "#1a1a1a",
        "panel_border": "#d8e5fb",
    },
    "gnome": {
        "accent": "#3584e4",
        "accent_soft": "#5a96e9",
        "input_bg": "#fdfdfd",
        "input_text": "#2e3436",
        "input_border": "#c9cdce",
        "input_border_focus": "#3584e4",
        "input_placeholder": "#6d7173",
        "label_color": "#2e3436",
        "support_text_color": "#4c5153",
        "panel_bg": "#f6f5f4",
        "panel_text": "#2e3436",
        "panel_border": "#d7d4d1",
    },
    "gruvbox": {
        "accent": "#fabd2f",
        "accent_soft": "#ebdbb2",
        "input_bg": "#3c3836",
        "input_text": "#ebdbb2",
        "input_border": "#665c54",
        "input_border_focus": "#fabd2f",
        "input_placeholder": "#d5c4a1",
        "label_color": "#fabd2f",
        "support_text_color": "#d5c4a1",
        "panel_bg": "#3c3836",
        "panel_text": "#ebdbb2",
        "panel_border": "#665c54",
    },
    "dark": {
        "accent": "#4a90e2",
        "accent_soft": "#9ec5ff",
        "input_bg": "#2b2b2b",
        "input_text": "#f0f0f0",
        "input_border": "#4d4d4d",
        "input_border_focus": "#4a90e2",
        "input_placeholder": "#b0b0b0",
        "label_color": "#f0f0f0",
        "support_text_color": "#c2c2c2",
        "panel_bg": "#2a2a2a",
        "panel_text": "#f0f0f0",
        "panel_border": "#4d4d4d",
    },
    "kde": {
        "accent": "#3daee9",
        "accent_soft": "#8fd0ff",
        "input_bg": "#2f343f",
        "input_text": "#eff0f1",
        "input_border": "#3f4754",
        "input_border_focus": "#3daee9",
        "input_placeholder": "#8fa1b3",
        "label_color": "#eff0f1",
        "support_text_color": "#b8c6d0",
        "panel_bg": "#31363b",
        "panel_text": "#eff0f1",
        "panel_border": "#3daee9",
    },
    "one-dark": {
        "accent": "#61afef",
        "accent_soft": "#98c379",
        "input_bg": "#2c313a",
        "input_text": "#abb2bf",
        "input_border": "#3e4451",
        "input_border_focus": "#61afef",
        "input_placeholder": "#5c6370",
        "label_color": "#abb2bf",
        "support_text_color": "#98c379",
        "panel_bg": "#2c313a",
        "panel_text": "#abb2bf",
        "panel_border": "#3e4451",
    },
    "dracula": {
        "accent": "#bd93f9",
        "accent_soft": "#8be9fd",
        "input_bg": "#303446",
        "input_text": "#f8f8f2",
        "input_border": "#6272a4",
        "input_border_focus": "#bd93f9",
        "input_placeholder": "#7082b6",
        "label_color": "#f8f8f2",
        "support_text_color": "#8be9fd",
        "panel_bg": "#303446",
        "panel_text": "#f8f8f2",
        "panel_border": "#6272a4",
    },
    "solarized-dark": {
        "accent": "#268bd2",
        "accent_soft": "#93a1a1",
        "input_bg": "#073642",
        "input_text": "#eee8d5",
        "input_border": "#586e75",
        "input_border_focus": "#2aa198",
        "input_placeholder": "#839496",
        "label_color": "#eee8d5",
        "support_text_color": "#93a1a1",
        "panel_bg": "#002b36",
        "panel_text": "#eee8d5",
        "panel_border": "#586e75",
    },
    "solarized-light": {
        "accent": "#268bd2",
        "accent_soft": "#859900",
        "input_bg": "#f5ecd3",
        "input_text": "#586e75",
        "input_border": "#d9d1be",
        "input_border_focus": "#268bd2",
        "input_placeholder": "#7a8a8a",
        "label_color": "#586e75",
        "support_text_color": "#657b83",
        "panel_bg": "#fdf6e3",
        "panel_text": "#586e75",
        "panel_border": "#d9d1be",
    },
    "tokyo-night": {
        "accent": "#7aa2f7",
        "accent_soft": "#7dcfff",
        "input_bg": "#1f2335",
        "input_text": "#c0caf5",
        "input_border": "#394260",
        "input_border_focus": "#7aa2f7",
        "input_placeholder": "#565f89",
        "label_color": "#c0caf5",
        "support_text_color": "#7dcfff",
        "panel_bg": "#1f2335",
        "panel_text": "#c0caf5",
        "panel_border": "#394260",
    },
    "catppuccin": {
        "accent": "#cba6f7",
        "accent_soft": "#f5c2e7",
        "input_bg": "#1e1e2e",
        "input_text": "#f5e0dc",
        "input_border": "#45475a",
        "input_border_focus": "#cba6f7",
        "input_placeholder": "#a6adc8",
        "label_color": "#f2cdcd",
        "support_text_color": "#f5c2e7",
        "panel_bg": "#1e1e2e",
        "panel_text": "#f5e0dc",
        "panel_border": "#585b70",
    },
}

THEME_ROLES_DEFAULT = {
    "accent": "#4a90e2",
    "accent_soft": "#d0d0d0",
    "input_bg": "#2b2b2b",
    "input_text": "#e0e0e0",
    "input_border": "#555555",
    "input_border_focus": "#888888",
    "input_placeholder": "#aaaaaa",
    "label_color": "#e0e0e0",
    "support_text_color": "#c8c8c8",
    "panel_bg": "#2a2a2a",
    "panel_text": "#e0e0e0",
    "panel_border": "#555555",
}


def get_theme_roles(name: str) -> dict[str, str]:
    normalized = normalize_theme(name)
    return THEME_ROLES.get(normalized, THEME_ROLES_DEFAULT).copy()


def get_palette(name: str) -> QPalette:
    key = (name or "dark").lower()
    pal = QPalette()

    if key in {"grayscale", "light", "escala de cinza", "escala_de_cinza"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#f2f2f2"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#e6e6e6"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1c1c1c"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1c1c1c"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#d9d9d9"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1c1c1c"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#fffcd6"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#202020"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#0a84ff"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#0a84ff"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#5c5ce0"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6e6e6e"))
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

    if key in {"kde", "plasma"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#31363b"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#232629"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#2f343f"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#eff0f1"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#eff0f1"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#3b4045"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#eff0f1"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#40464d"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#eff0f1"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#3daee9"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#232629"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#3daee9"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#a96eb7"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9fb2bf"))
        return pal

    if key in {"gnome", "adwaita"}:
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
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#d79921"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#282828"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#83a598"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#b16286"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#bdae93"))
        return pal

    # One Dark Pro
    if key in {"one-dark", "onedark", "one dark"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#282c34"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#1f2329"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#2c313c"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#abb2bf"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#abb2bf"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#2c313c"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#d7dae0"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2c313c"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#d7dae0"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#61afef"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1f2329"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#61afef"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#c678dd"))
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
        pal.setColor(QPalette.ColorRole.Link, QColor("#8be9fd"))
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
        pal.setColor(QPalette.ColorRole.Link, QColor("#7dcfff"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#bb9af7"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#565f89"))
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
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#89b4fa"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#181825"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#74c7ec"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#b4befe"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9399b2"))
        return pal

    # dark padrão (fallback)
    pal.setColor(QPalette.ColorRole.Window, QColor("#121212"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#252525"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#2a2a2a"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#4a90e2"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1e1e1e"))
    pal.setColor(QPalette.ColorRole.Link, QColor("#76baff"))
    pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#b58ae5"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9e9e9e"))
    return pal


def normalize_theme(name: str) -> str:
    name = (name or "dark").lower()
    if name in ("grayscale", "light", "claro", "escala de cinza", "escala_de_cinza"):
        return "grayscale"
    if name in ("windows7", "win7", "windows 7"):
        return "windows7"
    if name in ("kde", "plasma"):
        return "kde"
    if name in ("gnome", "adwaita"):
        return "gnome"
    if name in ("gruvbox", "vim", "vim-dark", "vim dark", "vim hard"):
        return "gruvbox"
    if name in ("one-dark", "onedark", "one dark"):
        return "one-dark"
    if name in ("dracula",):
        return "dracula"
    if name in ("solarized-dark", "solarized dark"):
        return "solarized-dark"
    if name in ("solarized-light", "solarized light"):
        return "solarized-light"
    if name in ("tokyo-night", "tokyonight", "tokyo night"):
        return "tokyo-night"
    if name in ("catppuccin", "catppuccin-mocha", "catppuccin mocha"):
        return "catppuccin"
    return "dark"



















