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
    return "dark"
