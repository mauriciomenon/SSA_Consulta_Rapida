#!/usr/bin/env python3
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication
from gui.gui_ssa import SSAMainWindow

def main():
    app = QApplication(sys.argv)
    w = SSAMainWindow()
    w.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())

