import os
import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from gui.app_gui import AppGuiWindow


def test_prepare_display_df_order_and_labels(qtbot=None):
    # Ensure QApplication exists
    app = QApplication.instance() or QApplication([])

    df = pd.DataFrame({
        'situacao': ['OK'],
        'numero_ssa': ['123'],  # should become 202500123 via formatter
        'descricao_ssa': ['Falha no painel'],
        'outra_coluna': ['x']
    })

    display_map = {}
    window = AppGuiWindow(df, display_map)

    prepared = window._prepare_display_df(df)

    # Expected order: numero_ssa, descricao_ssa, situacao (from priority), then the rest (outra_coluna)
    assert list(prepared.columns[:3]) == ['No', 'Desc SSA', 'Stat']
    assert prepared.columns[3] == 'outra_coluna'

    # Check SSA normalization applied before header rename
    assert prepared.iloc[0]['No'] == '202500123'

    # Cleanup the window
    window.close()
    if qtbot is None:
        app.quit()
