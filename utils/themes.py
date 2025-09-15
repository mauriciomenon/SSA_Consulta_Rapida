from PyQt6.QtGui import QPalette, QColor


def get_palette(name: str) -> QPalette:
    name = (name or "dark").lower()
    pal = QPalette()

    if name == "light":
        # Tema claro mais suave e profissional
        pal.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))          # Fundo principal mais suave
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))            # Fundo de campos
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f5f5f5"))   # Linhas alternadas
        pal.setColor(QPalette.ColorRole.Text, QColor("#2c2c2c"))            # Texto principal
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#2c2c2c"))      # Texto de janela
        pal.setColor(QPalette.ColorRole.Button, QColor("#e8e8e8"))          # Botoes
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#2c2c2c"))      # Texto dos botoes
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#fff3cd"))     # Tooltip fundo
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#856404"))     # Tooltip texto
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#0066cc"))       # Selecao
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff")) # Texto selecionado
        return pal

    if name in ("gruvbox", "vim", "vim-dark"):
        pal.setColor(QPalette.ColorRole.Window, QColor("#1d2021"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#282828"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#ebdbb2"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#3c3836"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#ebdbb2"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#d79921"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#282828"))
        return pal

    # dark padrao (fallback)
    pal.setColor(QPalette.ColorRole.Window, QColor("#121212"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#2a2a2a"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e0e0e0"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#4a90e2"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1e1e1e"))
    return pal


def normalize_theme(name: str) -> str:
    name = (name or "dark").lower()
    if name in ("light", "claro"):
        return "light"
    if name in ("gruvbox", "vim", "vim-dark", "vim dark", "vim hard"):
        return "gruvbox"
    return "dark"
