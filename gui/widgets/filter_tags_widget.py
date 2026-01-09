from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import pyqtSignal, Qt

class FilterTagsWidget(QWidget):
    filter_removed = pyqtSignal(str, object) # type, value

    def __init__(self):
        super().__init__()
        self._init_ui()
        self.active_filters = []

    def _init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_title = QLabel("Filtros Ativos:")
        self.lbl_title.setStyleSheet("font-weight: bold; color: gray;")
        self.layout.addWidget(self.lbl_title)
        self.lbl_title.hide()

    def update_tags(self, filters):
        """
        Updates the tags based on the provided dictionary of filters.
        filters: list of dicts or tuples e.g. [{'type': 'col', 'col': 'Setor', 'val': 'ENG'}]
        """
        # Clear existing tags (except label)
        while self.layout.count() > 1:
            child = self.layout.takeAt(1)
            if child.widget():
                child.widget().deleteLater()

        self.active_filters = filters

        if not filters:
            self.lbl_title.hide()
            return

        self.lbl_title.show()

        for f in filters:
            if isinstance(f, dict):
                 label_text = f"{f.get('label', f.get('col'))}: {f.get('val')}"
                 tag_val = f
            else:
                 # Fallback
                 label_text = str(f)
                 tag_val = f

            self._create_tag(label_text, tag_val)

    def _create_tag(self, text, value):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border-radius: 10px;
                border: 1px solid #c0c0c0;
            }
        """)
        flayout = QHBoxLayout(frame)
        flayout.setContentsMargins(8, 2, 8, 2)
        flayout.setSpacing(4)

        lbl = QLabel(text)
        lbl.setStyleSheet("border: none; color: black;")

        btn_close = QPushButton("×")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFixedSize(16, 16)
        btn_close.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-weight: bold;
                color: #666;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                color: red;
            }
        """)
        btn_close.clicked.connect(lambda: self.filter_removed.emit("remove", value))

        flayout.addWidget(lbl)
        flayout.addWidget(btn_close)

        self.layout.addWidget(frame)
