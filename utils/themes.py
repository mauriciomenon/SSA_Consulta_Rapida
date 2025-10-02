from PyQt6.QtGui import QPalette, QColor


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
        return pal

    if key in {"windows7", "win7"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f7f7"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1b1b1b"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1b1b1b"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#e1e1e1"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1b1b1b"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffe1"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#4a8cf7"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#1a5fb4"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#5a3b96"))
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
        return pal

    if key in {"gnome", "adwaita"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#f6f5f4"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#eceae8"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#d4d4d4"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffe1"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#2e3436"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#3584e4"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#1c64f2"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#5c3566"))
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
        return pal

    # Solarized Light
    if key in {"solarized-light", "solarized light"}:
        pal.setColor(QPalette.ColorRole.Window, QColor("#fdf6e3"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#eee8d5"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f5efdb"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#586e75"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#586e75"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#e6dfc9"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#586e75"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#268bd2"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#fdf6e3"))
        pal.setColor(QPalette.ColorRole.Link, QColor("#2aa198"))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor("#6c71c4"))
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
