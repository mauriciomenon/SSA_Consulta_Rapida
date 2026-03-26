# gui/qt_stubs.py
# Shared Qt stubs for headless use.

from __future__ import annotations

from typing import TYPE_CHECKING, Any

QT_AVAILABLE = True
try:
    from PyQt6 import sip as _pyqt_sip
    from PyQt6.QtCore import QSignalBlocker, Qt, QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMenu,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QTableWidgetItem,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
        QWidgetAction,
    )

    sip: Any = _pyqt_sip
except ImportError:
    QT_AVAILABLE = False
    sip: Any = None

    class _StubSignal:
        def connect(self, *_args, **_kwargs):
            return None

    class _Stub:
        def __init__(self, *_args, **_kwargs):
            return None

        def __getattr__(self, _name):
            def _noop(*_args, **_kwargs):
                return None

            return _noop

    class QApplication(_Stub):
        @staticmethod
        def primaryScreen():
            return None

    class QWidget(_Stub):
        def findChildren(self, *_args, **_kwargs):
            return []

    class QGroupBox(QWidget):
        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self._title = _args[0] if _args else ""

        def title(self):
            return self._title

    class QHBoxLayout(_Stub):
        def addWidget(self, *_args, **_kwargs):
            return None

        def addLayout(self, *_args, **_kwargs):
            return None

        def addStretch(self, *_args, **_kwargs):
            return None

        def addSpacing(self, *_args, **_kwargs):
            return None

    class QVBoxLayout(QHBoxLayout):
        pass

    class QGridLayout(QHBoxLayout):
        def count(self):
            return 0

        def takeAt(self, *_args, **_kwargs):
            return None

        def setColumnStretch(self, *_args, **_kwargs):
            return None

    class QToolButton(QWidget):
        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self.clicked = _StubSignal()

    class QMenu(QWidget):
        def addAction(self, *_args, **_kwargs):
            return None

        def exec(self, *_args, **_kwargs):
            return None

    class QCheckBox(QWidget):
        def __init__(self, text="", *_args, **_kwargs):
            super().__init__()
            self._checked = False
            self._text = text or ""
            self._props = {}
            self.toggled = _StubSignal()

        def isChecked(self):
            return bool(self._checked)

        def setChecked(self, value):
            self._checked = bool(value)

        def text(self):
            return self._text

        def setText(self, value):
            self._text = "" if value is None else str(value)

        def setProperty(self, key, value):
            self._props[key] = value

        def property(self, key):
            return self._props.get(key)

    class QComboBox(QWidget):
        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self.currentIndexChanged = _StubSignal()

        def addItem(self, *_args, **_kwargs):
            return None

        def itemData(self, *_args, **_kwargs):
            return None

        def currentData(self, *_args, **_kwargs):
            return None

    class QLabel(QWidget):
        pass

    class QScrollArea(QWidget):
        def setWidget(self, *_args, **_kwargs):
            return None

        def setWidgetResizable(self, *_args, **_kwargs):
            return None

    class QFrame(QWidget):
        class Shape:
            HLine = 0

        class Shadow:
            Sunken = 0

        def setFrameShape(self, *_args, **_kwargs):
            return None

        def setFrameShadow(self, *_args, **_kwargs):
            return None

    class QWidgetAction(_Stub):
        def setDefaultWidget(self, *_args, **_kwargs):
            return None

    class QPushButton(QWidget):
        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self.clicked = _StubSignal()

    class QLineEdit(QWidget):
        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self._text = ""

        def text(self):
            return self._text

        def setText(self, value):
            self._text = "" if value is None else str(value)

    class QTextEdit(QWidget):
        def setPlainText(self, *_args, **_kwargs):
            return None

        def setReadOnly(self, *_args, **_kwargs):
            return None

    class QDialog(QWidget):
        def exec(self):
            return None

    class QDialogButtonBox(QWidget):
        class StandardButton:
            Close = 0

        def __init__(self, *_args, **_kwargs):
            super().__init__()
            self.rejected = _StubSignal()

    class QSizePolicy:
        class Policy:
            Expanding = 0
            Fixed = 0
            Maximum = 0

    class Qt:
        class AlignmentFlag:
            AlignTop = 0
            AlignHCenter = 0
            AlignVCenter = 0
            AlignLeft = 0

        class ScrollBarPolicy:
            ScrollBarAlwaysOff = 0

        class ItemDataRole:
            UserRole = 0

    class QSignalBlocker:
        def __init__(self, *_args, **_kwargs):
            return None

    class QHeaderView:
        class ResizeMode:
            Fixed = 0
            Interactive = 0

    class QTableWidgetItem:
        def __init__(self, *_args, **_kwargs):
            return None

        def setTextAlignment(self, *_args, **_kwargs):
            return None

        def setData(self, *_args, **_kwargs):
            return None

    class QTimer:
        @staticmethod
        def singleShot(*_args, **_kwargs):
            return None


if TYPE_CHECKING:
    sip: Any
    Qt: Any
    QSignalBlocker: Any
    QTimer: Any
    QApplication: Any
    QComboBox: Any
    QCheckBox: Any
    QDialog: Any
    QDialogButtonBox: Any
    QFrame: Any
    QGridLayout: Any
    QGroupBox: Any
    QHBoxLayout: Any
    QLabel: Any
    QLineEdit: Any
    QMenu: Any
    QPushButton: Any
    QScrollArea: Any
    QSizePolicy: Any
    QTextEdit: Any
    QToolButton: Any
    QVBoxLayout: Any
    QWidget: Any
    QWidgetAction: Any
    QHeaderView: Any
    QTableWidgetItem: Any
