import json
import logging
import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QToolButton,
    QWidget,
)

logger = logging.getLogger(__name__)


class ProfileSelector(QWidget):
    profile_changed = pyqtSignal(list)  # Emits column list

    def __init__(self, profiles_file, default_columns, current_columns=None):
        super().__init__()
        self.profiles_file = profiles_file
        self.default_columns = default_columns
        self.current_columns = current_columns or default_columns
        self.profiles = {}
        self._load_profiles()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.combo = QComboBox()
        self.combo.setToolTip("Selecionar perfil de colunas")
        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        self.combo.setMinimumWidth(100)

        layout.addWidget(self.combo)

        self._update_combo()

    def _load_profiles(self):
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, "r") as f:
                    self.profiles = json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar perfis: {e}")

    def _save_profiles_to_disk(self):
        try:
            with open(self.profiles_file, "w") as f:
                json.dump(self.profiles, f)
        except Exception as e:
            logger.error(f"Erro ao salvar perfis: {e}")

    def _update_combo(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        # Removido item "Padrão" conforme solicitação do usuário
        for name, cols in self.profiles.items():
            self.combo.addItem(name, cols)
        self.combo.blockSignals(False)

    def _on_combo_changed(self, index):
        data = self.combo.itemData(index)
        if data:
            self.profile_changed.emit(data)

    def _save_profile(self):
        name, ok = QInputDialog.getText(self, "Salvar Perfil", "Nome do perfil:")
        if ok and name:
            self.profiles[name] = self.current_columns
            self._save_profiles_to_disk()
            self._update_combo()
            self.combo.setCurrentText(name)

    def _reset_default(self):
        self.profile_changed.emit(self.default_columns)
        # Não há mais índice 0 "Padrão", então apenas emite as colunas padrão
        if self.combo.count() > 0:
            self.combo.setCurrentIndex(0)
        else:
            self.combo.setCurrentIndex(-1)

    def _delete_current(self):
        curr = self.combo.currentText()
        # Removida verificação do "Padrão" pois não existe mais
        if curr in self.profiles:
            del self.profiles[curr]
            self._save_profiles_to_disk()
            self._update_combo()

    def set_current_columns(self, cols):
        self.current_columns = cols

    # --- Proxy Methods for QComboBox compatibility ---
    def findData(self, data, role=None):
        if role is None:
            return self.combo.findData(data)
        return self.combo.findData(data, role)

    def setCurrentIndex(self, index):
        self.combo.setCurrentIndex(index)

    def currentIndex(self):
        return self.combo.currentIndex()

    def currentText(self):
        return self.combo.currentText()

    def itemData(self, index, role=None):
        if role is None:
            return self.combo.itemData(index)
        return self.combo.itemData(index, role)

    def count(self):
        return self.combo.count()
