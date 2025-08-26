"""
TESTE DIAGNÓSTICO - REMOÇÃO DE TRUNCAMENTO FORÇADO

Este arquivo modifica temporariamente o comportamento do texto truncado
para verificar se é essa a causa do problema de renderização.

TESTE: Remover truncamento forçado e habilitar word wrap
"""

import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QTableWidget, QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt

def test_text_rendering():
    """Testa renderização de texto sem truncamento"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Cria uma tabela de teste
    table = QTableWidget(3, 2)
    table.setHorizontalHeaderLabels(["Coluna Estreita", "Coluna Larga"])
    
    # Configura larguras
    table.setColumnWidth(0, 100)  # Estreita
    table.setColumnWidth(1, 500)  # Larga
    
    # HABILITA WORD WRAP - ISSO PODE SER O QUE ESTÁ FALTANDO!
    table.setWordWrap(True)
    
    # Ajusta altura das linhas automaticamente
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    
    # Adiciona textos longos
    from PyQt6.QtWidgets import QTableWidgetItem
    
    # Texto longo para testar
    texto_longo = "REALIZADA EDIÇÃO E IMPLEMENTAÇÃO DO DBS NO SGT... Este é um texto muito longo que deveria ser renderizado completamente na coluna larga sem truncamento forçado."
    
    # Item sem truncamento
    item1 = QTableWidgetItem(texto_longo)
    item1.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    table.setItem(0, 1, item1)
    
    # Item com texto normal
    item2 = QTableWidgetItem("Texto normal")
    table.setItem(0, 0, item2)
    
    # Mostra a tabela
    table.resize(800, 300)
    table.show()
    
    print("TESTE DIAGNÓSTICO:")
    print(f"- Word Wrap habilitado: {table.wordWrap()}")
    print(f"- Largura coluna 1: {table.columnWidth(1)}px")
    print(f"- Texto completo: {len(texto_longo)} caracteres")
    print(f"- Texto no item: {item1.text()}")
    print("\nVerifique se o texto longo aparece completo na coluna larga.")
    
    return app, table

if __name__ == "__main__":
    app, table = test_text_rendering()
    app.exec()
