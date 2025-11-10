#!/usr/bin/env python
# Test script to isolate search input bug

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from gui.tabs import MainTab


class TestWindow(QMainWindow):
    """Minimal test window with only MainTab."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Clean Tab - Search Input Debug")
        self.resize(800, 600)

        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add main tab
        self.main_tab = MainTab(self)
        self.main_tab.search_requested.connect(self.on_search)
        self.tabs.addTab(self.main_tab, "Principal")

        print("[TestWindow] Initialized with clean MainTab")
        print("[TestWindow] No legacy code loaded")

    def on_search(self, text):
        """Handle search request."""
        print(f"[TestWindow] Search received: '{text}'")
        print(f"[TestWindow] Length: {len(text)}")
        print(f"[TestWindow] Repr: {text!r}")

        # Verify each character
        for i, char in enumerate(text):
            print(f"[TestWindow] Char {i}: '{char}' (Unicode: U+{ord(char):04X})")

        # If 'v' is missing, we'll see it here
        if 'svp' in text.lower():
            print("[TestWindow] ✓ Contains 'svp'")
        elif 'sp' in text.lower() and 'v' not in text.lower():
            print("[TestWindow] ✗ BUG: 'v' is missing!")
        else:
            print(f"[TestWindow] Search text: {text}")


if __name__ == '__main__':
    print("=" * 80)
    print("TESTE LIMPO - Sem codigo legado")
    print("Digite 'svp' no campo de busca e pressione Enter")
    print("Observe o console para verificar se o 'v' esta presente")
    print("=" * 80)

    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
