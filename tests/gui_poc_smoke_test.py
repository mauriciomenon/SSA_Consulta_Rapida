import os
import sys

import pandas as pd
from PyQt6.QtWidgets import QApplication


def make_sample_df():
    return pd.DataFrame(
        [
            {
                "numero_ssa": 101,
                "situacao": "ABERTA",
                "derivada_de": "-",
                "localizacao_codigo": "G076",
                "semana_cadastro": 34,
                "data_cadastro": "2025-08-18 10:11:12",
                "descricao_ssa": "Teste de descrição SSA",
                "setor_executor": "MNT",
                "setor_emissor": "OP",
                "solicitante": "João",
                "semana_programada": 35,
                "descricao_execucao": "Troca de componente",
            },
            {
                "numero_ssa": 102,
                "situacao": "EXECUTADA",
                "derivada_de": "100",
                "localizacao_codigo": "MEL3",
                "semana_cadastro": 33,
                "data_cadastro": "2025-08-10 08:00:00",
                "descricao_ssa": "Inspeção de rotina",
                "setor_executor": "INS",
                "setor_emissor": "OP",
                "solicitante": "Maria",
                "semana_programada": 33,
                "descricao_execucao": "Verificação",
            },
        ]
    )


def main():
    _app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
    # Garante que o diretório raiz do projeto está no sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from gui.gui_ssa import SSAMainWindow

    win = SSAMainWindow()

    # Injeta dataset de teste e exibe
    df = make_sample_df()
    win.df_completo = df.copy()
    win.display_data(df)

    assert win.table_widget.rowCount() == len(df)
    assert win.table_widget.columnCount() > 0

    # Testa filtro simples
    win.search_input.setText("MEL3")
    win.filter_data()
    assert not win.df_exibido.empty

    # Testa copiar célula
    item0 = win.table_widget.item(0, 0)
    if item0 is not None:
        win.copy_cell_value(item0)
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        text = clipboard.text()
        assert text.strip() != ""

    # Testa copiar linha
    if win.table_widget.rowCount() > 0:
        win.copy_row_data(0)
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        text = clipboard.text()
        assert "\t" in text or text.strip() != ""

    print("GUI PoC smoke test passed.")


if __name__ == "__main__":
    main()
