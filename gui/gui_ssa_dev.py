"""
# ==============================================================================
# DEV TOOL - KEEP AS ACTIVE DEVELOPMENT UTILITY
# ==============================================================================
# Status: Active development tool for API testing
# Purpose: Test Itaipu API without affecting production GUI
# Last modified: 2025-10-29T12:05:00 (documented purpose)
#
# Dev-only minimal GUI to fetch SSAs from Itaipu API without touching existing GUI.
#
# Features:
# - QThread-based worker wrapping utils.remote_itaipu.fetch_pending_ssas
# - Timeout, SSL verify toggle, cancel support
# - Simple preview table and JSON tab
#
# Run: python -m gui.gui_ssa_dev
"""
# ruff: noqa: E402

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6 import QtCore, QtWidgets  # noqa: E402

from utils.remote_itaipu import RequestOptions  # noqa: E402
from utils.remote_itaipu import fetch_pending_ssas, map_to_dataframe, to_json_pretty


class FetchWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(object)  # payload: list[dict] | Exception
    cancelled = QtCore.pyqtSignal()

    def __init__(self, start: str, end: str, years: int, opts: RequestOptions):
        super().__init__()
        self._start = start
        self._end = end
        self._years = years
        self._opts = opts
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            self.progress.emit(5)
            items = fetch_pending_ssas(
                start=self._start,
                end=self._end,
                years=self._years,
                opts=self._opts,
                cancel_flag=self._cancel,
            )
            self.progress.emit(95)
            self.finished.emit(items)
        except Exception as e:  # noqa: BLE001
            if self._cancel.is_set():
                self.cancelled.emit()
            else:
                self.finished.emit(e)
        finally:
            self.progress.emit(100)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SSA Dev (Itaipu)")
        self.resize(1000, 700)

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        form = QtWidgets.QHBoxLayout()
        self.start_edit = QtWidgets.QLineEdit("A000A000")
        self.end_edit = QtWidgets.QLineEdit("Z999Z999")
        self.years_spin = QtWidgets.QSpinBox()
        self.years_spin.setRange(1, 100000)
        self.years_spin.setValue(100000)
        self.timeout_spin = QtWidgets.QDoubleSpinBox()
        self.timeout_spin.setRange(1.0, 120.0)
        self.timeout_spin.setValue(30.0)
        self.ssl_check = QtWidgets.QCheckBox("Verify SSL")
        self.ssl_check.setChecked(True)

        form.addWidget(QtWidgets.QLabel("Start"))
        form.addWidget(self.start_edit)
        form.addWidget(QtWidgets.QLabel("End"))
        form.addWidget(self.end_edit)
        form.addWidget(QtWidgets.QLabel("Years"))
        form.addWidget(self.years_spin)
        form.addWidget(QtWidgets.QLabel("Timeout"))
        form.addWidget(self.timeout_spin)
        form.addWidget(self.ssl_check)
        layout.addLayout(form)

        btns = QtWidgets.QHBoxLayout()
        self.fetch_btn = QtWidgets.QPushButton("Fetch")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        btns.addWidget(self.fetch_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.tabs = QtWidgets.QTabWidget()
        # Table tab
        self.table = QtWidgets.QTableWidget(0, 0)
        self.tabs.addTab(self.table, "Table")
        # JSON tab
        self.json_edit = QtWidgets.QPlainTextEdit()
        self.json_edit.setReadOnly(True)
        self.tabs.addTab(self.json_edit, "JSON")
        layout.addWidget(self.tabs)

        status_bar = self.statusBar()
        if not isinstance(status_bar, QtWidgets.QStatusBar):
            status_bar = QtWidgets.QStatusBar(self)
            self.setStatusBar(status_bar)
        self.status = status_bar
        self._thr: Optional[QtCore.QThread] = None
        self.worker: Optional[FetchWorker] = None

        self.fetch_btn.clicked.connect(self._on_fetch)
        self.cancel_btn.clicked.connect(self._on_cancel)

    def _on_fetch(self) -> None:
        if self._thr is not None:
            return
        start = self.start_edit.text().strip() or "A000A000"
        end = self.end_edit.text().strip() or "Z999Z999"
        years = int(self.years_spin.value())
        opts = RequestOptions(
            timeout=float(self.timeout_spin.value()),
            verify_ssl=self.ssl_check.isChecked(),
        )
        self.progress.setValue(0)
        self.status.showMessage("Fetching...")
        self.fetch_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self._thr = QtCore.QThread(self)
        self.worker = FetchWorker(start, end, years, opts)
        self.worker.moveToThread(self._thr)
        self._thr.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_finished)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.finished.connect(self._cleanup_thread)
        self.worker.cancelled.connect(self._cleanup_thread)
        self._thr.start()

    def _on_cancel(self) -> None:
        if self.worker is not None:
            self.worker.request_cancel()
            self.status.showMessage("Cancelling...")

    def _cleanup_thread(self) -> None:
        self.cancel_btn.setEnabled(False)
        self.fetch_btn.setEnabled(True)
        if self._thr is not None:
            self._thr.quit()
            self._thr.wait(2000)
            self._thr = None
        self.worker = None
        self.status.clearMessage()

    def _on_cancelled(self) -> None:
        self.status.showMessage("Cancelled")

    def _on_finished(self, payload: object) -> None:
        if isinstance(payload, Exception):
            self.json_edit.setPlainText(str(payload))
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        items: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            items = [
                cast(Dict[str, Any], item) for item in payload if isinstance(item, dict)
            ]
        self.json_edit.setPlainText(to_json_pretty(items))
        df = map_to_dataframe(items)
        if df is None:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        if df.empty:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        # populate table with a preview (first 200 rows)
        preview = df.head(200)
        self.table.setRowCount(len(preview))
        self.table.setColumnCount(len(preview.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in preview.columns])
        for r in range(len(preview)):
            for c, col in enumerate(preview.columns):
                val = preview.iloc[r][col]
                item = QtWidgets.QTableWidgetItem("" if val is None else str(val))
                self.table.setItem(r, c, item)


def main() -> None:
    import sys

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
