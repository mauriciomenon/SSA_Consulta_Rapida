"""Headless Qt stubs used when PyQt6 is unavailable."""

from __future__ import annotations

from typing import Any, cast

sip = cast(Any, None)
PYQT_VERSION_STR = "indisponivel"
QT_VERSION_STR = "indisponivel"
DataLoaderWorker = cast(Any, None)
FilterWorker = cast(Any, None)
ColumnFilterDialog = cast(Any, None)
ColumnSelector = cast(Any, None)
FilterCache = cast(Any, None)

# Stubs manimos para permitir import em ambiente CI sem libs graficas
class _Sig:
    def emit(self, *a, **k):
        pass

    def connect(self, *a, **k):
        pass

def pyqtSignal(*a, **k):
    return _Sig()

class QWidget:
    def findChildren(self, *a, **k):
        return []

    def __getattr__(self, _name):
        def _noop(*_args, **_kwargs):
            return None

        return _noop

class QMainWindow(QWidget):
    pass

class QFont:
    def __init__(self, *a, **k):
        self._point_size = 10.0

    def setPointSizeF(self, size):
        self._point_size = size

    def pointSizeF(self):
        return self._point_size

    def setWeight(self, *a, **k):
        pass

    def setBold(self, *a, **k):
        pass

class QApplication:
    def __init__(self, *a, **k):
        pass

    def exec(self):
        return 0

    @staticmethod
    def processEvents(*a, **k):
        return None

    @staticmethod
    def clipboard():
        class _Clipboard:
            def setText(self, *a, **k):
                pass

        return _Clipboard()

class QVBoxLayout:
    def __init__(self, *a, **k):
        pass

    def addWidget(self, *a, **k):
        pass

    def addLayout(self, *a, **k):
        pass

    def addStretch(self, *a, **k):
        pass

    def addSpacing(self, *a, **k):
        pass

    def setSpacing(self, *a, **k):
        pass

    def setContentsMargins(self, *a, **k):
        pass

class QHBoxLayout(QVBoxLayout):
    def addItem(self, *a, **k):
        pass

class QGridLayout(QVBoxLayout):
    pass

class QSplitter(QWidget):
    def __init__(self, *a, **k):
        self.splitterMoved = _Sig()

    def addWidget(self, *a, **k):
        pass

    def setChildrenCollapsible(self, *a, **k):
        pass

    def setHandleWidth(self, *a, **k):
        pass

    def setStretchFactor(self, *a, **k):
        pass

    def setSizes(self, *a, **k):
        pass

    def sizes(self):
        return [1, 1]

class QTabWidget(QWidget):
    def __init__(self, *a, **k):
        self.currentChanged = _Sig()

    def addTab(self, *a, **k):
        pass

    def setStyleSheet(self, *a, **k):
        pass

class QTabBar(QWidget):
    def __init__(self, *a, **k):
        self.currentChanged = _Sig()

    def addTab(self, *a, **k):
        return 0

    def setCurrentIndex(self, *a, **k):
        pass

class QStackedWidget(QWidget):
    def addWidget(self, *a, **k):
        pass

    def setCurrentIndex(self, *a, **k):
        pass

class QLabel(QWidget):
    def __init__(self, *a, **k):
        pass

class QPushButton(QWidget):
    def __init__(self, *a, **k):
        self.clicked = _Sig()
        self.toggled = _Sig()
        self._text = a[0] if a else ""
        self._checkable = False
        self._checked = False

    def setToolTip(self, *a, **k):
        pass

    def setEnabled(self, *a, **k):
        pass

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setCheckable(self, enabled):
        self._checkable = bool(enabled)

    def setChecked(self, val):
        self._checked = bool(val)

    def isChecked(self):
        return self._checked

    def setStyleSheet(self, *a, **k):
        pass

    def setMaximumWidth(self, *a, **k):
        pass

class QLineEdit(QWidget):
    def __init__(self, *a, **k):
        self._text = ""
        self.returnPressed = _Sig()
        self.textChanged = _Sig()

    def text(self):
        return self._text

    def setText(self, value):
        self._text = "" if value is None else str(value)

    def clear(self):
        self._text = ""

    def setPlaceholderText(self, *a, **k):
        pass

    def setToolTip(self, *a, **k):
        pass

    def setMinimumWidth(self, *a, **k):
        pass

    def setMaximumWidth(self, *a, **k):
        pass

    def setMinimumHeight(self, *a, **k):
        pass

    def setSizePolicy(self, *a, **k):
        pass

    def blockSignals(self, *a, **k):
        pass

    def hasFocus(self):
        return False

    def setEnabled(self, *a, **k):
        pass

    def setStyleSheet(self, *a, **k):
        pass

class QTableWidget(QWidget):
    class EditTrigger:
        NoEditTriggers = 0

class QTableWidgetItem:
    def __init__(self, *a, **k):
        pass

class QHeaderView(QWidget):
    Stretch = 1

    class ResizeMode:
        Stretch = 1
        Interactive = 2
        Fixed = 3

class QMessageBox:
    @staticmethod
    def information(*a, **k):
        return 0

    @staticmethod
    def warning(*a, **k):
        return 0

    @staticmethod
    def critical(*a, **k):
        return 0

class QProgressBar(QWidget):
    pass

class QComboBox(QWidget):
    class SizeAdjustPolicy:
        AdjustToContents = 0

    def __init__(self):
        self._items = []
        self._data = []
        self._current_index = 0
        self.currentIndexChanged = _Sig()

    def addItems(self, items):
        for item in items:
            self.addItem(item)

    def addItem(self, item, userData=None):
        self._items.append(item)
        self._data.append(userData)

    def addWidget(self, *a, **k):
        pass

    def setMinimumWidth(self, *a, **k):
        pass

    def setSizeAdjustPolicy(self, *a, **k):
        pass

    def setMaximumWidth(self, *a, **k):
        pass

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, *a, **k):
        try:
            self._current_index = int(a[0])
        except Exception:
            self._current_index = 0

    def currentData(self):
        return self.itemData(self._current_index)

    def clear(self):
        self._items = []
        self._data = []
        self._current_index = 0

    def blockSignals(self, *a, **k):
        pass

    def itemData(self, index):
        try:
            return self._data[index]
        except Exception:
            return None

    def findData(self, data):
        try:
            return self._data.index(data)
        except ValueError:
            return -1

class QSpinBox(QWidget):
    pass

class QAbstractItemView:
    NoEditTriggers = 0

    class SelectionBehavior:
        SelectRows = 0

class QMenu(QWidget):
    def __init__(self, *a, **k):
        self._actions = []

    def addAction(self, *args, **kwargs):
        if args and isinstance(args[0], QAction):
            action = args[0]
        else:
            label = str(args[0]) if args else ""
            action = QAction(label)
            callback = args[1] if len(args) > 1 else None
            if callable(callback):
                action.triggered.connect(callback)
        self._actions.append(action)
        return action

    def addSeparator(self):
        return None

    def clear(self):
        self._actions = []

    def exec(self, *a, **k):
        pass

    def setPalette(self, *a, **k):
        pass

    def setStyleSheet(self, *a, **k):
        pass

    def setAttribute(self, *a, **k):
        pass

    def setMaximumHeight(self, *a, **k):
        pass

class QWidgetAction:
    def __init__(self, *a, **k):
        self._widget = None

    def setDefaultWidget(self, widget):
        self._widget = widget

class QToolButton(QWidget):
    class ToolButtonPopupMode:
        InstantPopup = 0

    def __init__(self, *a, **k):
        self._menu = None
        self._text = ""

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setMenu(self, menu):
        self._menu = menu

    def setPopupMode(self, *a, **k):
        pass

    def showMenu(self):
        pass

    def setToolTip(self, *a, **k):
        pass

    def setMinimumWidth(self, *a, **k):
        pass

    def setSizePolicy(self, *a, **k):
        pass

    def setEnabled(self, *a, **k):
        pass

    def setStyleSheet(self, *a, **k):
        pass

class QGroupBox(QWidget):
    def __init__(self, *a, **k):
        pass

    def setVisible(self, *a, **k):
        pass

    def setEnabled(self, *a, **k):
        pass

class QTextEdit(QWidget):
    def __init__(self, *a, **k):
        pass

    def setReadOnly(self, *a, **k):
        pass

    def setFrameShape(self, *a, **k):
        pass

    def viewport(self):
        class _Viewport:
            def setAutoFillBackground(self, *a, **k):
                pass

        return _Viewport()

    def clear(self):
        pass

    def setHtml(self, *a, **k):
        pass

    def setPlainText(self, *a, **k):
        pass

    def setFont(self, *a, **k):
        pass

    def setStyleSheet(self, *a, **k):
        pass

class QTextBrowser(QTextEdit):
    def setOpenLinks(self, *a, **k):
        pass

    def setOpenExternalLinks(self, *a, **k):
        pass

class QScrollArea(QWidget):
    def __init__(self, *a, **k):
        pass

    def setWidgetResizable(self, *a, **k):
        pass

    def setWidget(self, *a, **k):
        pass

class QFileDialog:
    @staticmethod
    def getSaveFileName(*a, **k):
        return ("", "")

    @staticmethod
    def getOpenFileName(*a, **k):
        return ("", "")

    @staticmethod
    def getOpenFileNames(*a, **k):
        return ([], "")

class QAction:
    def __init__(self, *a, **k):
        self.triggered = _Sig()
        self._checked = False

    def setChecked(self, value):
        self._checked = bool(value)

    def isChecked(self):
        return self._checked

class QDialog(QWidget):
    class DialogCode:
        Accepted = 1
        Rejected = 0

    def __init__(self, *a, **k):
        pass

    def exec(self):
        return self.DialogCode.Accepted

    def accept(self):
        return self.DialogCode.Accepted

    def reject(self):
        return self.DialogCode.Rejected

class QListWidget(QWidget):
    def __init__(self, *a, **k):
        self._items = []

    def setAlternatingRowColors(self, *a, **k):
        pass

    def setSelectionMode(self, *a, **k):
        pass

    def setDragDropMode(self, *a, **k):
        pass

    def setDefaultDropAction(self, *a, **k):
        pass

    def clear(self):
        self._items.clear()

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def item(self, index):
        try:
            return self._items[index]
        except Exception:
            return None

class QListWidgetItem:
    def __init__(self, text=""):
        self._text = text
        self._data = {}
        self._flags = 0
        self._check = 0
        self._hidden = False

    def flags(self):
        return self._flags

    def setFlags(self, flags):
        self._flags = flags

    def setData(self, role, value):
        self._data[role] = value

    def data(self, role):
        return self._data.get(role)

    def setCheckState(self, state):
        self._check = state

    def checkState(self):
        return self._check

    def text(self):
        return self._text

    def setHidden(self, hidden):
        self._hidden = hidden

class QDialogButtonBox:
    class StandardButton:
        Ok = 0
        Cancel = 1

    def __init__(self, *a, **k):
        self.accepted = _Sig()
        self.rejected = _Sig()

class QCheckBox(QWidget):
    def __init__(self, *a, **k):
        self._checked = False
        self._text = a[0] if a else ""
        self.toggled = _Sig()

    def isChecked(self):
        return self._checked

    def setChecked(self, val):
        self._checked = bool(val)

    def setToolTip(self, *a, **k):
        pass

    def text(self):
        return self._text

    def setEnabled(self, *a, **k):
        pass

class QItemSelectionModel:
    Select = 0

class QTimer:
    def __init__(self, *a, **k):
        self.timeout = _Sig()

    def setSingleShot(self, *a, **k):
        pass

    def setInterval(self, *a, **k):
        pass

    @staticmethod
    def singleShot(*a, **k):
        pass

class QThread:
    def __init__(self, *a, **k):
        pass

    def start(self):
        pass

    def run(self):
        pass

class QSignalBlocker:
    def __init__(self, *_args, **_kwargs):
        pass

class Qt:
    AlignLeft = 0

    class SortOrder:
        AscendingOrder = 0
        DescendingOrder = 1

    class ContextMenuPolicy:
        CustomContextMenu = 0

    class MouseButton:
        RightButton = 2

    class ItemDataRole:
        UserRole = 32

    class WidgetAttribute:
        WA_DeleteOnClose = 0

# Stub for FilterGUISSAMixin in headless mode
class FilterGUISSAMixin:
    """Stub mixin for headless testing."""

    pass

# Type-checking bridge: fallback stubs are runtime-safe but too strict for static unions.
QWidget = cast(Any, QWidget)
QApplication = cast(Any, QApplication)
QMainWindow = cast(Any, QMainWindow)
QVBoxLayout = cast(Any, QVBoxLayout)
QHBoxLayout = cast(Any, QHBoxLayout)
QGridLayout = cast(Any, QGridLayout)
QLabel = cast(Any, QLabel)
QPushButton = cast(Any, QPushButton)
QLineEdit = cast(Any, QLineEdit)
QTableWidget = cast(Any, QTableWidget)
QProgressBar = cast(Any, QProgressBar)
QStackedWidget = cast(Any, QStackedWidget)
QTabBar = cast(Any, QTabBar)
QTabWidget = cast(Any, QTabWidget)
QMessageBox = cast(Any, QMessageBox)
QFileDialog = cast(Any, QFileDialog)
QMenu = cast(Any, QMenu)
QAction = cast(Any, QAction)
QTimer = cast(Any, QTimer)
Qt = cast(Any, Qt)
FilterGUISSAMixin = cast(Any, FilterGUISSAMixin)


class _QEventType:
    FocusIn = 0
    FocusOut = 1
    InputMethod = 2
    InputMethodQuery = 3
    Show = 4
    Hide = 5
    ContextMenu = 6
    MouseButtonPress = 7
    MouseButtonDblClick = 8


class QEvent:
    Type = _QEventType


class QUrl:
    def __init__(self, value=""):
        self._value = str(value or "")

    @staticmethod
    def fromLocalFile(path):
        return QUrl(path)

    def toString(self):
        return self._value

    def scheme(self):
        return ""

    def host(self):
        return ""


class QDesktopServices:
    @staticmethod
    def openUrl(*_args, **_kwargs):
        return False


class QSizePolicy:
    class Policy:
        Fixed = 0
        Preferred = 1
        Expanding = 2
