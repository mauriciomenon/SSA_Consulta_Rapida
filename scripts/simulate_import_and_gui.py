#!/usr/bin/env python3
"""Simulação integrada de importação de novos dados + interação GUI.

Objetivos:
  * Gerar DataFrame sintético (emula nova planilha Excel) e inserir no DB.
  * Abrir a GUI em modo offscreen (QT_QPA_PLATFORM=offscreen).
  * Acionar botões de Carregar Dados e Aplicar filtro programaticamente.
  * Esperar término dos threads e fechar a janela de forma limpa.

Uso isolado:
  python scripts/simulate_import_and_gui.py --db data/ssas.db --iterations 1

Integração com loop de testes: script pode ser chamado após cada iteração.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import time
from contextlib import suppress
from pathlib import Path

import pandas as pd

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SSA_SYNC_FILTER", "1")  # força caminho síncrono se implementado

from PyQt6.QtWidgets import QApplication

from armazenamento import database
from gui.gui_ssa import SSAMainWindow

DEFAULT_DB = os.path.join("data", "ssas.db")


def generate_synthetic_batch(batch_id: int) -> pd.DataFrame:
    base_num = 202590000 + batch_id * 10
    rows = []
    for i in range(3):
        numero = f"{base_num + i:09d}"  # já normalizado como string de 9 dígitos
        rows.append(
            {
                "numero_ssa": numero,
                "situacao": "ABERTA" if i % 2 == 0 else "EM ANDAMENTO",
                "data_cadastro": f"2025-09-13 0{i}:00:00",
                "descricao_ssa": f"Synthetic Row {batch_id}-{i}",
                "setor_executor": "SIM",
            }
        )
    return pd.DataFrame(rows)


def ensure_db_initialized(db_path: str):
    # Se não existir, inicializa com schema padrão
    if not os.path.exists(db_path):
        # cria diretório se necessário
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        database.initialize_database(db_path)


def insert_batch(db_path: str, df: pd.DataFrame):
    database.insert_dataframe_with_smart_upsert(df, db_path, "ssas")


def simulate_gui_cycle(db_path: str):
    app = QApplication.instance() or QApplication([])
    window = SSAMainWindow()
    window.show()  # ainda que offscreen

    # Carrega dados
    window.load_data()
    # Aguarda carregamento (polling simples)
    timeout = time.time() + 10
    while (
        getattr(window, "data_loader_thread", None)
        and not getattr(window.data_loader_thread, "isFinished", lambda: True)()
    ):
        if time.time() > timeout:
            break
        app.processEvents()
        time.sleep(0.05)

    # Dispara filtragem (caso tenha lógica síncrona, retorna rápido)
    with suppress(Exception):
        window.initiate_filtering()
    for _ in range(50):
        app.processEvents()
        time.sleep(0.02)

    # Fecha janela
    with suppress(Exception):
        window.close()
    app.processEvents()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument(
        "--excel",
        default="docs_entrada/Consulta SSA - 10-09-2025_0307PM (1).xlsx",
        help="Planilha real a tentar importar antes dos lotes sintéticos",
    )
    parser.add_argument(
        "--import-real-once",
        action="store_true",
        help="Importa planilha real apenas se tabela vazia",
    )
    args = parser.parse_args()

    ensure_db_initialized(args.db)

    # Tenta importação robusta de planilha real se existir
    excel_path = Path(args.excel)
    if excel_path.exists():
        try:
            from armazenamento import database as _db
            from utils.robust_importer import import_excel_robust  # import local

            # Condição opcional: só importar se vazio
            do_import = True
            if args.import_real_once:
                with sqlite3.connect(args.db) as _c:
                    cur = _c.execute("SELECT COUNT(*) FROM ssa_table")
                    current = cur.fetchone()[0]
                    if current > 0:
                        do_import = False
            if do_import:
                df_real, stats = import_excel_robust(str(excel_path))
                if not df_real.empty:
                    _db.insert_dataframe_with_smart_upsert(df_real, args.db, "ssas")
                    print(
                        f"[SIMULATION] Import real: {len(df_real)} linhas | stats dup_drop={stats.get('duplicate_rows_dropped')} invalid_ssa={stats.get('invalid_numero_ssa_rows')}"
                    )
                else:
                    print(
                        "[SIMULATION] Planilha real lida mas resultou DataFrame vazio"
                    )
        except Exception as e:  # pragma: no cover
            print(f"[SIMULATION] Falha importando planilha real: {e}")

    for i in range(args.iterations):
        batch = generate_synthetic_batch(i)
        insert_batch(args.db, batch)
        simulate_gui_cycle(args.db)

    # Verificação rápida: conta linhas
    with sqlite3.connect(args.db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ssa_table")
        total = cur.fetchone()[0]
        print(f"[SIMULATION] Linhas na tabela após simulação: {total}")


if __name__ == "__main__":  # pragma: no cover
    main()
